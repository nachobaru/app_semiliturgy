# CLAUDE.md

App en Python que genera la hoja de liturgia semanal del Seminario Metropolitano de Oviedo.
Idioma del proyecto: español (código, comentarios, commits y documentación).

- Tests: `python -m pytest -q`. `tests/test_hoja.py` contrasta con la hoja real de la semana XXXIII
  (15-21 nov 2026); no romper esos casos sin hablarlo.
- Calendario de España: Epifanía el 6 de enero, Ascensión y Corpus trasladados a domingo.
- Las reglas litúrgicas viven en `semiliturgy/borrador.py` (un función por campo de la hoja);
  los criterios propios del Seminario en `config.yaml`, no en el código.
- Nunca subir PDFs de breviario, misal, cantoral o epacta: el repo es público. Van en `fuentes/`.
- Lo que no se sepa con certeza del calendario propio se marca `verificar: true`.
