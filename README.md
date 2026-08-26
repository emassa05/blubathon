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
redacta a partir de documentos cargados en el corpus, y cada cita tiene que ser
literal de uno de ellos. Si el texto generado no se puede anclar a una fuente,
la recomendación no se muestra: se declara abstenida, con el motivo. No hay
consejo sin procedencia.

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

El backend, con datos de demostración:

```bash
python -m tools.seed
uvicorn "apps.api.main:create_app" --factory --port 8000
```

Y después la interfaz:

```bash
pnpm install
pnpm --dir apps/mobile dev        # http://localhost:5173
```

Para correr el dominio real y el RAG completo:


(`BLUBATHON_DRAFT_LLM=ollama`).


```bash
python -m tools.rag_authoring.load_local --db data/blubathon.db \
    --title "Guía de apoyos" --file guia.pdf
```
