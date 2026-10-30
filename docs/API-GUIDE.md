# Funcionamiento técnico

Integración no oficial para la API cloud de Flame Connect. El contrato completo de cuenta se entrega en [openapi.json](openapi.json); el cliente de esta integración expone únicamente inventario, estado y escritura de parámetros conocidos.

## Servidores y cabeceras

API: `https://mobileapi.gdhv-iot.com`. Se envía el access token como Bearer, `Accept: application/json`, Content-Type JSON en escrituras y las cabeceras del cliente recuperadas de la app: `app_name`, `api_version`, `app_version`, `app_device_os`, `device_version`, `device_manufacturer`, `device_model`, `lang_code`, `country`, `logging_required_flag`.

Su presencia reproduce el cliente conocido; no se ha probado que todas sean obligatorias. No se aceptan servidores alternativos ni cabeceras arbitrarias mediante opciones.

## Autenticación

Cliente público de Azure B2C, authorization code con PKCE S256 y `offline_access`; sin client secret. El retorno registrado es nativo. El verificador y nonce permanecen en la transacción en memoria de Home Assistant; el asistente de escritorio recibe únicamente el enlace público de autorización y captura el retorno.

Se verifica RS256, claves públicas del proveedor, issuer y expiración. Para el ID token se valida audience y nonce. La autorización del access token para el recurso la comprueba también la API remota. Tokens y claves no se reflejan en errores o registros. Metadatos y claves solo se aceptan del host B2C conocido, sin seguir redirecciones.

Los tokens persistentes se guardan mediante ConfigEntry y sobreviven a reinicios. Un bloqueo por cuenta coordina la renovación y guarda el refresh token rotado antes de utilizar las nuevas credenciales. Un error temporal de red no se trata como una contraseña incorrecta.

## Estado y órdenes

- `GetFires`: inventario y capacidades.
- `GetFireOverview?FireId=...`: estado y `WifiFireOverview.Parameters`.
- `WriteWifiParameters`: lista de paquetes a modificar.

HTTP 200 no basta: se comprueban ResultCode, IsException y el identificador del equipo. Los resultados no reconocidos se rechazan. Cada chimenea comparte su snapshot y un bloqueo de órdenes entre plataformas.

Siempre se lee el estado antes de construir una escritura y después de enviarla. No se repiten automáticamente escrituras ni se restauran estados antiguos al iniciar Home Assistant. Ante un 401, una consulta puede repetirse una vez después de renovar; una escritura informa del fallo y requiere revisión manual.

## Paquetes binarios

`Value` es Base64 del paquete: ID uint16 little endian, longitud uint8 y payload. Se validan ID, tamaño y longitud antes de acceder a offsets. Los cambios preservan los bytes restantes del paquete recibido.

| ID | Payload | Uso |
|---|---:|---|
| 236 | 1 byte | Preferencia Celsius/Fahrenheit del equipo |
| 321 | 3 | Modo y temperatura Celsius |
| 322 | 20 | Efecto de llama, velocidad, brillo y colores |
| 323 | 5 | Calefacción, modo, consigna Celsius y boost |
| 326 | 3 | Temporizador, duración little endian |
| 327 | 9 | Firmware, expuesto como bytes sin atribuir versiones no verificadas |
| 329 | 4 | Errores, expuestos como bytes sin interpretación no verificada |
| 369 | 2 | Volumen y archivo de sonido |

El color de llama ocupa el byte absoluto 19, offset 16 del payload 322. Sus códigos 0..6 representan presets, con etiquetas según FlamePresetOptions. No es RGB arbitrario.

La app convierte la consigna Fahrenheit a Celsius antes de escribir. La integración aplica el mismo criterio; el parámetro 236 no cambia el significado térmico del paquete. Los límites proceden de la UI del cliente: 15 °C a 30.6/32.9 °C según familia, y pueden necesitar ajuste para otros modelos.

## Disponibilidad y diagnósticos

Cada chimenea tiene su coordinador. Un fallo marca sus controles no disponibles sin bloquear otros equipos. La cuenta se comprueba durante el arranque; los dispositivos individuales desconectados pueden cargar no disponibles y recuperarse después.

Los diagnósticos descargables incluyen modelo, capacidades, opciones e IDs de parámetros, excluyendo nombre personal del dispositivo, PIN, identificadores de cuenta y equipo, tokens y contraseñas. Los registros notifican pérdida y recuperación sin repetir el mismo error en cada consulta.

## Compatibilidad de Home Assistant

La primera base de pruebas es Home Assistant 2026.10.4 y Python 3.14. Se contempla el cambio de propiedades nativas de climatización anunciado para 2026.11, pero esa compatibilidad debe comprobarse también con su versión publicada. Cada publicación indicará las versiones efectivamente ensayadas.
