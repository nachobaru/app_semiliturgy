// Genera las PNG del icono de Ordo a partir de sitio_src/icono.svg.
//
//   node scripts/generar_iconos.js [ruta/a/eb-garamond-latin-600-normal.woff2]
//
// Necesita Playwright con Chromium. La fuente (EB Garamond, licencia OFL) es opcional: si no se
// pasa, se usa la serif del sistema. Solo se usa para renderizar: la web no carga ninguna fuente.
// En el tamaño pequeño (32 px) se quitan la cruz y el filete para que la palabra se lea.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const raiz = path.resolve(__dirname, "..");
const svg = fs.readFileSync(path.join(raiz, "sitio_src", "icono.svg"), "utf8");
const fuente = process.argv[2];
const fontFace = fuente
  ? `@font-face { font-family: "EB Garamond"; font-weight: 600;
       src: url(data:font/woff2;base64,${fs.readFileSync(fuente).toString("base64")}) format("woff2"); }`
  : "";
const PEQUENO = `.cruz, .filete { display: none }
  .palabra { font-size: 212px; font-weight: 700; transform: translateY(-50px); }`;

(async () => {
  const b = await chromium.launch();
  for (const lado of [32, 180, 192, 512]) {
    const p = await b.newPage({ viewport: { width: lado, height: lado }, deviceScaleFactor: 1 });
    await p.setContent(`<!doctype html><style>${fontFace} html,body{margin:0;background:transparent}
      svg{display:block;width:${lado}px;height:${lado}px} ${lado <= 48 ? PEQUENO : ""}</style>${svg}`);
    await p.evaluate(() => document.fonts.ready);
    const destino = path.join(raiz, "sitio_src", `icono-${lado}.png`);
    await p.screenshot({ path: destino, omitBackground: true });
    console.log(destino);
    await p.close();
  }
  await b.close();
})();
