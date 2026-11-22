import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { prepararArchivosPublicos } from "./scripts/publicar-manual.mjs";

function instalarRutaManual(servidor) {
  servidor.middlewares.use((peticion, respuesta, siguiente) => {
    const ruta = new URL(peticion.url, "http://localhost");
    if (ruta.pathname === "/manual") {
      respuesta.writeHead(308, { Location: `/manual/${ruta.search}` }).end();
      return;
    }
    if (ruta.pathname === "/manual/") peticion.url = `/manual/index.html${ruta.search}`;
    siguiente();
  });
}

const rutaManual = { name: "ruta-manual", configureServer: instalarRutaManual, configurePreviewServer: instalarRutaManual };

export default defineConfig(async ({ command, isPreview }) => ({
  plugins: [vue(), rutaManual],
  publicDir: isPreview ? false : await prepararArchivosPublicos(command),
  server: { proxy: { "/api": "http://localhost:8000" } },
}));
