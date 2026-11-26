# app_semiliturgy

Generador de la **hoja de liturgia semanal** del Seminario Metropolitano de Oviedo.

A partir de una fecha, la app calcula el calendario litúrgico de la semana y propone un
borrador con todo lo que sale por reglas:

- tiempo litúrgico, semana y **semana del salterio**;
- celebración de cada día (solemnidad, fiesta, memoria, feria) según la tabla de precedencias;
- **Laudes y Vísperas**: himno (no el título, sino de dónde se toma: *Feria*, *Propio* o *Del común
  de …*), salmodia (Feria / Domingo I / Propia) y antífona del
  Benedictus o del Magníficat; I Vísperas de domingos y solemnidades;
- **Eucaristía**: formulario y **prefacio** (rotando los comunes sin repetir en la semana);
- **cantos** de entrada, ofertorio y comunión tomados del cantoral del Seminario, adecuados al
  tiempo o la fiesta y sin repetir los de las últimas semanas.

El encargado de liturgia revisa y edita el borrador (un YAML legible) y la app genera la hoja
en HTML y PDF con el mismo formato que la hoja actual (A4 apaisado).

## Uso

```bash
pip install -r requirements.txt          # WeasyPrint necesita las librerías de Pango del sistema

python -m semiliturgy dia 2026-11-21               # qué se celebra un día
python -m semiliturgy borrador 2026-11-23          # crea semanas/2026-11-22.yaml (cualquier fecha de la semana)
#   ...editar semanas/2026-11-22.yaml...
python -m semiliturgy hoja semanas/2026-11-22.yaml # genera .html y .pdf
```

### Interfaz web

```bash
python -m semiliturgy web      # http://127.0.0.1:5000
```

Lista las semanas, crea el borrador de cualquier fecha, permite editar cada día (con
autocompletado de cantos), guardar en `semanas/*.yaml`, ver la hoja y descargar el PDF.
No tiene usuarios ni contraseña: escucha solo en `127.0.0.1`. No la expongas a internet
(`--host 0.0.0.0`) sin ponerle delante autenticación.

### Versión estática (GitHub Pages)

`python scripts/generar_sitio.py` crea `sitio/`: una página sin servidor que edita los borradores
en el navegador, muestra la hoja y la imprime a PDF (diálogo de impresión, A4 apaisado). Los
borradores de las próximas ~80 semanas se pregeneran con las reglas de Python y se respetan los
YAML revisados de `semanas/`. Cada canto tiene un botón **Elegir** que abre un buscador: primero los
cantos adecuados para ese día y momento (según el tiempo, la fiesta y sin los usados en las últimas
semanas) y luego el resto, agrupados por sección del cantoral, con número y página; se busca por
número o título. Lo editado se guarda en el navegador y se exporta como YAML
(**Descargar YAML**) para subirlo a `semanas/`.

La publica `.github/workflows/pages.yml` al subir a `main` y cada lunes. Hay que activarlo una vez en
*Settings → Pages → Source: GitHub Actions*.

Los YAML de `semanas/` son también el **historial**: de ahí se saca qué cantos se han usado
para no repetirlos. Conviene guardarlos en el repositorio.

## Estructura

| Ruta | Qué es |
|---|---|
| `semiliturgy/calendario.py` | Cómputo pascual, tiempos, salterio, ciclos y precedencias |
| `semiliturgy/borrador.py` | Reglas de cada campo de la hoja y generación del borrador |
| `semiliturgy/cantos.py` | Catálogo del cantoral y sugerencia de cantos |
| `semiliturgy/hoja.py`, `plantillas/hoja.html` | Render HTML/PDF |
| `semiliturgy/web.py`, `plantillas_web/` | Interfaz web local (Flask) |
| `sitio_src/`, `scripts/generar_sitio.py` | Versión estática para GitHub Pages |
| `config.yaml` | Horario por día, prefacios comunes, criterios del Seminario |
| `data/santoral.yaml` | Calendario Romano General + España |
| `data/calendario_propio.yaml` | Propio de Oviedo y del Seminario (**verificar con la Epacta**) |
| `data/cantoral.json` | Catálogo extraído del cantoral (número, título, página, sección) |
| `data/etiquetas_cantos.yaml` | Ajustes manuales de cantos (momentos, etiquetas, `solo_si`) |
| `scripts/extraer_cantoral.py` | Regenera `data/cantoral.json` desde el PDF del cantoral |

## Fuentes y derechos

Los PDF del breviario, el misal y el cantoral **no se suben al repositorio** (el repo es
público y esos textos tienen derechos). Guardadlos en `fuentes/`, que está en `.gitignore`.
Del cantoral solo se guardan títulos y páginas.

## Pendiente

- [ ] Verificar el santoral y el propio de Oviedo con la **Epacta** (y completar memorias libres).
- [ ] Traslado automático de solemnidades impedidas (ahora solo se avisa).
- [x] Interfaz web para editar el borrador sin tocar YAML (mejoras: autenticación, aviso de cantos repetidos).
- [ ] Exportar también a Word, si el encargado lo prefiere.
