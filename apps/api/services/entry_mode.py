"""Derivación de `entry_mode` en el servidor (SPEC 5.5, CONVENTIONS 8.3).

El cliente envía la interacción; nunca se confía en un `entry_mode` de navegador.
Una combinación no contemplada falla: no se elige el modo por prioridad
implícita.
"""

from __future__ import annotations

from apps.api.contracts.enums import AnswerInteraction, EntryMode, FormSessionKind, IntakeChannel
from apps.api.errors import invalid


def derive_entry_mode(
    *,
    intake_channel: IntakeChannel,
    session_kind: FormSessionKind,
    audit_mode: bool,
    interaction: AnswerInteraction,
    has_current_presentation: bool,
) -> EntryMode:
    # 1. Canal de importación: exige mapping aprobado y produce imported_observed.
    if intake_channel is IntakeChannel.IMPORT:
        return EntryMode.IMPORTED_OBSERVED

    # 3. Interacción `unknown`: produce explicit_unknown sin valor.
    #
    # Se evalúa antes que la regla 2 porque `professional_observed` asigna valor
    # y `unknown` es por definición una decisión sin valor (SPEC 8.2). La
    # combinación "sesión profesional + unknown" no está contemplada de forma
    # explícita en la precedencia del SPEC 5.5; P2 la resuelve de la única forma
    # que no fabrica un valor y la reporta como pregunta de contrato a P1.
    if interaction is AnswerInteraction.UNKNOWN:
        return EntryMode.EXPLICIT_UNKNOWN

    # 2. Sesión de observación profesional: no muestra defaults.
    if session_kind is FormSessionKind.PROFESSIONAL_OBSERVATION:
        if has_current_presentation:
            raise invalid("validation_error", reason="professional_session_has_no_defaults")
        return EntryMode.PROFESSIONAL_OBSERVED

    # 5 y 6. Aceptar o editar exige una presentación vigente.
    if interaction in (AnswerInteraction.ACCEPT_DEFAULT, AnswerInteraction.EDIT_DEFAULT):
        if not has_current_presentation:
            raise invalid("default_presentation_not_current")
        return (
            EntryMode.DEFAULT_ACCEPTED
            if interaction is AnswerInteraction.ACCEPT_DEFAULT
            else EntryMode.DEFAULT_EDITED
        )

    # 4. Sesión auditada: una respuesta manual produce audit_manual.
    if audit_mode:
        return EntryMode.AUDIT_MANUAL

    # 7. Un valor manual sobre un campo con presentación vigente es default_edited,
    #    aunque el cliente lo llame `manual`.
    if has_current_presentation:
        return EntryMode.DEFAULT_EDITED

    # 8. manual_no_default solo si ese campo/sesión nunca tuvo presentación.
    return EntryMode.MANUAL_NO_DEFAULT
