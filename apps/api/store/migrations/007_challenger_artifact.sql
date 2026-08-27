-- El artefacto del challenger se hasheaba y se tiraba.
--
-- `tools/train` serializaba `{intercept, beta_sleep, beta_regulation, penalty}`
-- solo para calcular `artifact_sha256`, y los coeficientes se perdían con el
-- proceso. Sin ellos el runtime no puede puntuar: por eso el track abstenía con
-- `model_state_not_shadow` incluso con una versión publicada en `shadow`.
--
-- El hash se queda: sigue siendo la identidad del artefacto y lo que permite
-- comprobar que lo cargado es lo que se entrenó.
ALTER TABLE model_versions ADD COLUMN artifact TEXT;
