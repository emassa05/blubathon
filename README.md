# Blubathon

Blubathon es una aplicación de seguimiento diario para quien cuida a un niño o
niña con necesidades de apoyo. Cada día se responde un formulario breve sobre
cómo fue el día —sueño, alimentación, rutina, regulación, asistencia— y a partir de
ese historial Blubathon devuelve tres cosas: una estimación de riesgo para las
próximas 24 horas, una sugerencia de apoyo con su fuente citada, y una pregunta
de cierre para confirmar qué pasó realmente.

Ese último paso es el que sostiene todo lo demás. Blubathon no aprende de lo que
predijo, sino de lo que se le confirmó que ocurrió.

---

## Qué permite hacer

**Registrar el día sin que sea una carga.** El formulario tiene 19 campos, pero
no pregunta los 19 cada vez. Ordena las preguntas según qué falta hace: primero
lo que lleva una semana sin responderse, después un campo elegido a propósito
para no dejar zonas ciegas, después lo que más información aporta. Dos o tres
preguntas quedan destacadas; el resto sigue accesible para quien quiera
responderlo.

**Rellenar menos.** Si un campo se ha respondido igual de forma consistente
durante los últimos dos meses, Blubathon propone ese valor. La propuesta se
marca como propuesta y el campo sigue vacío hasta que se toque: una sugerencia
no cuenta como respuesta.

**Ver una estimación con su incertidumbre, o ninguna.** El riesgo del día sale
de la tasa observada del propio niño en episodios anteriores comparables, no de
un promedio poblacional. Viene con un intervalo, no con una cifra sola. Y cuando
no hay historial suficiente —menos de cinco resultados confirmados, o
información en conflicto— no muestra número. Dice que no sabe.

**Recibir una sugerencia que se puede rastrear.** La recomendación del día se
redacta a partir de documentos cargados en el corpus, y cada cita tiene que ser
literal de uno de ellos. Si el texto generado no se puede anclar a una fuente,
la recomendación no se muestra: se declara abstenida, con el motivo. No hay
consejo sin procedencia.

**Cerrar el círculo.** Después de cada día registrado queda abierta una pregunta
—¿ocurrió el evento en la ventana declarada?— con plazo. Responderla es lo que
alimenta la estimación siguiente.

**Decir que una sugerencia no sirvió.** Marcarla como mala no es responder una
encuesta: descarta los fragmentos que se usaron y vuelve a redactar con otros.

---

## Qué no hace

Está escrito en la propia aplicación, no solo aquí:

> Faro organiza registros, calcula estadísticas personales y muestra
> estimaciones experimentales. No diagnostica, no indica tratamientos y no
> reemplaza el criterio profesional.

> Faro no vigila emergencias ni envía alertas. Ante peligro inmediato, sigue de
> inmediato los protocolos de emergencia o resguardo de tu localidad.

(Los textos de la aplicación y el paquete `@faro/contract` todavía dicen
«Faro», el nombre anterior del producto.)

No es monitoreo pasivo: no hay sensores ni dispositivos, todo lo que sabe se lo
contó una persona. No sustituye una consulta. Y no se guarda texto libre ni
identidad en la parte que consulta al modelo de lenguaje: la redacción solo ve
los fragmentos recuperados del corpus.

---

## Cómo se ve

La interfaz es una sola pantalla, **Salud**, y el riesgo del día no cambia solo
una cifra: cambia el color de la pantalla entera. Cuatro estados —desconocido en
gris, bajo en celeste, medio en amarillo, alto en rojo— con un horizonte
dibujado que se agita más según sube el riesgo. Cuando no hay estimación, la
pantalla se pone gris y escribe un guion, porque pintar la ausencia de dato de
celeste se leería como riesgo bajo.

Debajo van la recomendación del día con sus citas, lo que el formulario prioriza
preguntar hoy, y los últimos cuatro días con su estado de respuesta.

---

## Cómo correrlo

Hacen falta las dos mitades. Primero el backend, con datos de demostración:

```bash
python -m tools.seed
uvicorn "apps.api.main:create_app" --factory --port 8000
```

Y después la interfaz:

```bash
pnpm install
pnpm --dir apps/mobile dev        # http://localhost:5173
```

Así arranca en modo demo, con adaptadores simulados y sin redacción por modelo
de lenguaje. Para correr el dominio real y el RAG completo:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
BLUBATHON_P1_ADAPTERS=real BLUBATHON_DRAFT_LLM=anthropic \
  uvicorn "apps.api.main:create_app" --factory --port 8000
```

También corre contra un modelo local servido por Ollama
(`BLUBATHON_DRAFT_LLM=ollama`).

Para cargar documentos propios al corpus que consulta la recomendación:

```bash
python -m tools.rag_authoring.load_local --db data/blubathon.db \
    --title "Guía de apoyos" --file guia.pdf
```

---

## El estado del proyecto

Los datos de demostración son ficticios y la definición del evento objetivo
también: no viene de un consenso clínico ni de una guía publicada. El modelo
retador está entrenado pero nunca expuesto. La pantalla hoy solo lee —el
formulario se puede enviar por la API, pero todavía no hay vista para
responderlo—.

---

## Dónde está el resto

| Documento | Qué cubre |
|---|---|
| [`docs/backend.md`](docs/backend.md) | La API completa, el modelo predictivo, el orden del formulario, el pipeline RAG |
| [`apps/mobile/README.md`](apps/mobile/README.md) | La pantalla: bandas de color, layout, accesibilidad, contrastes verificados |
