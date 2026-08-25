"""Fechas locales de la zona de referencia (SPEC 5.1, 5.2, 5.8).

`local_date` se deriva de `effective_at` en `America/Santiago` y se persiste,
para reproducir ventanas aunque cambie la librería de zona horaria.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from apps.api.contracts.constants import REFERENCE_TIMEZONE

REFERENCE_ZONE = ZoneInfo(REFERENCE_TIMEZONE)


def local_date(moment: datetime) -> date:
    return moment.astimezone(REFERENCE_ZONE).date()


def inclusive_window(day: date, window_days: int) -> tuple[date, date]:
    """`últimos W días, inclusivo = [D-(W-1), D]` (SPEC 5.8)."""
    return day - timedelta(days=window_days - 1), day


def exclusive_window(day: date, window_days: int) -> tuple[date, date]:
    """`W días previos, exclusivo = [D-W, D)` (SPEC 5.8)."""
    return day - timedelta(days=window_days), day
