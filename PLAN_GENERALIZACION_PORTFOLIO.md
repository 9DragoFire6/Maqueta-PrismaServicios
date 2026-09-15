# Plan: generalizar el sistema Fam&Co para portfolio propio

## Objetivo

Extraer la arquitectura técnica de este proyecto hacia un repo nuevo, propiedad exclusiva
de Kevin, generalizada a un dominio genérico de **"gestión de clientes + servicios
programados + personal + facturación"** — útil para mostrar el trabajo y reutilizable en
cualquier negocio que opere por proyectos/servicios (no solo cuidado de personas). Ningún
dato real, nombre real, ni detalle específico del rubro de Fam&Co debe quedar visible.

Este plan **no toca el repo `byfamco`**. Todo el trabajo ocurre en un repo nuevo aparte.
Nada de esto se ejecuta sin que Kevin revise y apruebe cada fase.

**Alcance de ejecución: solo local.** La versión generalizada no se despliega (no hay
Railway ni Vercel) — vive y se corre en el computador de Kevin. Esto saca del plan todo lo
que tenía que ver con configuración de despliegue, CORS de producción y URLs de hosting;
solo queda un `.env.example` apuntando a `localhost` y un README con instrucciones de "cómo
correrlo local" (backend con `runserver`, frontend con `vite dev`).

## Cómo se ejecuta este plan (logística)

- **Chat nuevo, separado de este.** Esta conversación tiene harto contexto operativo real
  de Fam&Co (bugs, nombres, decisiones de negocio) que no debería filtrarse ni por
  accidente a los comentarios o el README del repo genérico. Un chat nuevo parte limpio.
- **Esa sesión nueva necesita acceso a dos carpetas:** la carpeta `byfamco` (como
  referencia de solo lectura — nunca se escribe ahí) y una carpeta nueva, vacía, que sea el
  repo del proyecto genérico (ahí se escribe todo). Si la app no permite conectar dos
  carpetas a la misma sesión, el plan B es que yo arme la primera copia de trabajo acá
  mismo (ya tengo acceso a `byfamco` en esta sesión) y la dejes lista para que la muevas a
  la carpeta nueva antes de abrir el otro chat.
- **No recomiendo copiar el repo completo tal cual y depurar encima.** Arrastraría el
  historial de git, las migraciones de Django, `mediafiles/`, `node_modules/` y cualquier
  `.env` con secretos reales — nada de eso debería existir en el repo genérico. Mejor
  reescribir fresco cada módulo (leyendo el original como referencia) siguiendo el glosario
  de este plan, fase por fase.
- **Llévate este archivo al chat nuevo** (está en tu carpeta de descargas de esta sesión) —
  cópialo a la raíz de la carpeta nueva o adjúntalo al abrir la conversación, así el chat
  nuevo arranca sabiendo exactamente en qué fase estamos y con el mismo glosario.

## Principios que rigen todas las fases

- **Generalizar, no traducir.** No es un find-and-replace de nombres — cuando una regla de
  negocio es específica del rubro (ej. el cálculo de IVA fijo por fecha de Portugal), se
  reemplaza por una versión configurable, no solo se renombra.
- **No perder funcionalidad.** Cada fase se verifica contra la lógica original antes de
  pasar a la siguiente — la meta es que el sistema genérico siga haciendo lo mismo
  (agendar, facturar, controlar ausencias, etc.), solo que sin el ropaje de Fam&Co.
- **Fases chicas y revisables.** Cada fase es un módulo o grupo de módulos acotado. Se
  para a revisar contigo al final de cada una antes de seguir — así si algo no convence, se
  corrige ahí mismo y no hay que deshacer trabajo de fases posteriores.
- **Datos ficticios desde el principio.** Antes de generalizar el primer modelo, se arma un
  comando de datos de ejemplo con nombres/empresas inventados, para poder probar cada fase
  sin tocar nunca datos reales de Fam&Co.

## Glosario de renombres (guía para todas las fases)

| Original (Fam&Co) | Generalizado | Nota |
|---|---|---|
| `Familia` | `Cliente` | Entidad que contrata servicios |
| `Bebe` | *(se elimina)* | Demasiado específico de cuidado infantil — es el campo que más delata el rubro. No se generaliza, se saca del todo. |
| `Freelancer` | `Empleado` | Por tu indicación — son empleados, aunque se les pague por servicio prestado (ese patrón de pago sí es genérico y útil para otros rubros: técnicos de campo, personal de limpieza, etc.) |
| `Servicio` (tipo: founder/colaboradora) | `Servicio` (categoría configurable) | Se saca el caso especial "founder cobra 100%" y se reemplaza por una regla de compensación configurable por servicio |
| `Contrato` / `AcuerdoServicio` | Igual, sin cambio de nombre | Ya son genéricos: contrato general + líneas de servicio contratado |
| `Turno` / `Ausencia` / `SolicitudAusencia` | Igual, sin cambio de nombre | Ya son genéricos (agendamiento + control de ausencias) |
| `Ingreso` / `Recibo` / `Factura` | Igual, sin cambio de nombre | Ya son genéricos |
| `PagoFreelancer` | `PagoEmpleado` | Sigue el mismo renombre que `Freelancer` |
| `GastoCorporativo` / `NotaCredito` / `Liquidacion` / `TareaCobro` / `TareaRecurrente` | Igual, sin cambio de nombre | Ya son genéricos |
| `PlantillaClausulasContrato` | Igual, sin cambio de nombre | Ya es genérico (plantillas de cláusulas por tipo de contrato) |

## Qué se elimina por completo (no se generaliza)

- Modelo `Bebe` y todo lo que dependa de él.
- La regla de `FECHA_CAMBIO_IVA` (IVA fijo de Portugal desde una fecha exacta) — se
  reemplaza por un `iva_porcentaje` simple y configurable por cliente, sin la lógica
  histórica forzada.
- Cualquier texto de servicio real ("Night Care", "Day Care", etc.), branding, logos,
  colores de marca.
- URLs reales (`byfamco.vercel.app`), correos reales, nombres de las socias.
- Contenido real de PDFs/plantillas de contrato.
- Todos los README actuales se reescriben desde cero en la versión genérica — no se copian
  ni resumen, porque están llenos de contexto real ("Kevin pidió", "las socias", etc.).

## Fases

### Fase 0 — Preparación (sin migrar código todavía)

- Crear el repo nuevo en tu GitHub (a definir: nombre y si queda público o privado al
  principio).
- Decidir si el proyecto se mantiene en español o se traduce a inglés (recomendación: dejarlo
  en español está bien — es trabajo real, no hace falta traducirlo para que se vea
  profesional).
- Dejar este glosario como archivo de referencia en el repo nuevo, para que las fases
  siguientes sean consistentes entre sí.
- Armar el comando de datos de ejemplo ficticios (reemplaza a
  `generar_datos_prueba_operativos.py` / `generar_datos_prueba_facturacion.py`) con clientes,
  servicios y empleados inventados — esto se usa para probar cada fase siguiente.

**Se revisa antes de seguir:** el glosario y el nombre/alcance del repo te hacen sentido.

### Fase 1 — Seguridad y autenticación

Módulo más autocontenido y el que mejor muestra nivel técnico: JWT + 2FA (TOTP), el sistema
de doble verificación con contraseña para ediciones sensibles, campos cifrados para datos
personales. Es el que menos lógica de negocio específica tiene — casi se traslada intacto,
solo sacando URLs hardcodeadas (pasan a variable de entorno, que además es mejor práctica).

**Se revisa antes de seguir:** login, 2FA y doble verificación funcionan igual que en el
original, sin ninguna referencia a Fam&Co.

### Fase 2 — Entidades núcleo (Cliente, Servicio, Contrato)

`Familia` → `Cliente` (sin `Bebe`), `Servicio` con datos de ejemplo genéricos, `Contrato` y
`AcuerdoServicio` con la regla founder/colaboradora reemplazada por compensación
configurable.

**Se revisa antes de seguir:** se puede crear un cliente, un servicio y un contrato de
punta a punta con datos ficticios, igual que en el original.

### Fase 3 — Motor de agendamiento (Turno, Ausencias)

`Freelancer` → `Empleado`, `Turno`, `Ausencia`, `SolicitudAusencia`, la detección
automática de ausencias (ventana de 12h) y el flujo de corrección. Es prácticamente
genérico tal cual — el trabajo acá es sobre todo de renombre, no de rediseño.

**Se revisa antes de seguir:** el ciclo completo (turno programado → registro de horas →
detección de ausencia si no se registra → corrección) funciona igual.

### Fase 4 — Motor financiero (Ingresos, Facturación, Pagos)

`Ingreso`, `Recibo`, `Factura`, `TareaCobro`, `TareaRecurrente`, `PagoFreelancer` →
`PagoEmpleado`. Se generaliza el IVA (se saca la regla histórica de Portugal), se revisa la
importación idempotente/no idempotente como ejemplo de manejo de datos externos.

**Se revisa antes de seguir:** la facturación semanal agregada y el flujo de pago a
empleados siguen dando los mismos resultados que el original con datos ficticios.

### Fase 5 — Documentos y contratos PDF

Generalizar la plantilla de contrato (título, cláusulas de ejemplo), sacar todo branding.

**Se revisa antes de seguir:** se genera un PDF de contrato de ejemplo, sin ninguna
referencia real.

### Fase 6 — Frontend

Renombrar páginas y componentes siguiendo el mismo glosario (`Familias.jsx` →
`Clientes.jsx`, `ProfesionalDetalle.jsx` → `EmpleadoDetalle.jsx`, etc.), sacar branding
visual, conectar con los datos ficticios de las fases anteriores.

**Se revisa antes de seguir:** la app se ve y funciona completa, de punta a punta, con datos
ficticios.

### Fase 7 — Documentación final (lo que realmente se muestra)

README tipo case-study: arquitectura, diagramas, decisiones de diseño explicadas en
términos genéricos (por qué doble verificación, por qué campos cifrados, por qué
facturación agregada semanal en vez de por turno, etc.). Este es el documento que hace el
trabajo de "vender" el proyecto — se escribe al final, con todo ya generalizado y probado.

## Próximo paso

Si te hace sentido este plan, el primer paso concreto es la Fase 0: definir nombre/alcance
del repo nuevo y armar los datos de ejemplo ficticios. Ahí recién se empieza a escribir
código — nada se toca antes de que apruebes cada fase.
