// Interacción del manual: índice, sección actual, visor de capturas, copiar comandos y preguntas desplegables.
const encabezados = [...document.querySelectorAll("main h2[id]")];

function llenarIndice(lista) {
  for (const encabezado of encabezados) {
    const elemento = document.createElement("li");
    const enlace = document.createElement("a");
    enlace.href = "#" + encabezado.id;
    enlace.textContent = encabezado.dataset.corto || encabezado.textContent;
    elemento.append(enlace);
    lista.append(elemento);
  }
}

const indice = document.querySelector("#indice-auto");
const indiceMovil = document.querySelector("#indice-movil");
if (indice) llenarIndice(indice);
if (indiceMovil) {
  llenarIndice(indiceMovil);
  indiceMovil.addEventListener("click", (evento) => {
    if (evento.target.closest("a")) indiceMovil.closest("details").open = false;
  });
}

// Marca en el índice la sección que se está leyendo
if (indice && encabezados.length) {
  const enlaces = [...indice.querySelectorAll("a")];
  let pendiente = false;
  const marcar = () => {
    pendiente = false;
    let actual = 0;
    encabezados.forEach((encabezado, posicion) => {
      if (encabezado.getBoundingClientRect().top < 140) actual = posicion;
    });
    if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 4) actual = encabezados.length - 1;
    enlaces.forEach((enlace, posicion) => enlace.classList.toggle("activo", posicion === actual));
  };
  window.addEventListener("scroll", () => {
    if (!pendiente) { pendiente = true; requestAnimationFrame(marcar); }
  }, { passive: true });
  marcar();
}

// Capturas: clic para verlas en grande
const visor = document.createElement("dialog");
visor.className = "visor";
visor.innerHTML = '<img alt=""><button type="button" aria-label="Cerrar">×</button>';
document.body.append(visor);
document.addEventListener("click", (evento) => {
  const imagen = evento.target.closest("figure img");
  if (!imagen || typeof visor.showModal !== "function") return;
  const grande = visor.querySelector("img");
  grande.src = imagen.currentSrc || imagen.src;
  grande.alt = imagen.alt;
  visor.showModal();
});
visor.addEventListener("click", () => visor.close());

// Botón para copiar comandos
for (const bloque of document.querySelectorAll("pre")) {
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "copiar";
  boton.textContent = "Copiar";
  boton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText((bloque.querySelector("code") ?? bloque).innerText.trim());
      boton.textContent = "Copiado";
    } catch {
      boton.textContent = "No se pudo";
    }
    setTimeout(() => { boton.textContent = "Copiar"; }, 1600);
  });
  bloque.append(boton);
}

// Preguntas: abrir o cerrar todas, abrir la del enlace y abrirlas todas al imprimir
const preguntas = [...document.querySelectorAll("details.pregunta")];
for (const boton of document.querySelectorAll("[data-desplegar]")) {
  const actualizar = () => { boton.textContent = preguntas.every((pregunta) => pregunta.open) ? "Cerrar todas" : "Abrir todas"; };
  boton.addEventListener("click", () => {
    const abrir = !preguntas.every((pregunta) => pregunta.open);
    preguntas.forEach((pregunta) => { pregunta.open = abrir; });
    actualizar();
  });
  preguntas.forEach((pregunta) => pregunta.addEventListener("toggle", actualizar));
}
function abrirPreguntaDelEnlace() {
  const destino = location.hash ? document.getElementById(decodeURIComponent(location.hash.slice(1))) : null;
  if (destino && destino.matches("details")) destino.open = true;
}
abrirPreguntaDelEnlace();
window.addEventListener("hashchange", abrirPreguntaDelEnlace);
window.addEventListener("beforeprint", () => preguntas.forEach((pregunta) => { pregunta.open = true; }));
