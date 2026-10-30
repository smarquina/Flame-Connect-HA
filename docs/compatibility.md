# Compatibilidad y límites

Proyecto no oficial. [Flame Connect](https://www.flame-connect.com/) describe las funciones de la aplicación y su compatibilidad comercial; esas capacidades no garantizan soporte en esta integración.

## Alcance

Solo chimeneas Wi-Fi/IoT devueltas por la cuenta. No hay control BLE local, descubrimiento LAN ni funcionamiento sin Internet.

Los nombres de modelos y las capacidades se obtienen de la API. No se declara compatibilidad universal con todas las chimeneas de una marca. Modelo de referencia inicial: familia Optiflame/OLF; hace falta completar la validación de esta integración en el equipo concreto.

## Validación funcional

| Función | Evidencia actual |
|---|---|
| Login oficial y obtención del JWT | Validado por el usuario en el laboratorio previo |
| Listado y estado | Validado por el usuario en el laboratorio previo |
| Encendido/espera, calefacción y llama | Validados por el usuario en el laboratorio previo |
| Renovación y errores | Pruebas automatizadas con proveedor simulado |
| Integración completa en Home Assistant | Pendiente de validación del usuario |
| Color de llama | Pendiente de validación física; experimental |
| Temporizador | Pendiente de validación física; experimental |
| Sonido | Pendiente; puede no estar disponible o no ser útil en ciertos modelos |
| Cambio de escala del equipo | Pendiente de validación física; experimental |

Las pruebas del laboratorio no se presentan como validación física de toda la integración. Los tests automáticos no accionan chimeneas reales.

## Funciones no expuestas

Invitados, transferencia de propiedad, horarios semanales, favoritos, firmware y restablecimiento de fábrica. Los bytes de firmware/errores son solo información de lectura; no implican soporte de actualización ni diagnóstico interpretado.

La escala de calidad se utiliza como criterio técnico, no como certificación oficial de Home Assistant o HACS. No se publicará una afirmación de certificación Plata para esta integración personalizada.
