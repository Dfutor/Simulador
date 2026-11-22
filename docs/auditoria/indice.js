const listado = document.querySelector("#indice-auto");
if (listado) {
  for (const encabezado of document.querySelectorAll("main h2[id]")) {
    const elemento = document.createElement("li");
    const enlace = document.createElement("a");
    enlace.href = "#" + encabezado.id;
    enlace.textContent = encabezado.textContent;
    elemento.append(enlace);
    listado.append(elemento);
  }
}
