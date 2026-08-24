"""§0.12 — El sistema sugiere, nunca autocompleta. Una sugerencia sin
confirmar no llega a `/ingest`: un valor sugerido y no tocado no existe."""

from ml.errors import ContractViolationError
from ml.voi.compute import suggestion_for
from packages.shared.models import DailyLog


def test_s0_12_hay_sugerencia_disponible_pero_no_se_envia_sola(calm_history):
    """La sugerencia (mediana personal) existe y se puede calcular, pero
    `/ingest` exige que el cliente la haya tocado: mandarla sin procedencia
    'confirmed'/'observed' vía assumed_stable es justamente el caso que
    §2.5 prohíbe (no existe una vía de 'autocompletar')."""
    as_of = "2026-08-10"
    history = [log for log in calm_history if log["date"] <= as_of]
    suggestion, _label = suggestion_for(history, "sleep_quality", as_of)
    assert suggestion is not None  # hay base para sugerir

    # "Enviar" la sugerencia sin que la persona la haya tocado significa
    # mandarla con provenance assumed_stable (que nunca asigna valor) o no
    # mandarla. Intentar colar el valor sugerido como si fuera 'assumed_stable'
    # debe rechazarse: la sugerencia no puede colarse como dato.
    try:
        DailyLog(
            child_id="c1",
            date="2026-08-11",
            source="home",
            sleep_quality=suggestion,
            field_provenance={"sleep_quality": "assumed_stable"},
        )
        raised = False
    except ContractViolationError:
        raised = True
    assert raised


def test_s0_12_campo_no_tocado_queda_null_unknown():
    log = DailyLog(child_id="c1", date="2026-08-11", source="home")
    assert log.sleep_quality is None
    assert log.field_provenance.get("sleep_quality", "unknown") == "unknown"
