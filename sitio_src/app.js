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

/* La maqueta de la hoja impresa está en hoja.js (renderHoja). */

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
const aYaml = (h) => {
  const limpia = JSON.parse(JSON.stringify(h));
  for (const d of limpia.dias) { delete d.opciones; delete d.opcion; delete d.adecuados; }   // en el YAML solo queda lo elegido
  return aYamlTexto(limpia);
};
const aYamlTexto = (h) => "# Hoja de liturgia exportada desde la web. Súbela a semanas/ para que cuente en el historial de cantos.\n"
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

const CAMPOS_VARIANTE = ["celebracion", "color", "laudes_con_eucaristia", "laudes", "eucaristia", "cantos", "visperas", "adecuados"];

/* Cambia la opción de un día: guarda lo editado en la variante actual y carga la elegida. */
function elegirOpcion(dia, i) {
  if (i === dia.opcion) return;
  const actualV = dia.opciones[dia.opcion];
  for (const k of CAMPOS_VARIANTE) { if (k in dia) actualV[k] = dia[k]; else delete actualV[k]; }
  for (const k of CAMPOS_VARIANTE) delete dia[k];
  const nueva = JSON.parse(JSON.stringify(dia.opciones[i]));
  for (const k of CAMPOS_VARIANTE) if (k in nueva) dia[k] = nueva[k];
  dia.opcion = i;
}

function selectorOpciones(dia, alCambiar) {
  const caja = document.createElement("div"); caja.className = "opciones";
  caja.setAttribute("role", "radiogroup"); caja.setAttribute("aria-label", "Celebración del día");
  const t = document.createElement("div"); t.className = "tit"; t.textContent = "Este día hay varias opciones"; caja.appendChild(t);
  dia.opciones.forEach((o, i) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "opcion";
    b.setAttribute("role", "radio"); b.setAttribute("aria-checked", String(i === dia.opcion));
    const peq = document.createElement("small"); peq.textContent = o.tipo || "";
    b.append(peq, document.createTextNode(o.etiqueta));
    b.addEventListener("click", () => { elegirOpcion(dia, i); alCambiar(); });
    caja.appendChild(b);
  });
  return caja;
}

function tarjetaDia(dia) {
  const c = document.createElement("div"); c.className = "dia"; c.dataset.color = dia.color || "";
  const cab = document.createElement("div"); cab.className = "dia-cab";
  cab.innerHTML = "<h3></h3><span class='num'></span>";
  cab.querySelector("h3").textContent = dia.dia; cab.querySelector(".num").textContent = dia.fecha.slice(8);
  c.appendChild(cab);
  const col = document.createElement("div"); col.className = "color"; col.textContent = "Color litúrgico: " + (dia.color || "—");
  c.appendChild(col);
  if (dia.opciones && dia.opciones.length > 1) {
    c.appendChild(selectorOpciones(dia, () => {
      guardar(); c.replaceWith(tarjetaDia(dia)); vistaPrevia();
    }));
  }
  c.appendChild(entrada("Celebración", dia.celebracion, (v) => { dia.celebracion = v; guardar(); }));
  for (const sec of SECCIONES) {
    const bloque = dia[sec];
    if (!bloque && sec !== "cantos") continue;
    const fs = document.createElement("fieldset"), lg = document.createElement("legend");
    lg.textContent = ETIQ[sec] + (sec === "visperas" && bloque.de ? " (I Vísperas)" : ""); fs.appendChild(lg);
    const claves = sec === "cantos" ? [...new Set([...Object.keys(bloque || {}), ...MOMENTOS])] : Object.keys(bloque);
    for (const k of claves) {
      if (sec === "cantos") { fs.appendChild(campoCanto(dia, k)); continue; }
      const lista = k === "himno" ? "lista-himnos" : null;
      fs.appendChild(entrada(ETIQ[k] || k, (bloque || {})[k], (v) => { (dia[sec] = dia[sec] || {})[k] = v; guardar(); }, lista));
    }
    c.appendChild(fs);
  }
  return c;
}

/* ---------- selector de cantos ---------- */
let CAT = new Map();
const normalizar = (t) => String(t).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

function campoCanto(dia, k) {
  const poner = (v) => { (dia.cantos = dia.cantos || {})[k] = v; guardar(); };
  const l = entrada(ETIQ[k] || k, (dia.cantos || {})[k], poner);
  const input = l.querySelector("input");
  const fila = document.createElement("div"); fila.className = "fila-campo";
  const b = document.createElement("button"); b.type = "button"; b.className = "sec elegir"; b.textContent = "Elegir";
  b.setAttribute("aria-label", `Elegir canto de ${(ETIQ[k] || k).toLowerCase()}`);
  b.addEventListener("click", () => abrirSelector(dia, k, (v) => { input.value = v; poner(v); vistaPrevia(); }));
  fila.append(input, b); l.appendChild(fila);
  return l;
}

function abrirSelector(dia, momento, alElegir) {
  const dlg = $("selector");
  $("sel-titulo").textContent = `Canto de ${(ETIQ[momento] || momento).toLowerCase()} · ${dia.dia} ${dia.fecha.slice(8)}`;
  $("sel-celeb").textContent = dia.celebracion || "";
  const buscar = $("sel-buscar"), todo = $("sel-todo");
  buscar.value = ""; todo.checked = false;
  const actual = (dia.cantos || {})[momento] || "";
  const pintar = () => pintarSelector(dia, momento, buscar.value.trim(), todo.checked, actual, (c) => {
    alElegir(c.etiqueta); dlg.close();
  });
  buscar.oninput = pintar; todo.onchange = pintar;
  pintar();
  dlg.showModal();
  $("sel-lista").scrollTop = 0;
  if (!matchMedia("(pointer: coarse)").matches) buscar.focus();   // en móvil no se abre el teclado de golpe
}

function filaCanto(c, actual, elegir) {
  const b = document.createElement("button"); b.type = "button"; b.className = "fila-canto";
  if (actual === c.etiqueta) b.setAttribute("aria-current", "true");
  const t = document.createElement("span"); t.className = "t";
  const n = document.createElement("b"); n.textContent = c.n;
  t.append(n, document.createTextNode(" · " + c.titulo));
  const m = document.createElement("small"); m.textContent = `${c.subseccion} · pág. ${c.pagina}`;
  b.append(t, m);
  b.addEventListener("click", () => elegir(c));
  return b;
}

function pintarSelector(dia, momento, q, todo, actual, elegir) {
  const lista = $("sel-lista"); lista.replaceChildren();
  const nq = normalizar(q), num = /^\d+$/.test(q);
  const coincide = (c) => !q || (num ? String(c.n).startsWith(q) : normalizar(c.titulo).includes(nq));
  const grupo = (titulo, cantos, agrupar) => {
    if (!cantos.length) return;
    const h = document.createElement("h4"); h.textContent = `${titulo} (${cantos.length})`; lista.appendChild(h);
    let sub = null;
    for (const c of cantos) {
      if (agrupar && c.subseccion !== sub) {
        sub = c.subseccion; const s = document.createElement("div"); s.className = "subgrupo"; s.textContent = sub; lista.appendChild(s);
      }
      lista.appendChild(filaCanto(c, actual, elegir));
    }
  };
  const nums = ((dia.adecuados || {})[momento] || []);
  const ade = nums.map((n) => CAT.get(n)).filter((c) => c && coincide(c));
  const enAde = new Set(nums);
  const resto = [...CAT.values()].filter((c) => !enAde.has(c.n) && coincide(c) && (todo || c.momentos.includes(momento)))
    .sort((a, b) => a.subseccion.localeCompare(b.subseccion, "es") || a.n - b.n);
  grupo("Adecuados para este día", ade, false);
  grupo(todo ? "Resto del cantoral" : `Otros cantos de ${(ETIQ[momento] || momento).toLowerCase()}`, resto, true);
  if (!ade.length && !resto.length) {
    const p = document.createElement("p"); p.className = "vacio";
    p.textContent = todo ? "Ningún canto coincide." : "Ningún canto coincide. Prueba con «Ver todo el cantoral».";
    lista.appendChild(p);
  }
}

function pintarEditor() {
  const ed = $("editor"); ed.replaceChildren();
  const cab = document.createElement("div"); cab.className = "semana-cab";
  const t = document.createElement("h2"); t.textContent = hoja.titulo; cab.appendChild(t);
  const chips = document.createElement("div"); chips.className = "chips";
  for (const x of [`Salterio ${hoja.salterio}`, `Tiempo ${hoja.tiempo}`]) {
    const s = document.createElement("span"); s.className = "chip"; s.textContent = x; chips.appendChild(s);
  }
  cab.appendChild(chips); ed.appendChild(cab);
  if (hoja.notas && hoja.notas.length) {
    const det = document.createElement("details"); det.className = "notas"; det.open = true;
    const s = document.createElement("summary"); s.textContent = "Avisos de la app (no salen en la hoja)"; det.appendChild(s);
    const ul = document.createElement("ul");
    for (const n of hoja.notas) { const li = document.createElement("li"); li.textContent = n; ul.appendChild(li); }
    det.appendChild(ul); ed.appendChild(det);
  }
  const tt = entrada("Título de la hoja", hoja.titulo, (v) => { hoja.titulo = v; guardar(); });
  tt.className = "titulo-hoja"; ed.appendChild(tt);
  const grid = document.createElement("div"); grid.className = "dias";
  for (const dia of hoja.dias) grid.appendChild(tarjetaDia(dia));
  ed.appendChild(grid);
  const l = document.createElement("label"); l.textContent = "Avisos de la semana (salen en la hoja)"; l.style.marginTop = "18px";
  const ta = document.createElement("textarea"); ta.value = hoja.avisos || "";
  ta.addEventListener("input", () => { hoja.avisos = ta.value; guardar(); });
  l.appendChild(ta); ed.appendChild(l);
}

function vistaPrevia() {
  $("tit-previa").hidden = false; $("papel").hidden = false;
  $("previa").srcdoc = renderHoja(hoja, datos.css, datos.ajuste);
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
  CAT = new Map(datos.cantos.map((c) => [c.n, c]));
  $("sel-cerrar").addEventListener("click", () => $("selector").close());
  for (const id of ["selector", "ayuda"]) {   // tocar fuera del diálogo lo cierra
    $(id).addEventListener("click", (e) => { if (e.target.id === id) e.target.close(); });
  }
  const abrirAyuda = (e) => { e.preventDefault(); $("ayuda").showModal(); $("ayuda").querySelector(".dlg-cuerpo").scrollTop = 0; };
  $("ayuda-abrir").addEventListener("click", abrirAyuda);
  $("ayuda-enlace").addEventListener("click", abrirAyuda);
  $("ayuda-cerrar").addEventListener("click", () => $("ayuda").close());
  for (const [lista, valores] of [["lista-himnos", datos.himnos]]) {
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
    const f = $("previa"); $("tit-previa").hidden = false; $("papel").hidden = false; f.srcdoc = renderHoja(hoja, datos.css, datos.ajuste);
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
