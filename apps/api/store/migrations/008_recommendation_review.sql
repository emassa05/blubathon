-- La decisión profesional sobre una recomendación viva.
--
-- Tabla propia, y no la `recommendation_reviews` de la migración 003: aquella
-- revisa una `strategy_version` del catálogo P1 —columna obligatoria, con clave
-- foránea— y una recomendación redactada por el RAG no tiene estrategia que
-- referenciar. Reutilizarla obligaría a inventar una fila de catálogo por cada
-- borrador solo para poder firmarlo.
--
-- También aparte de `recommendation_feedback`: el rating del cuidador ("no me
-- sirvió") y el visto bueno del profesional ("esto puede entregarse") son dos
-- hechos con dos autores y dos consecuencias. Un `bad` redacta de nuevo; un
-- `rejected` no. En la misma columna sería imposible contar cuántas pasaron
-- revisión sin contar también las quejas.
--
-- Append-only, como el resto del registro clínico: cambiar de opinión inserta
-- otra fila y la anterior sigue siendo auditable. Por eso no hay UNIQUE sobre
-- `recommendation_instance_id` y la vigente es la última por `reviewed_at`.
CREATE TABLE recommendation_decisions (
    decision_id                TEXT PRIMARY KEY,
    recommendation_instance_id TEXT NOT NULL
                                    REFERENCES recommendation_instances(recommendation_instance_id),
    decision                   TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    -- El rol queda escrito en la fila y no se deduce de quién consulta: en v0.4
    -- la API no pide sesión, y cuando la pida esta columna ya distingue una
    -- decisión profesional de cualquier otra cosa que llegue por la misma ruta.
    reviewer_role              TEXT NOT NULL DEFAULT 'professional'
                                    CHECK (reviewer_role IN ('professional')),
    note_es                    TEXT,
    reviewed_at                TEXT NOT NULL
);

-- La consulta que sirve la cola: la última decisión de una instancia.
CREATE INDEX ix_decisions_instance
    ON recommendation_decisions(recommendation_instance_id, reviewed_at DESC);
