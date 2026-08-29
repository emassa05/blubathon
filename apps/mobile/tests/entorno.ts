/**
 * Lo que jsdom no trae y el navegador sí.
 *
 * jsdom no calcula disposición, así que no implementa `scrollIntoView`: no es
 * que se comporte distinto, es que el método no existe y llamarlo revienta.
 * Todos los navegadores en los que corre la aplicación lo tienen, así que el
 * componente lo llama sin preguntar y aquí se le da un cuerpo vacío, que es
 * exactamente lo que hace desplazarse en una pantalla que no se pinta.
 */
Element.prototype.scrollIntoView = function scrollIntoView(): void {};

/**
 * Y por lo mismo tampoco hay `ResizeObserver`: sin disposición no hay tamaño
 * que observar, así que nunca notificaría. El doble no llama al callback nunca,
 * que es la verdad en jsdom: todos los elementos miden cero y no cambian.
 */
globalThis.ResizeObserver = class {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
};
