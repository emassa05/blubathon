"""Point-in-time personal baselines and model features from SPEC section 9.1."""

from __future__ import annotations

import math
import warnings
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.covariance import MinCovDet

from ml.spec_constants import (
    FEATURE_LAG_FIELDS,
    FEATURE_LAGS,
    FEATURE_MAD_SCALE,
    FEATURE_MAHALANOBIS_REGULARIZATION,
    FEATURE_MIN_OBSERVATIONS,
    FEATURE_ROBUST_WINDOW_MAX_DAYS,
    FEATURE_ROBUST_WINDOW_MIN_DAYS,
    FEATURE_ROLLING_WINDOWS,
    FEATURE_TREND_WINDOW_DAYS,
    FEATURE_WEEKDAY_MIN_OBSERVATIONS,
    FEATURE_ZERO_MAD_SCALE,
    MODEL_INPUT_FIELDS,
    NUMERIC_FIELDS,
    RANDOM_SEED,
)
from packages.shared import DailyLog


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _records(history: Iterable[DailyLog | Mapping[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(history, pd.DataFrame):
        frame = history.copy()
    else:
        records = [
            item.model_dump(mode="python") if isinstance(item, DailyLog) else dict(item)
            for item in history
        ]
        frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    return frame


def _aggregate_daily(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    available_values = [variable for variable in MODEL_INPUT_FIELDS if variable in frame]
    aggregation: dict[str, str] = {variable: "median" for variable in available_values}
    if "crisis_occurred" in frame:
        aggregation["crisis_occurred"] = "max"
    daily = frame.groupby(["child_id", "date"], as_index=False, sort=True).agg(aggregation)
    for variable in MODEL_INPUT_FIELDS:
        if variable not in daily:
            daily[variable] = np.nan
        daily[variable] = pd.to_numeric(daily[variable], errors="coerce")
    if "crisis_occurred" not in daily:
        daily["crisis_occurred"] = np.nan
    return daily.sort_values(["child_id", "date"], ignore_index=True)


def _prior_windows(series: pd.Series, window: int) -> np.ndarray:
    values = series.to_numpy(dtype=float)
    padded = np.pad(values, (window, 0), constant_values=np.nan)
    return np.lib.stride_tricks.sliding_window_view(padded, window)[: len(values)]


def _rolling_prior_stats(series: pd.Series, window: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    windows = _prior_windows(series, window)
    count = np.sum(~np.isnan(windows), axis=1).astype(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        median = np.nanmedian(windows, axis=1)
        mad = np.nanmedian(np.abs(windows - median[:, None]), axis=1) * FEATURE_MAD_SCALE
    return (
        pd.Series(count, index=series.index),
        pd.Series(median, index=series.index),
        pd.Series(mad, index=series.index),
    )


def _weekday_prior_stats(series: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    values = np.column_stack(
        [series.shift(days).to_numpy(dtype=float) for days in range(7, window + 1, 7)]
    )
    count = np.sum(~np.isnan(values), axis=1).astype(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        median = np.nanmedian(values, axis=1)
    return pd.Series(count, index=series.index), pd.Series(median, index=series.index)


def _choose_window(short: pd.Series, long: pd.Series, short_count: pd.Series) -> pd.Series:
    return short.where(short_count >= FEATURE_MIN_OBSERVATIONS, long)


def _point_in_time_zscores(series: pd.Series) -> pd.Series:
    short_window = FEATURE_ROBUST_WINDOW_MIN_DAYS
    long_window = FEATURE_ROBUST_WINDOW_MAX_DAYS
    short_count, global_short, raw_short_mad = _rolling_prior_stats(series, short_window)
    long_count, global_long, raw_long_mad = _rolling_prior_stats(series, long_window)
    global_expected = _choose_window(global_short, global_long, short_count)

    weekday_short_count, weekday_short = _weekday_prior_stats(series, short_window)
    weekday_long_count, weekday_long = _weekday_prior_stats(series, long_window)

    use_short = short_count >= FEATURE_MIN_OBSERVATIONS
    weekday_expected = weekday_short.where(use_short, weekday_long)
    weekday_count = weekday_short_count.where(use_short, weekday_long_count)
    expected = weekday_expected.where(
        weekday_count >= FEATURE_WEEKDAY_MIN_OBSERVATIONS,
        global_expected,
    )

    residual = series - expected
    residual_short_count, _, residual_short_mad = _rolling_prior_stats(residual, short_window)
    residual_long_count, _, residual_long_mad = _rolling_prior_stats(residual, long_window)
    residual_mad = _choose_window(
        residual_short_mad,
        residual_long_mad,
        residual_short_count,
    )
    residual_count = residual_short_count.where(use_short, residual_long_count)

    raw_mad = _choose_window(raw_short_mad, raw_long_mad, short_count)
    scale = residual_mad.where(residual_count >= FEATURE_MIN_OBSERVATIONS, raw_mad)
    scale = scale.mask(scale <= 0.0, FEATURE_ZERO_MAD_SCALE)
    zscores = (series - expected) / scale
    return zscores.where(long_count >= FEATURE_MIN_OBSERVATIONS)


def compute_robust_zscore(
    history: Iterable[DailyLog | Mapping[str, Any]] | pd.DataFrame,
    variable: str,
    target_date: date | datetime | str,
    current_value: float | int | bool | None = None,
    *,
    child_id: str | None = None,
) -> float:
    """Compare one value with one child's prior weekday-adjusted baseline."""
    frame = _aggregate_daily(_records(history))
    if frame.empty or variable not in frame:
        return float("nan")
    child_ids = frame["child_id"].astype(str).unique()
    if child_id is None:
        if len(child_ids) != 1:
            raise ValueError("child_id is required when history contains multiple children")
        child_id = child_ids[0]
    child = frame[frame["child_id"].astype(str) == str(child_id)]
    if child.empty:
        return float("nan")

    target = pd.Timestamp(_as_date(target_date))
    values = child.set_index("date")[variable].sort_index()
    full_index = pd.date_range(min(values.index.min(), target), max(values.index.max(), target))
    series = values.reindex(full_index).astype(float)
    if current_value is not None:
        series.loc[target] = float(current_value)
    return float(_point_in_time_zscores(series).get(target, np.nan))


def _select_personal_window(history: pd.DataFrame, target: pd.Timestamp) -> pd.DataFrame:
    short_start = target - pd.DateOffset(days=FEATURE_ROBUST_WINDOW_MIN_DAYS)
    short = history[(history["date"] >= short_start) & (history["date"] < target)]
    if len(short) >= FEATURE_MIN_OBSERVATIONS:
        return short
    long_start = target - pd.DateOffset(days=FEATURE_ROBUST_WINDOW_MAX_DAYS)
    return history[(history["date"] >= long_start) & (history["date"] < target)]


def compute_robust_mahalanobis(
    history: Iterable[DailyLog | Mapping[str, Any]] | pd.DataFrame,
    child_id: str,
    target_date: date | datetime | str,
    current: Mapping[str, float | int | bool | None] | pd.Series | None = None,
    variables: Sequence[str] = NUMERIC_FIELDS,
) -> float:
    """Compute one child's point-in-time robust distance without imputing missing values."""
    daily = _aggregate_daily(_records(history))
    if daily.empty:
        return float("nan")
    target = pd.Timestamp(_as_date(target_date))
    child = daily[daily["child_id"].astype(str) == str(child_id)]
    if child.empty:
        return float("nan")
    if current is None:
        current_rows = child[child["date"] == target]
        if current_rows.empty:
            return float("nan")
        current = current_rows.iloc[-1]
    personal_history = _select_personal_window(child, target)

    usable = [
        variable
        for variable in variables
        if variable in personal_history
        and current.get(variable) is not None
        and not pd.isna(current.get(variable))
        and personal_history[variable].notna().sum() >= FEATURE_MIN_OBSERVATIONS
    ]
    while usable:
        complete = personal_history[usable].dropna()
        required_rows = max(FEATURE_MIN_OBSERVATIONS, len(usable) + 1)
        if len(complete) >= required_rows:
            break
        least_observed = min(
            usable,
            key=lambda variable: personal_history[variable].notna().sum(),
        )
        usable.remove(least_observed)
    if not usable:
        return float("nan")

    complete = personal_history[usable].dropna().astype(float)
    current_vector = np.array([float(current[variable]) for variable in usable])
    medians = complete.median(axis=0).to_numpy()
    mads = (complete - medians).abs().median(axis=0).to_numpy() * FEATURE_MAD_SCALE
    varying = mads > 0.0
    constant_delta = (current_vector[~varying] - medians[~varying]) / FEATURE_ZERO_MAD_SCALE
    squared_constant_distance = float(constant_delta @ constant_delta)
    if not varying.any():
        return math.sqrt(squared_constant_distance)

    scaled_history = (complete.to_numpy()[:, varying] - medians[varying]) / mads[varying]
    scaled_current = (current_vector[varying] - medians[varying]) / mads[varying]
    if scaled_history.shape[1] == 1:
        return math.sqrt(squared_constant_distance + float(scaled_current[0] ** 2))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            estimator = MinCovDet(random_state=RANDOM_SEED).fit(scaled_history)
            location = estimator.location_
            covariance = estimator.covariance_
        except ValueError:
            location = np.median(scaled_history, axis=0)
            covariance = np.cov(scaled_history, rowvar=False)
    covariance = np.atleast_2d(covariance) + np.eye(scaled_history.shape[1]) * (
        FEATURE_MAHALANOBIS_REGULARIZATION
    )
    centered = scaled_current - location
    squared_variable_distance = float(centered @ np.linalg.pinv(covariance) @ centered)
    return math.sqrt(max(0.0, squared_constant_distance + squared_variable_distance))


def _rolling_slopes(series: pd.Series, window: int) -> pd.Series:
    values = series.to_numpy(dtype=float)
    padded = np.pad(values, (window - 1, 0), constant_values=np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(padded, window)
    observed = ~np.isnan(windows)
    count = observed.sum(axis=1)
    x = np.broadcast_to(np.arange(window, dtype=float), windows.shape)
    safe_values = np.where(observed, windows, 0.0)
    safe_x = np.where(observed, x, 0.0)
    x_mean = np.divide(safe_x.sum(axis=1), count, out=np.zeros(len(count)), where=count > 0)
    y_mean = np.divide(safe_values.sum(axis=1), count, out=np.zeros(len(count)), where=count > 0)
    centered_x = np.where(observed, x - x_mean[:, None], 0.0)
    centered_y = np.where(observed, safe_values - y_mean[:, None], 0.0)
    denominator = np.sum(centered_x**2, axis=1)
    numerator = np.sum(centered_x * centered_y, axis=1)
    slopes = np.divide(
        numerator,
        denominator,
        out=np.full(len(count), np.nan),
        where=(count >= 2) & (denominator > 0.0),
    )
    return pd.Series(slopes, index=series.index)


def _child_features(child: pd.DataFrame) -> pd.DataFrame:
    child = child.sort_values("date").copy()
    original_dates = pd.DatetimeIndex(child["date"])
    full_dates = pd.date_range(original_dates.min(), original_dates.max())
    indexed = child.set_index("date").reindex(full_dates)
    output = pd.DataFrame(
        {
            "child_id": child["child_id"].to_numpy(),
            "date": original_dates,
        }
    )

    for variable in MODEL_INPUT_FIELDS:
        series = indexed[variable].astype(float)
        output[variable] = series.reindex(original_dates).to_numpy()
        output[f"{variable}_missing"] = series.reindex(original_dates).isna().to_numpy()
        if variable in NUMERIC_FIELDS:
            zscores = _point_in_time_zscores(series)
            output[f"{variable}_z"] = zscores.reindex(original_dates).to_numpy()
            for window_days in FEATURE_ROLLING_WINDOWS:
                rolling = series.rolling(window_days, min_periods=1).mean()
                output[f"{variable}_mean_{window_days}d"] = rolling.reindex(
                    original_dates
                ).to_numpy()
            trend = _rolling_slopes(series, FEATURE_TREND_WINDOW_DAYS)
            output[f"{variable}_trend_{FEATURE_TREND_WINDOW_DAYS}d"] = trend.reindex(
                original_dates
            ).to_numpy()
        if variable in FEATURE_LAG_FIELDS:
            for lag_days in FEATURE_LAGS:
                output[f"{variable}_lag_{lag_days}d"] = (
                    series.shift(lag_days).reindex(original_dates).to_numpy()
                )

    crisis = indexed["crisis_occurred"].astype(float)
    output["personal_base_rate"] = (
        crisis.expanding(min_periods=1).mean().reindex(original_dates).to_numpy()
    )
    output["day_of_week"] = original_dates.weekday
    return output


def build_feature_matrix(
    history: Iterable[DailyLog | Mapping[str, Any]] | pd.DataFrame,
) -> pd.DataFrame:
    """Build point-in-time features using only each row's date and earlier history."""
    daily = _aggregate_daily(_records(history))
    if daily.empty:
        return pd.DataFrame(columns=["child_id", "date"])
    matrices = [_child_features(child) for _, child in daily.groupby("child_id", sort=True)]
    return pd.concat(matrices, ignore_index=True).sort_values(
        ["child_id", "date"], ignore_index=True
    )
