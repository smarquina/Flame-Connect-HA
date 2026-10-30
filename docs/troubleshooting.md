# Problemas frecuentes

## No aparece la integración

Comprueba la descarga en HACS y reinicia Home Assistant después de la primera instalación. Busca **Flame Connect (unofficial)**. Confirma que la versión cumple los requisitos.

## No puedo vincular la cuenta

Utiliza el enlace de la transacción actual y termina antes de 10 minutos. Selecciona el mismo tipo de acceso que en la app. Usa Chrome/Chromium/Edge y el asistente en tu ordenador, no dentro de Home Assistant OS.

Un retorno inválido o ya canjeado obliga a empezar con el nuevo enlace. No compartas retornos, tokens ni contraseñas en incidencias. Si el acceso oficial también falla fuera de Home Assistant, consulta el soporte de [Flame Connect](https://www.flame-connect.com/).

## La cuenta no devuelve chimeneas

Comprueba en la app que has utilizado la cuenta correcta y que tiene acceso a equipos Wi-Fi. Los equipos exclusivamente Bluetooth no se incorporan a esta integración. Un error de permisos no se corrige enviando órdenes repetidas.

## Una chimenea está no disponible

Comprueba su alimentación, Wi-Fi y acceso desde la app. El estado se consulta cada 30 segundos y se recuperará cuando responda. Si solo falla una, las demás siguen funcionando. El sensor Conexión informa del éxito de la lectura, no sustituye un diagnóstico de la red doméstica.

## Una orden falla o parece no aplicarse

Lee el estado y contrástalo con la app antes de volver a pulsar. Una pérdida de respuesta puede ocurrir después de que el equipo haya recibido la orden. La integración evita repetirla automáticamente.

## Las unidades no coinciden con la app

Home Assistant aplica su unidad global a la tarjeta de climatización. La API transmite Celsius y el equipo puede mostrar Fahrenheit. La preferencia de la integración y el cambio experimental de escala del equipo son ajustes distintos.

## No aparecen color, temporizador o sonido

Activa Crear controles experimentales en las opciones y habilita individualmente las entidades creadas. Algunos controles solo aparecen si el modelo declara esa capacidad. Un control cuyo parámetro no se recibe queda no disponible.

## Se solicita autenticación de nuevo

La renovación puede ser revocada por el proveedor. Utiliza el aviso de reautenticación y la misma cuenta; no borres la entrada. Un reinicio normal conserva los tokens.

## Obtener ayuda

Descarga los diagnósticos de la integración desde Dispositivos y servicios y comunica la versión de Home Assistant, versión de integración, modelo y acción que falla. Adjunta únicamente registros revisados y diagnósticos sin información personal. No adjuntes HAR completos: pueden contener tokens, PIN e identificadores.
