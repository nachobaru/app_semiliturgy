"use strict";
/* Editor estático de la hoja de liturgia. Los borradores vienen pregenerados en datos.json
   (scripts/generar_sitio.py); aquí solo se edita, se maqueta y se exporta. */

const CLAVE = "semiliturgy:v1:";
const SECCIONES = ["laudes", "eucaristia", "cantos", "visperas"];
const MOMENTOS = ["entrada", "ofertorio", "comunion"];
const ETIQ = { laudes: "Laudes", eucaristia: "Eucaristía", visperas: "Vísperas", cantos: "Cantos",
  de: "De", himno: "Himno", salmodia: "Salmodia", benedictus: "Benedictus", magnificat: "Magnificat",
  formulario: "Formulario", prefacio: "Prefacio", entrada: "Entrada", ofertorio: "Ofertorio", comunion: "Comunión" };

let datos, actual = null, hoja = null;
const $ = (id) => document.getElementById(id);

/* ---------- almacenamiento local (puede fallar: modo privado, datos bloqueados) ---------- */
function leerLocal(id) {
  try { const t = localStorage.getItem(CLAVE + id); return t ? JSON.parse(t) : null; } catch (e) { return null; }
}
function guardarLocal(id, h) {
  try { localStorage.setItem(CLAVE + id, JSON.stringify(h)); return true; } catch (e) { return false; }
}
function borrarLocal(id) { try { localStorage.removeItem(CLAVE + id); } catch (e) { /* nada */ } }

/* ---------- fechas ---------- */
function domingoDe(iso) {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() - d.getUTCDay());
  return d.toISOString().slice(0, 10);
}

/* ---------- maqueta de la hoja (equivale a semiliturgy/plantillas/hoja.html) ---------- */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const NUM = /^\s*(\d{1,3})\s*·/;
function canto(t) {
  const m = NUM.exec(t || "");
  return m ? `${esc(t.slice(m[0].length).trim())} <span class="n">(n.º ${m[1]})</span>` : esc(t);
}
const campo = (et, v) => `<p class="campo"><b>${et}:</b> ${esc(v)}</p>`;

function celdaDia(d) {
  let h = `<td><div class="cab"><div class="dia">${esc(d.dia)}</div><div class="celeb">${esc(d.celebracion)}</div></div><div class="cuerpo">`;
  if (d.laudes) {
    h += `<div class="titbloque">${d.laudes_con_eucaristia && d.eucaristia ? "Laudes y Eucaristía" : "Laudes"}</div>`;
    if (d.laudes.himno) h += campo("Himno", d.laudes.himno);
    h += campo("Salmodia", d.laudes.salmodia) + campo("Benedictus", d.laudes.benedictus);
  }
  if (d.eucaristia) {
    if (!(d.laudes && d.laudes_con_eucaristia)) h += `<div class="titbloque">Eucaristía</div>`;
    h += campo("Formulario", d.eucaristia.formulario) + campo("Prefacio", d.eucaristia.prefacio);
  }
  if (d.visperas) {
    h += `<div class="titbloque">${d.visperas.de ? "I Vísperas" : "Vísperas"}</div>`;
    if (d.visperas.de) h += campo("De", d.visperas.de);
    if (d.visperas.himno) h += campo("Himno", d.visperas.himno);
    h += campo("Salmodia", d.visperas.salmodia) + campo("Magnificat", d.visperas.magnificat);
  }
  return h + "</div></td>";
}

function lateral(h, filas) {
  let c = "";
  for (const d of h.dias) {
    if (!d.cantos || !Object.values(d.cantos).some(Boolean)) continue;
    c += `<div class="diacantos">${esc(d.dia)}</div>`;
    for (const [m, et] of [["entrada", "Entrada"], ["ofertorio", "Ofertorio"], ["comunion", "Comunión"]]) {
      if (d.cantos[m]) c += `<p class="campo">${et}: ${canto(d.cantos[m])}</p>`;
    }
  }
  return `<td class="lateral" rowspan="${filas}"><div class="cab semana">${esc(h.titulo)}</div><div class="cuerpo">
    <p class="campo"><b>SEMANA DE SALTERIO: ${esc(h.salterio)}</b></p><p class="campo"><b>TIEMPO: ${esc(h.tiempo)}</b></p>
    <div class="titbloque">Cantos</div>${c}
    <div class="titbloque" style="margin-top:10px">Avisos</div><div class="avisos">${esc(h.avisos || "")}</div></div></td>`;
}

function renderHoja(h) {
  const filas = [];
  for (let i = 0; i < h.dias.length; i += 3) filas.push(h.dias.slice(i, i + 3));
  const cuerpo = filas.map((fila, i) =>
    `<tr>${i === 0 ? lateral(h, filas.length) : ""}${fila.map(celdaDia).join("")}${"<td></td>".repeat(3 - fila.length)}</tr>`).join("");
  return `<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Hoja de liturgia · ${esc(h.titulo)}</title>
<style>${datos.css}</style></head><body><h1>HOJA LITURGIA</h1><table class="hoja">${cuerpo}</table></body></html>`;
}

/* ---------- YAML (estructura simple: dicts, listas y cadenas) ---------- */
const escalar = (v) => v === null || v === undefined ? "null" : typeof v === "string" ? JSON.stringify(v) : String(v);
const clave = (k) => /^[A-Za-z_]\w*$/.test(k) ? k : JSON.stringify(k);
const vacio = (v) => v && typeof v === "object" && Object.keys(v).length === 0;
function lineas(v, n) {
  const sp = " ".repeat(n), out = [];
  if (Array.isArray(v)) {
    for (const it of v) {
      if (it && typeof it === "object" && !vacio(it)) {
        const sub = lineas(it, n + 2);
        sub[0] = sp + "- " + sub[0].slice(n + 2);
        out.push(...sub);
      } else out.push(`${sp}- ${vacio(it) ? (Array.isArray(it) ? "[]" : "{}") : escalar(it)}`);
    }
  } else {
    for (const [k, x] of Object.entries(v)) {
      if (x && typeof x === "object" && !vacio(x)) out.push(`${sp}${clave(k)}:`, ...lineas(x, n + 2));
      else out.push(`${sp}${clave(k)}: ${vacio(x) ? (Array.isArray(x) ? "[]" : "{}") : escalar(x)}`);
    }
  }
  return out;
}
const aYaml = (h) => "# Hoja de liturgia exportada desde la web. Súbela a semanas/ para que cuente en el historial de cantos.\n"
  + lineas(h, 0).join("\n") + "\n";

/* ---------- interfaz ---------- */
function estado(txt) { $("estado").textContent = txt; }
function aviso(txt) { const a = $("aviso"); a.hidden = !txt; a.textContent = txt || ""; }

function guardar() {
  estado(guardarLocal(actual, hoja) ? "Cambios guardados en este navegador." : "No se pudo guardar en el navegador: descarga el YAML.");
  refrescarSelector();
}

function entrada(et, valor, onInput, lista) {
  const l = document.createElement("label"); l.textContent = et;
  const i = document.createElement("input"); i.type = "text"; i.value = valor ?? "";
  if (lista) i.setAttribute("list", lista);
  i.addEventListener("input", () => onInput(i.value));
  l.appendChild(i); return l;
}

function pintarEditor() {
  const ed = $("editor"); ed.replaceChildren();
  const t = document.createElement("h2"); t.textContent = hoja.titulo; ed.appendChild(t);
  const sub = document.createElement("div"); sub.className = "estado";
  sub.textContent = `Salterio ${hoja.salterio} · Tiempo ${hoja.tiempo}`; ed.appendChild(sub);
  if (hoja.notas && hoja.notas.length) {
    const det = document.createElement("details"); det.className = "notas"; det.open = true;
    const s = document.createElement("summary"); s.textContent = "Avisos de la app (no salen en la hoja)"; det.appendChild(s);
    const ul = document.createElement("ul");
    for (const n of hoja.notas) { const li = document.createElement("li"); li.textContent = n; ul.appendChild(li); }
    det.appendChild(ul); ed.appendChild(det);
  }
  ed.appendChild(entrada("Título de la hoja", hoja.titulo, (v) => { hoja.titulo = v; guardar(); }));
  const grid = document.createElement("div"); grid.className = "dias";
  for (const dia of hoja.dias) {
    const c = document.createElement("div"); c.className = "dia";
    c.innerHTML = "<h3></h3><div class='color'></div>";
    c.querySelector("h3").textContent = `${dia.dia} ${dia.fecha.slice(8)}`;
    c.querySelector(".color").textContent = dia.color || "";
    c.appendChild(entrada("Celebración", dia.celebracion, (v) => { dia.celebracion = v; guardar(); }));
    for (const sec of SECCIONES) {
      const bloque = dia[sec];
      if (!bloque && sec !== "cantos") continue;
      const fs = document.createElement("fieldset"), lg = document.createElement("legend");
      lg.textContent = ETIQ[sec] + (sec === "visperas" && bloque.de ? " (I Vísperas)" : ""); fs.appendChild(lg);
      const claves = sec === "cantos" ? [...new Set([...Object.keys(bloque || {}), ...MOMENTOS])] : Object.keys(bloque);
      for (const k of claves) {
        const lista = sec === "cantos" ? "lista-cantos" : k === "himno" ? "lista-himnos" : null;
        fs.appendChild(entrada(ETIQ[k] || k, (bloque || {})[k], (v) => { (dia[sec] = dia[sec] || {})[k] = v; guardar(); }, lista));
      }
      c.appendChild(fs);
    }
    grid.appendChild(c);
  }
  ed.appendChild(grid);
  const l = document.createElement("label"); l.textContent = "Avisos de la semana (salen en la hoja)"; l.style.marginTop = "16px";
  const ta = document.createElement("textarea"); ta.value = hoja.avisos || "";
  ta.addEventListener("input", () => { hoja.avisos = ta.value; guardar(); });
  l.appendChild(ta); ed.appendChild(l);
}

function vistaPrevia() {
  const f = $("previa"); f.hidden = false; f.srcdoc = renderHoja(hoja);
}

function abrir(id) {
  if (!datos.semanas[id]) {
    const ids = Object.keys(datos.semanas);
    aviso(`No hay borrador para la semana del ${id}. Disponibles: del ${ids[0]} al ${ids[ids.length - 1]}.`);
    return;
  }
  aviso(null); actual = id;
  const local = leerLocal(id);
  hoja = local || JSON.parse(JSON.stringify(datos.semanas[id]));
  $("semana").value = id; $("fecha").value = id;
  estado(local ? "Se han cargado tus cambios guardados en este navegador." : "Borrador sin tocar.");
  $("acciones").hidden = false;
  pintarEditor(); vistaPrevia();
}

function refrescarSelector() {
  const s = $("semana"), previo = actual;
  for (const o of s.options) o.textContent = o.dataset.base + (leerLocal(o.value) ? "  ✎" : "");
  if (previo) s.value = previo;
}

async function iniciar() {
  try { datos = await (await fetch("datos.json")).json(); }
  catch (e) { aviso("No se pudieron cargar los datos. Abre la página desde su dirección web, no como fichero."); return; }
  for (const [lista, valores] of [["lista-cantos", datos.cantos], ["lista-himnos", datos.himnos]]) {
    const dl = document.createElement("datalist"); dl.id = lista;
    for (const v of valores) { const o = document.createElement("option"); o.value = v; dl.appendChild(o); }
    document.body.appendChild(dl);
  }
  const sel = $("semana");
  for (const [id, h] of Object.entries(datos.semanas)) {
    const o = document.createElement("option"); o.value = id; o.dataset.base = `${id} · ${h.titulo}`; sel.appendChild(o);
  }
  refrescarSelector();
  sel.addEventListener("change", () => abrir(sel.value));
  $("fecha").addEventListener("change", (e) => e.target.value && abrir(domingoDe(e.target.value)));
  $("vista").addEventListener("click", vistaPrevia);
  $("imprimir").addEventListener("click", () => {
    const f = $("previa"); f.hidden = false; f.srcdoc = renderHoja(hoja);
    f.onload = () => { f.onload = null; f.contentWindow.focus(); f.contentWindow.print(); };
  });
  $("yaml").addEventListener("click", () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([aYaml(hoja)], { type: "text/yaml;charset=utf-8" }));
    a.download = `${actual}.yaml`; a.click(); URL.revokeObjectURL(a.href);
  });
  $("restaurar").addEventListener("click", () => {
    if (confirm("Se descartarán tus cambios de esta semana y volverá el borrador original. ¿Seguir?")) {
      borrarLocal(actual); abrir(actual); refrescarSelector();
    }
  });
  const hoy = new Date().toISOString().slice(0, 10), ids = Object.keys(datos.semanas);
  abrir(datos.semanas[domingoDe(hoy)] ? domingoDe(hoy) : ids[0]);
}
iniciar();
