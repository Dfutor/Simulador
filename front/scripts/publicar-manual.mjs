import { copyFile, cp, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = fileURLToPath(new URL("../../", import.meta.url));
const auditoria = join(raiz, "docs", "auditoria");
const front = join(raiz, "front");

function esFuentePublicable(fuente) {
  return ["README.md", "Levantamiento_de_requrimientos_Cap1COSBUS.md"].includes(fuente)
    || /^simulador2\/[\w]+\.py$/.test(fuente)
    || /^front\/src\/(?:[\w-]+\/)*[\w-]+\.(?:vue|js)$/.test(fuente);
}

export async function prepararArchivosPublicos(comando) {
  const publico = join(front, ".publico", comando);
  const manual = join(publico, "manual");
  await rm(publico, { recursive: true, force: true });
  await cp(join(front, "public"), publico, { recursive: true });
  await cp(auditoria, manual, {
    recursive: true,
    filter: (ruta) => !ruta.endsWith(".pdf") && !(dirname(ruta) === auditoria && ruta.endsWith(".html")),
  });

  const fuentes = new Set();
  const paginas = (await readdir(auditoria)).filter((archivo) => archivo.endsWith(".html"));
  for (const pagina of paginas) {
    const html = await readFile(join(auditoria, pagina), "utf8");
    const publicado = html
      .replace(/href="manual\.html([#"])/g, 'href="./$1')
      .replace(/<a href="\.\.\/\.\.\/([^"#]+)(#[^"]*)?">([\s\S]*?)<\/a>/g, (_, ruta, ancla = "", etiqueta) => {
        const fuente = decodeURIComponent(ruta);
        if (fuente.endsWith(".pdf")) return `<span>${etiqueta} (consulta local)</span>`;
        if (!esFuentePublicable(fuente)) throw new Error(`Fuente no prevista en el manual: ${fuente}`);
        fuentes.add(fuente);
        return `<a href="fuentes/${ruta}.txt${ancla}">${etiqueta}</a>`;
      });
    const destino = pagina === "manual.html" ? "index.html" : pagina;
    await writeFile(join(manual, destino), publicado, "utf8");
  }

  for (const fuente of fuentes) {
    const destino = join(manual, "fuentes", `${fuente}.txt`);
    await mkdir(dirname(destino), { recursive: true });
    await copyFile(join(raiz, fuente), destino);
  }

  return publico;
}
