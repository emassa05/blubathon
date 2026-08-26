# Contrato del backend de Faro — v0.3.0

Estado del contrato, tal como está implementado hoy en el repositorio. No es una
propuesta: cada ruta, campo, enum, constante y código de error de este documento
sale del código que corre.

- **`spec_version`**: `0.3.0` (constante `C01`)
- **`contract_version`**: `faro-contract-0.3.0`
- **`schema_hash`**: `8c4c956037e952b0666b8f99722d07faaf09bb11528a1072f20b91c811cee526`
  (léelo siempre de `packages/shared/generated/contract.lock.json`, no de aquí:
  un hash copiado en prosa se pudre)
- **143 definiciones** en el bundle JSON Schema, **87 modelos publicados**

## Fuentes de verdad

| Qué | Dónde |
|---|---|
| Modelos Pydantic (fuente de verdad) | `packages/shared/domain/**`, reexportados por `packages/shared/models.py` |
| Extensiones de producto de P2 | `apps/api/contracts/models.py` (subclases, nunca copias) |
| Vocabularios cerrados | `packages/shared/enums.py` |
| Catálogo de campos y matriz de fuentes | `packages/shared/field_catalog.py` |
| Constantes C01–C50 | `packages/shared/constants.py` |
| Textos en español | `packages/shared/texts.py` |
| Rutas HTTP | `apps/api/routes/v1.py` |
| Traducción de errores a HTTP | `apps/api/errors.py`, `apps/api/main.py` |
| JSON Schema / TypeScript / Zod | `packages/shared/generated/` |
| Ejemplos válidos e inválidos | `packages/shared/examples/` |

Nada bajo `generated/` ni `examples/` se edita a mano:

```bash
python -m tools.contracts.generate
python -m tools.contracts.examples
git diff --exit-code packages/shared/generated packages/shared/examples
```

---

## 1. Convenciones transversales

### 1.1 Prefijo y documentación

- Todas las rutas de producto cuelgan de **`/api/v1`** (`C02`).
- `GET /health` y `/docs` viven fuera del prefijo.
- `/docs` y `/openapi.json` **solo existen en `FARO_MODE=demo`**; el modo piloto
  los deshabilita (`CONVENTIONS 15`).

### 1.2 Autenticación

```http
Authorization: Bearer <demo_session_token>
```

En modo demo el token busca un usuario sembrado en `users.demo_session_token`.
**El modo piloto rechaza este autenticador** (`invalid_credentials`, 401): el
piloto exige OIDC y todavía no está implementado.

Tokens de demostración sembrados por `python -m tools.seed`:

| Token | Persona ficticia | Rol |
|---|---|---|
| `demo-cuidadora-ana` | Ana Ríos | `caregiver` |
| `demo-profesional-a` | Pilar Soto | `professional` acreditada |
| `demo-evaluador-a` | Evaluador Demo A | `model_evaluator` |
| `demo-profesional-sin-acreditacion` | — | `professional` sin acreditación vigente |
| `demo-cuidador-b` | — | `caregiver` de otra organización |

### 1.3 Autorización

Tenant + rol **no bastan**. Toda operación clínica exige además un
`SubjectAccessGrant` activo con la capability literal de la operación
(`SPEC 2.26`). Matriz mínima (`OPERATION_MATRIX`, `packages/shared/domain/identity.py`):

| Operación | Roles permitidos | Grant capability | Acreditación | Nota |
|---|---|---|---|---|
| `read_subject_or_form` | caregiver, professional | `subject_read` | `subject_care` | |
| `write_daily_observation` | caregiver, professional | `daily_observation_write` | `subject_care` | |
| `submit_form` | caregiver, professional | `form_submit` | `subject_care` | |
| `report_outcome` | caregiver, professional | `outcome_report` | — | el rol debe estar en `eligible_reporter_roles` del target |
| `review_recommendation` | professional | `recommendation_review` | `subject_care` | el actor debe satisfacer `required_approver_role` |
| `record_execution` | caregiver, professional | `execution_record` | — | el rol debe estar en `allowed_executor_roles` del ítem |
| `read_clinical_evaluation` | model_evaluator, professional | `evaluation_read` | `model_evaluation` | |

La acreditación solo se exige a quien tiene rol `professional` **y no** rol
`caregiver`.

Precedencia de negación al autorizar un sujeto (`AuthorizationService.authorize_subject`),
todas **403** y todas auditadas:

1. sujeto inexistente o de otro tenant → `cross_tenant`
2. cohorte no permitida por el modo de despliegue → `cohort_not_allowed`
3. rol no permitido → `role_not_allowed`
4. professional sin acreditación vigente → `accreditation_required`
5. sin grant activo con la capability → `subject_access_denied`

Un recurso (episodio, instancia, sesión) de otro tenant se comporta como
**inexistente**: **404 `not_found`**, nunca 403. Un 403 confirmaría que existe.

Los listados se filtran **en SQL** por tenant y grant (`GRANT_FILTER_SQL`);
nunca se cargan filas prohibidas para descartarlas después.

### 1.4 Cabeceras

| Cabecera | Dirección | Obligatoria en | Efecto |
|---|---|---|---|
| `Authorization: Bearer …` | request | todas las rutas `/api/v1` | 401 si falta o no resuelve |
| `Idempotency-Key: <str>` | request | **todo POST** | 400 `idempotency_key_required` si falta o viene vacía |
| `If-Match: <revision>` | request | POST de `reviews` y `executions` | 428 `precondition_required` si falta |
| `ETag: "<revision>"` | response | `GET …/recommendations` | token a devolver en `If-Match` |
| `X-Request-Id: <uuid>` | response | **todas** | mismo valor que `error.request_id` |

CORS: allowlist explícita (`FARO_CORS_ORIGINS`), nunca comodín.
`allow_credentials=false`; métodos `GET, POST, OPTIONS`; headers permitidos
`Authorization, Content-Type, Idempotency-Key, If-Match`; se expone `ETag`.

### 1.5 Idempotencia (`SPEC 11.2`)

El scope es la tupla **`(tenant_id, actor_id, method, ruta concreta, idempotency_key)`**.
La ruta es la **concreta y normalizada**, con los IDs reales — nunca la plantilla
de ruta. Un scope con `{` o `}` es un error de contrato: la misma clave sobre dos
recursos distintos jamás puede reproducir la respuesta del otro.

La huella del request cubre además `path_params`, la query canónica y el body:

```
request_fingerprint = sha256(dominio, contract_version, {scope, path_params, query, body})
```

- Misma clave + misma huella → se devuelve la respuesta guardada (**replay**).
- Misma clave + huella distinta → **409 `idempotency_key_conflict`**.
- Un replay **vuelve a autorizar** rol, acreditación, grant y capability antes de
  devolver la respuesta guardada: si el grant se revocó, el replay ya no pasa.

### 1.6 Concurrencia optimista

`GET …/recommendations` devuelve `revision` en el cuerpo y en el `ETag`.
Los POST de `reviews` y `executions` exigen `If-Match`:

| Situación | Respuesta |
|---|---|
| sin cabecera `If-Match` | **428** `precondition_required` |
| revisión vigente | **201** |
| revisión obsoleta | **409** `revision_conflict` |

### 1.7 Sobre de error (`SPEC 11.7`)

```json
{
  "error": {
    "code": "forbidden",
    "message_es": "No tienes autorización para esta operación.",
    "request_id": "d26b9ac7-59e4-43be-bfcc-7b1daca98f10"
  }
}
```

El sobre **nunca lleva payload clínico**. Toda negativa queda en auditoría
append-only, sin payload, aunque la transacción del comando se revierta.

**La abstención no es un error.** Un track que no estima, un catálogo que no
recomienda y una métrica sin soporte responden **HTTP 200** con su propio estado
explícito (`abstained`, `unavailable`, `not_estimable`,
`awaiting_professional_review`). El sobre de error jamás se usa para eso.

### 1.8 Reglas del modelo base (`FaroModel`)

- `extra="forbid"`: un campo desconocido es **422**, no se ignora.
- `frozen=True`: los modelos son inmutables; una corrección es una fila nueva
  enlazada con `supersedes_id`, nunca una mutación.
- Identificadores: **UUID**.
- Instantes: **datetime con zona**, normalizados a UTC. Un naive es error de contrato.
- Enums cerrados; toda respuesta tiene modelo explícito (ninguna ruta devuelve un dict suelto).

Tipos escalares:

| Tipo | Regla |
|---|---|
| `UtcDatetime` | aware, convertido a UTC |
| `Probability` | float en `[0.0, 1.0]` |
| `NonNegativeFloat` | float `≥ 0.0` |
| `VersionLabel` | `^[a-z0-9][a-z0-9._-]{0,63}$` |
| `Sha256Hex` | `^[0-9a-f]{64}$` |
| `Tag` | `^[a-z][a-z0-9_]*$`, ≤64 |
| `NamespacedTag` | `^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$`, ≤96 |
| `SpanishText` | texto normalizado, longitud ≥1 |
| `NotesText` | texto normalizado, ≤500 |
| `Interval` | `{lower, upper}`, ambos o ninguno, `lower ≤ upper` |

