-- SPEC 14.3. `tools/train` (P1) publica el reporte con el desglose de
-- abstenciones como lista de `AbstentionBreakdown` -razón, conteo y tasa-, no
-- como un mapa de razón a tasa. P2 importa lo que esa herramienta produce, así
-- que la columna toma el nombre y la forma del contrato.
--
-- Las filas anteriores traen el mapa `{razón: tasa}`; se dejan como están y el
-- lector las rechaza en vez de inventarles un conteo.
ALTER TABLE evaluation_reports RENAME COLUMN abstention_by_reason TO abstentions;
