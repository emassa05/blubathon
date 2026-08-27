# Blubathon

Blubathon es una aplicación de seguimiento diario para quien cuida a un niño o
niña con necesidades de apoyo. Cada día se responde un formulario breve sobre
cómo fue el día, sueño, alimentación, rutina, regulación, asistencia y a partir de
ese historial Blubathon devuelve tres cosas, una estimación de riesgo para las
próximas 24 horas, una sugerencia de apoyo con su fuente citada, y una pregunta
de cierre para confirmar qué pasó realmente.

Ese último paso permite no aprender de lo que predijo, sino de lo que se le confirmó que ocurrió.

---

## Qué permite hacer

**Registrar el día sin que sea una carga.** El formulario es extenso pero Blubathon no pregunta lo mismo cada vez. Ordena las preguntas según qué falta hace: primero
lo que lleva una semana sin responderse, después un campo elegido a propósito
para no dejar zonas ciegas, después lo que más información aporta. Dos o tres
preguntas quedan destacadas; el resto sigue accesible para quien quiera
responderlo.

**Rellenar menos.** Si un campo se ha respondido igual de forma consistente
durante los últimos dos meses, Blubathon propone ese valor. La propuesta se
marca como propuesta y el campo sigue vacío hasta que se toque, una sugerencia
no cuenta como respuesta.

**Ver una estimación con su incertidumbre, o ninguna.** El riesgo del día sale
de la tasa observada del propio niño en episodios anteriores comparables, no de
un promedio poblacional. Viene con un intervalo, no con una cifra sola. Y cuando
no hay historial suficiente menos de cinco resultados confirmados, o
información en conflicto no muestra número. Dice que no sabe.

**Recibir una sugerencia que se puede rastrear.** La recomendación del día se
redacta a partir de documentos cargados en el corpus. El texto está escrito en
palabras propias, pero cada afirmación declara de qué fragmento salió, y ese
fragmento tiene que ser uno de los que se le entregaron al redactar. Si una cita
apunta a una fuente que no se recuperó, la recomendación no se muestra: se
declara abstenida, con el motivo. No hay consejo sin procedencia.

**Cerrar el círculo.** Después de cada día registrado queda abierta una pregunta
¿ocurrió el evento en la ventana declarada? con plazo. Responderla es lo que
alimenta la estimación siguiente.

**Decir que una sugerencia no sirvió.** Marcarla como mala no es responder una
encuesta: descarta los fragmentos que se usaron y vuelve a redactar con otros.

---

## Qué no hace

No diagnostica, no indica tratamientos y no reemplaza el criterio profesional.

No vigila emergencias ni envía alertas. Ante peligro inmediato, sigue de inmediato los protocolos de emergencia o resguardo.

---

## Cómo correrlo

Requisitos: Python 3.12, pnpm 9 y [Ollama](https://ollama.com).

**1. Instalar.**

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
pnpm install
ollama pull qwen2.5:14b
```

**2. Montar la base.**

```bash
.venv/bin/python -m tools.demo --reset
```

**3. Levantar Ollama.**

```bash
ollama serve
```

**4. Levantar el backend.**

```bash
BLUBATHON_P1_ADAPTERS=real \
BLUBATHON_DRAFT_LLM=ollama \
BLUBATHON_OLLAMA_MODEL=qwen2.5:14b \
  .venv/bin/python -m uvicorn "apps.api.main:create_app" --factory --port 8000
```

**5. Levantar la interfaz.**

```bash
pnpm --dir apps/mobile dev
```

http://localhost:5173

---

### Corpus propio

Los archivos en `data/local_corpus/` (`.pdf`, `.txt`, `.md`) entran en el
próximo `tools.demo`. Para cargar uno desde otra ruta:

```bash
.venv/bin/python -m tools.rag_authoring.load_local --db data/blubathon.db \
    --title "Guía de apoyos" --file /ruta/guia.pdf
```

### Pruebas

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
pnpm --dir apps/mobile test
```

Después de tocar `rag/authoring/prompts/`:

```bash
.venv/bin/python -m tools.rag_authoring manifest
```
