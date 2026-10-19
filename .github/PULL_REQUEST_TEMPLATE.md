## ¿Qué cambia y por qué?

<!-- Conventional Commit en el título del PR (feat:/fix:/refactor:/test:/docs:/chore:)
     Primera línea ≤ 72 chars.
     Aquí: explica el WHY, no el what — el diff ya muestra el what. -->

## ¿Cómo lo probaste?

<!-- Pasos concretos. Si aplica, incluye el comando exacto que corriste, contra qué
     backend (pipeline / hybrid-engine / vlm-engine) y con qué documento. -->

---

## Checklist

- [ ] Tests para toda lógica nueva
- [ ] `ruff check .` pasa sin errores
- [ ] `pytest` en verde
- [ ] Título del PR en formato Conventional Commit
- [ ] Identifiers (clases, funciones, variables, archivos) en **inglés**
- [ ] Comentarios y mensajes de commit en **español**
- [ ] Nombres y parámetros de las tools sin cambios (o el cambio está justificado arriba)
