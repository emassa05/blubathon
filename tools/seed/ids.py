"""Identificadores deterministas de la demo.

Todos son UUID v4 válidos y completamente ficticios. Ningún valor procede de un
export real: está prohibido usar datos reales en tests o seeds.
"""

from __future__ import annotations


def _uuid(suffix: int) -> str:
    return f"00000000-0000-4000-8000-{suffix:012d}"


TENANT_A = _uuid(1)
TENANT_B = _uuid(2)

CAREGIVER_A = _uuid(11)
PROFESSIONAL_A = _uuid(12)
TENANT_ADMIN_A = _uuid(13)
MODEL_EVALUATOR_A = _uuid(14)
UNACCREDITED_PROFESSIONAL_A = _uuid(15)
CAREGIVER_B = _uuid(21)
PROFESSIONAL_B = _uuid(22)
TENANT_ADMIN_B = _uuid(23)

SUBJECT_ANA = _uuid(101)
SUBJECT_BETO = _uuid(102)
SUBJECT_SIN_GRANT = _uuid(103)
SUBJECT_REAL = _uuid(104)
SUBJECT_REAL_B = _uuid(105)
SUBJECT_SUENO = _uuid(106)
#: La cohorte que hace medible la calibración. Seis personas más, sembradas con
#: proporciones de días difíciles muy distintas: sus tasas base caen repartidas
#: por los tres tramos de riesgo, y sin ese reparto la calibración solo puede
#: medir el tramo donde se amontonan todos —con dos personas parecidas, 109 de
#: 120 días caían en `medium` y los otros dos tramos no se podían comprobar.
SUBJECT_COHORTE_C = _uuid(107)
SUBJECT_COHORTE_D = _uuid(108)
SUBJECT_COHORTE_E = _uuid(109)
SUBJECT_COHORTE_F = _uuid(110)
SUBJECT_COHORTE_G = _uuid(111)
SUBJECT_COHORTE_H = _uuid(112)
SUBJECT_TENANT_B = _uuid(201)

TOKENS: dict[str, str] = {
    CAREGIVER_A: "demo-cuidadora-ana",
    PROFESSIONAL_A: "demo-profesional-a",
    TENANT_ADMIN_A: "demo-admin-a",
    MODEL_EVALUATOR_A: "demo-evaluador-a",
    UNACCREDITED_PROFESSIONAL_A: "demo-profesional-sin-acreditacion",
    CAREGIVER_B: "demo-cuidador-b",
    PROFESSIONAL_B: "demo-profesional-b",
    TENANT_ADMIN_B: "demo-admin-b",
}

TARGET_DEMO_FIXTURE = "target-demo-fixture-0.3.0"
TARGET_TENANT_A = "target-tenant-a-0.3.0"
CORPUS_FIXTURE = "corpus-fixture-0.3.0"
CATALOG_FIXTURE = "catalog-fixture-0.3.0"
