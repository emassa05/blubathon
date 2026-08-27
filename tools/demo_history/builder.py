"""Días pasados con su envío, su episodio y su resultado verificado.

Existe por una razón concreta: **el baseline personal no cuenta cuestionarios,
cuenta resultados verificados** (C19, cinco). Y un resultado solo se
puede reportar cuando la ventana de 24 h del episodio ya cerró, así que por la
aplicación harían falta cinco días reales de calendario antes de ver la primera
cifra. Esto los fabrica hacia atrás.

No hay atajos: se llama a los mismos servicios que usa la API, con el `now`
movido al pasado. Cada día produce exactamente las filas que produciría un
cuidador que hubiese contestado ese día y reportado al siguiente, así que lo
sembrado es indistinguible de lo vivido.

Dos reglas mandan sobre el calendario y no se pueden esquivar:

- un `no` solo cuenta reportado `on_time`, o sea entre el cierre del objetivo y
  el vencimiento de captura;
- un `yes` necesita además un `occurred_at` dentro de `(inicio, fin]`.

Reportar antes de tiempo no falla: deja la resolución en `pending`, que es
justo lo que hacía que no se acumulara nada.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from apps.api.adapters import build_ports
from apps.api.canonical import canonical_timestamp
from apps.api.context import DEMO_TENANT_ID
from apps.api.contracts.models import AnswerItem, OutcomeReportRequest
from apps.api.services import build_registry
from apps.api.services.base import Services
from apps.api.services.local_time import REFERENCE_ZONE
from apps.api.services.local_time import local_date as reference_date
from apps.api.settings import Settings, load_settings
from apps.api.store.db import Database
from packages.shared.constants import (
    OUTCOME_CAPTURE_LIMIT_HOURS,
    TARGET_HORIZON_HOURS,
)

#: Hora local en la que se da por contestado el cuestionario de cada día.
HORA_DE_ENVIO = 9

#: El reporte llega una hora después de cerrarse la ventana del objetivo: ya es
#: `on_time` (que es lo que exige un `no`) y sigue lejos del vencimiento.
HORAS_HASTA_EL_REPORTE = TARGET_HORIZON_HOURS + 1

#: Dentro de `(inicio, fin]`, que es lo que exige un `yes`.
HORAS_HASTA_EL_EPISODIO = TARGET_HORIZON_HOURS // 2

# Un día tranquilo y uno dificil. La alternancia la decide quien llama, para
# que la tasa observada del baseline no salga siempre igual.
DIA_TRANQUILO: tuple[tuple[str, object], ...] = (
    ("sleep_quality", "restorative"),
    ("wake_state", "calm_happy"),
    ("sleep_hours", 9.5),
    ("night_awakenings", 0),
    ("daily_regulation_state", "excellent"),
    ("gi_status", "normal"),
    ("medication_adherence", "taken"),
)

DIA_DIFICIL: tuple[tuple[str, object], ...] = (
    ("sleep_quality", "interrupted"),
    ("wake_state", "irritable_crying"),
    ("sleep_hours", 5.5),
    ("night_awakenings", 3),
    ("daily_regulation_state", "frequent_dysregulation"),
    ("gi_status", "constipation"),
    ("medication_adherence", "missed"),
)

#: Un día malo **solo por el sueño**: lo digestivo, la medicación y la
#: regulación vienen bien.
#:
#: `query_for()` arma la consulta con las etiquetas de todos los campos, así que
#: un día difícil del perfil mixto aporta vocabulario de GI, medicación y rutina
#: al mismo tiempo, y BM25 reparte el puntaje entre fragmentos de esos temas. El
#: que gana no es el de sueño. Dejando el resto en su valor bueno la consulta
#: queda dominada por sueño y la recomendación sale sobre eso.
DIA_SOLO_SUENO: tuple[tuple[str, object], ...] = (
    ("sleep_quality", "interrupted"),
    ("wake_state", "irritable_crying"),
    ("sleep_hours", 5.0),
    ("night_awakenings", 4),
    ("daily_regulation_state", "excellent"),
    ("gi_status", "normal"),
    ("medication_adherence", "taken"),
)

#: Perfiles de día malo disponibles, por nombre de `--perfil`.
PERFILES_DIFICILES: dict[str, tuple[tuple[str, object], ...]] = {
    "mixto": DIA_DIFICIL,
    "sueno": DIA_SOLO_SUENO,
}


@dataclass(frozen=True, slots=True)
class DiaSembrado:
    local_date: str
    prediction_episode_id: str
    outcome_value: str
    resolution_status: str


@dataclass(frozen=True, slots=True)
class DemoHistoryResult:
    child_id: str
    days: tuple[DiaSembrado, ...]

    @property
    def verified(self) -> int:
        return sum(1 for day in self.days if day.resolution_status in {"yes", "no"})


CAMPOS_CON_DEFECTO: tuple[tuple[str, object, object], ...] = (
    ("food_changes", False, True),
    ("activity_participation", 4, 3),
    ("social_interactions", 3, 4),
    ("eating_status", 4, 3),
)

#: Uno de cada cuantos días se responde la alternativa en vez del dominante.
CADA_CUANTOS_VARIA = 7


# Probabilidad de que haya crisis, según cómo venga el día.
#
# **No es 1.0 y 0.0 a propósito.** Antes el resultado salía del perfil del día
# sin ruido, y el challenger aprendía esa regla a la perfección: un Brier de
# 0.004 que no medía el modelo sino mi forma de sembrar. Con una relación
# probabilística los coeficientes salen de una señal que existe pero no es
# perfecta, que es como se comportan los datos de verdad.
#
# Un día difícil no garantiza la crisis y uno tranquilo no la descarta: eso es
# justo lo que hace falta predecir.
RIESGO_DIA_DIFICIL = 0.70
RIESGO_DIA_TRANQUILO = 0.15


def _hubo_crisis(child_id: str, local_date: str, dificil: bool) -> bool:
    """Sorteo reproducible: la misma semilla siembra siempre lo mismo."""

    semilla = hashlib.sha256(f"{child_id}|{local_date}|crisis".encode()).digest()
    sorteo = int.from_bytes(semilla[:8], "big") / 2**64
    return sorteo < (RIESGO_DIA_DIFICIL if dificil else RIESGO_DIA_TRANQUILO)


def _answers(dificil: bool, indice: int, perfil: str = "mixto") -> tuple[AnswerItem, ...]:
    filas = list(PERFILES_DIFICILES[perfil] if dificil else DIA_TRANQUILO)
    # Determinista y desfasado por campo: si todos variaran el mismo día, la
    # variación sería un patrón y no ruido.
    for desplazamiento, (code, dominante, alterno) in enumerate(CAMPOS_CON_DEFECTO):
        varia = (indice + desplazamiento * 2) % CADA_CUANTOS_VARIA == 0
        filas.append((code, alterno if varia else dominante))
    return tuple(
        AnswerItem(field_code=code, value=value, interaction="manual") for code, value in filas
    )


def build_history(
    *,
    child_id: str,
    days: int,
    dificiles: int,
    perfil: str = "mixto",
    settings: Settings | None = None,
    adapters: str | None = None,
) -> DemoHistoryResult:
    """Siembra `days` días cerrados, `dificiles` de ellos con mal perfil.

    `dificiles` cuenta **días con mal aspecto**, no crisis: si hubo crisis lo
    decide el sorteo de `_hubo_crisis`. Un día difícil que acaba bien y uno
    tranquilo que acaba mal son exactamente los casos que el modelo tiene que
    aprender a pesar.

    El día de hoy no se toca: su ventana de 24 h sigue abierta y su resultado
    todavía no se puede reportar. Se empieza en ayer y se va hacia atrás.
    """

    if days < 1:
        raise ValueError("hacen falta al menos dos días para que el baseline cuente algo")
    if not 0 <= dificiles <= days:
        raise ValueError("los días difíciles tienen que caber en los días sembrados")
    if perfil not in PERFILES_DIFICILES:
        opciones = ", ".join(sorted(PERFILES_DIFICILES))
        raise ValueError(f"perfil desconocido: {perfil} (hay {opciones})")

    resolved = settings or load_settings()
    database = Database(resolved, clock=lambda: datetime.now(UTC))
    database.migrate()
    core = Services(
        settings=resolved,
        database=database,
        ports=build_ports(adapters, secret=resolved.audit_secret, database=database),
        # La redacción del RAG no entra aquí: sembrar historial no necesita
        # recomendaciones, y pedirlas sin modelo solo produce abstenciones.
        draft_transport=None,
    )
    registry = build_registry(core)

    # El ancla se cuenta en la zona de referencia, no en UTC.
    #
    # Santiago va cuatro horas por detrás, así que entre medianoche y las 04:00
    # UTC el "hoy" de UTC ya es el día siguiente para el sistema. Anclando en
    # UTC, el `offset=1` caía sobre la fecha local de hoy: la herramienta se
    # comía el día que tenía que dejar libre, y el envío del cuestionario se
    # enganchaba al episodio ya sembrado en vez de abrir uno nuevo.
    hoy = datetime.combine(
        reference_date(datetime.now(UTC)),
        time(HORA_DE_ENVIO, 0),
        tzinfo=REFERENCE_ZONE,
    )
    sembrados: list[DiaSembrado] = []
    try:
        # De más antiguo a más reciente, para que cada episodio vea a los
        # anteriores ya resueltos, igual que en el tiempo real.
        for offset in range(days, 0, -1):
            enviado_a_las = hoy - timedelta(days=offset)
            # Repartidos por todo el rango, no en bloque al principio. Un bloque
            # deja los días difíciles perfectamente separados de los tranquilos,
            # y sobre eso el challenger no aprende nada útil: la costumbre del
            # niño (`personal_predictor_rate`, 30 días) sería constante dentro de
            # cada mitad y la desviación del día, cero.
            indice = days - offset
            dificil = (indice * dificiles) // days != ((indice - 1) * dificiles) // days
            with core.database.write() as connection:
                envio = registry.submissions.submit(
                    connection,
                    tenant_id=DEMO_TENANT_ID,
                    subject_id=child_id,
                    source="caregiver_daily",
                    local_date=enviado_a_las.date().isoformat(),
                    answers=_answers(dificil, offset, perfil),
                    now=canonical_timestamp(enviado_a_las),
                )
            episodio = envio.prediction_episode_id
            if episodio is None:
                continue

            crisis = _hubo_crisis(child_id, enviado_a_las.date().isoformat(), dificil)
            reportado_a_las = enviado_a_las + timedelta(hours=HORAS_HASTA_EL_REPORTE)
            ocurrido_a_las = enviado_a_las + timedelta(hours=HORAS_HASTA_EL_EPISODIO)
            with core.database.write() as connection:
                reporte = registry.outcomes.create_report(
                    connection,
                    tenant_id=DEMO_TENANT_ID,
                    prediction_episode_id=str(episodio),
                    request=OutcomeReportRequest(
                        value="yes" if crisis else "no",
                        occurred_at=ocurrido_a_las if crisis else None,
                    ),
                    now=canonical_timestamp(reportado_a_las),
                )
            sembrados.append(
                DiaSembrado(
                    local_date=enviado_a_las.date().isoformat(),
                    prediction_episode_id=str(episodio),
                    outcome_value=reporte.report.value,
                    resolution_status=reporte.resolution.status,
                )
            )
    finally:
        database.close()

    return DemoHistoryResult(child_id=child_id, days=tuple(sembrados))


__all__ = [
    "HORAS_HASTA_EL_REPORTE",
    "OUTCOME_CAPTURE_LIMIT_HOURS",
    "DemoHistoryResult",
    "DiaSembrado",
    "build_history",
]
