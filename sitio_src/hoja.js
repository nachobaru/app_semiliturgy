"use strict";
/* Maqueta de la hoja impresa para la web. Es la misma que semiliturgy/plantillas/hoja.html (Jinja):
   si cambias el marcado aquí, cámbialo allí (tests/test_hoja.py::test_paridad_con_la_web lo comprueba).
   El CSS y el script de ajuste no se duplican: generar_sitio.py los saca de hoja.html a datos.json. */
(function (raiz) {
  // Mismo escapado que Jinja/MarkupSafe
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&#34;", "'": "&#39;" }[c]));
  const NUM = /^\s*(\d{1,3})\s*·/;
  function canto(t) {
    const m = NUM.exec(t || "");
    return m ? `${esc(t.slice(m[0].length).trim())} <span class="n">(n.º ${m[1]})</span>` : esc(t);
  }
  const campo = (et, v) => `<p class="campo"><b>${et}:</b> ${esc(v)}</p>`;
  const MOMENTOS = [["entrada", "Entrada"], ["ofertorio", "Ofertorio"], ["comunion", "Comunión"]];

  function dia(d) {
    let h = `<section class="dia" data-color="${esc(d.color)}">`
      + `<div class="cab"><div class="fila"><span class="nombre">${esc(d.dia)}</span>`
      + `<span class="num">${parseInt(d.fecha.slice(8), 10)}</span></div>`
      + `<div class="celeb">${esc(d.celebracion)}</div></div><div class="cuerpo">`;
    if (d.laudes) {
      h += `<div class="bloque"><h3>${d.laudes_con_eucaristia && d.eucaristia ? "Laudes y Eucaristía" : "Laudes"}</h3>`;
      if (d.laudes.himno) h += campo("Himno", d.laudes.himno);
      h += campo("Salmodia", d.laudes.salmodia) + campo("Benedictus", d.laudes.benedictus) + "</div>";
    }
    if (d.eucaristia) {
      h += `<div class="bloque">${d.laudes && d.laudes_con_eucaristia ? "" : "<h3>Eucaristía</h3>"}`
        + campo("Formulario", d.eucaristia.formulario) + campo("Prefacio", d.eucaristia.prefacio) + "</div>";
    }
    if (d.cantos && Object.values(d.cantos).some(Boolean)) {
      h += `<div class="bloque cantos-dia"><h3>Cantos</h3>`;
      for (const [m, et] of MOMENTOS) if (d.cantos[m]) h += `<p><i>${et}:</i> ${canto(d.cantos[m])}</p>`;
      h += "</div>";
    }
    if (d.visperas) {
      h += `<div class="bloque"><h3>${d.visperas.de ? "I Vísperas" : "Vísperas"}</h3>`;
      if (d.visperas.de) h += campo("De", d.visperas.de);
      if (d.visperas.himno) h += campo("Himno", d.visperas.himno);
      h += campo("Salmodia", d.visperas.salmodia) + campo("Magnificat", d.visperas.magnificat) + "</div>";
    }
    return h + "</div></section>";
  }

  function renderHoja(h, css, ajuste) {
    return `<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Hoja de liturgia · ${esc(h.titulo)}</title>`
      + `<style>${css || ""}</style></head><body><div class="pagina">`
      + `<header class="cabecera"><div class="marca">HOJA LITURGIA</div><h1>${esc(h.titulo)}</h1>`
      + `<div class="datos">SEMANA DE SALTERIO: ${esc(h.salterio)}<span>·</span>TIEMPO: ${esc(h.tiempo)}</div></header>`
      + `<main class="cuerpo-hoja">${h.dias.map(dia).join("")}</main>`
      + `<footer class="pie"><h2>Avisos</h2><div class="avisos">${esc(h.avisos || "")}</div></footer>`
      + `</div><script>${ajuste || ""}<\/script></body></html>`;
  }

  raiz.renderHoja = renderHoja;
  if (typeof module !== "undefined" && module.exports) module.exports = { renderHoja };
})(typeof window !== "undefined" ? window : globalThis);
