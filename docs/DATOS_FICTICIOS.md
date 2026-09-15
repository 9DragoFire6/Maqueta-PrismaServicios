# Dataset ficticio de referencia

Este documento define el negocio inventado que van a usar los datos de ejemplo
en todas las fases siguientes (reemplaza a `generar_datos_prueba_operativos.py`
/ `generar_datos_prueba_facturacion.py` del original). Ningún nombre, cifra ni
situación de acá corresponde al proyecto original.

El comando de management real (`generar_datos_demo`) no se puede escribir
todavía porque los modelos (`Cliente`, `Servicio`, `Contrato`, `Empleado`,
`Turno`, ...) no existen hasta las Fases 2-4. Este documento es el guión que
ese comando va a implementar, para que los nombres y valores sean consistentes
entre fases y no haya que inventar datos nuevos cada vez.

## Rubro elegido

**Servicios de limpieza y mantenimiento a domicilio**, para hogares y
oficinas. Rubro genérico, con turnos programados, personal por servicio y
facturación recurrente — pero sin ningún parecido al cuidado de personas.

Empresa ficticia: **Prisma Servicios**.

## Clientes (`Cliente`, ex-`Familia`)

| Nombre de contacto | NIF | Dirección | IVA % |
|---|---|---|---|
| TEST-Cliente Aguirre | TEST100001 | Av. de Prueba 100, Ciudad Demo | 21 |
| TEST-Cliente Rossi | TEST100002 | Calle Ficticia 45, Ciudad Demo | 21 |

## Empleados (`Empleado`, ex-`Freelancer`)

Se elimina la distinción especial "founder/colaboradora" y se reemplaza por
**categorías de servicio con compensación configurable** (ver más abajo). Los
empleados de ejemplo:

| Nombre | Rol narrativo |
|---|---|
| TEST-Diego | Empleado titular, turno diurno estándar |
| TEST-Sofía | Empleada titular, segundo contrato |
| TEST-Marta | Sustituta (cubre ausencias) |
| TEST-Julia | Empleada de la categoría "premium" (turno nocturno) |

## Servicios (`Servicio`)

Reemplaza el caso especial "founder cobra 100%" por un campo de compensación
configurable por servicio (ej. `compensacion_porcentaje` o
`pago_empleado` fijo, a definir en Fase 2/4).

| Código | Nombre | Tarifa cliente | Pago empleado | Categoría | Cruza medianoche |
|---|---|---|---|---|---|
| LIMP-STD | Limpieza estándar | 15 | 10 | estándar | No |
| LIMP-NOC | Limpieza industrial nocturna | 20 | (100% configurable) | premium | Sí |
| MANT-TEC | Mantenimiento técnico | 18 | 12 | estándar | No |

## Contratos y agendamiento

Mismo esqueleto narrativo que el original, solo con los nombres de arriba:

- Contrato 1 (TEST-Cliente Aguirre): `AcuerdoServicio` con TEST-Diego,
  LIMP-STD, lunes a viernes 08:00–16:00, 4 semanas ya transcurridas (para
  probar facturación agregada).
- Segundo `AcuerdoServicio` sobre el mismo contrato: TEST-Julia, LIMP-NOC,
  martes/jueves 22:00–07:00 (cruza medianoche), para probar ese caso.
- Ausencias de TEST-Diego cubiertas por TEST-Marta (colaboradora) y por
  TEST-Julia (categoría premium), en semanas reales del acuerdo — mismo patrón
  que el original, sin el caso "founder cubre siempre".
- Contrato 2 (TEST-Cliente Rossi): TEST-Sofía, MANT-TEC, para probar que la
  facturación se agrupa por contrato y no por cliente.

## Gastos corporativos

Mismas categorías genéricas que el original (`operativo`, `legal`,
`software`), sin los nombres de las socias — se generalizan a
`retiro_socio_1` / `retiro_socio_2` o un modelo de socios configurable (a
decidir en Fase 4).

## Próximo uso de este documento

- **Fase 2**: al crear `Cliente`/`Servicio`/`Contrato`, usar estos mismos
  nombres y valores en los fixtures/seed de prueba de esa fase.
- **Fase 3**: al crear `Empleado`/`Turno`/`Ausencia`, usar los empleados de
  arriba.
- **Fase 4**: al escribir el comando `generar_datos_demo` completo (que
  reemplaza definitivamente a los dos comandos originales), implementar
  exactamente este guión.
