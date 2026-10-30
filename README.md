# Flame Connect para Home Assistant — no oficial

[![Quality gate status](https://sonarcloud.io/api/project_badges/measure?project=smarquina_Flame-Connect-HA&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=smarquina_Flame-Connect-HA)

<img src="custom_components/flame_connect/brand/icon.png" width="112" alt="Icono de Flame Connect">

Integración comunitaria para controlar chimeneas eléctricas Wi-Fi compatibles con **Flame Connect** desde Home Assistant. Cada chimenea aparece como un dispositivo con sus controles y sensores.

**Proyecto no oficial, sin afiliación, aprobación ni soporte de Glen Dimplex o de los fabricantes de las chimeneas.** La información del producto y el soporte de la aplicación original están en [flame-connect.com](https://www.flame-connect.com/).

La comunicación utiliza la nube de Flame Connect: necesita Internet y una cuenta con acceso al equipo. No proporciona control local Bluetooth ni una API LAN.

## Requisitos e instalación

- Home Assistant **2026.10.4 o posterior**, dentro de las versiones comprobadas indicadas en cada publicación.
- Marketplace integrado en Home Assistant **2026.11 o posterior**, o HACS en **2026.10.4**. Una chimenea **Wi-Fi/IoT** registrada en la app original; los modelos solo Bluetooth no están soportados.
- Para vincular la cuenta: un ordenador con Chrome, Chromium o Edge y Node.js 22.15 o posterior. **Home Assistant no necesita navegador ni Node.js**.

En **Home Assistant 2026.11 o posterior**, abre **Ajustes → Marketplace → Añadir desde enlace (Add from link)**. Introduce `https://github.com/smarquina/Flame-Connect-HA`, conecta GitHub cuando se solicite y confirma. Si pide el tipo, selecciona **Integración**. Abre el repositorio y pulsa **Instalar**; sigue cualquier aviso de reinicio. El Marketplace puede abrir la configuración al terminar; también puedes añadir **Flame Connect (unofficial)** desde **Ajustes → Dispositivos y servicios → Añadir integración**.

En **Home Assistant 2026.10.4**, utiliza **HACS → Repositorios personalizados**, añade la misma URL con categoría **Integración**, descarga la versión y reinicia antes de añadir la integración.

Consulta la [guía de instalación y vinculación](docs/installation.md), incluidas las versiones beta. Según la [documentación oficial de HACS](https://hacs.xyz/docs/marketplace/), la actualización a 2026.11 migra las instalaciones y repositorios personalizados al Marketplace; no debes reinstalar HACS. Esta transición no acredita que Flame Connect haya sido probada en esa versión de Home Assistant.

Esta versión es **beta**. Implementa las funciones descritas a continuación; la autenticación completa del componente debe validarse en tu instalación. El acceso nativo ya fue comprobado en el laboratorio, pero no equivale a una prueba completa de esta integración.

## Dispositivos y funciones

Los nombres de tus chimeneas proceden de la cuenta. Sus identificadores permanecen estables aunque cambies el nombre.

| Entidad | Función |
|---|---|
| Calefacción | Activación independiente, temperatura y consigna |
| Encendido de chimenea | Encender como la app o poner en espera |
| Llama | Activar o desactivar solo el efecto decorativo |
| Brillo de llama | High, Low, Flicker high y Flicker low, si el modelo lo admite |
| Velocidad de llama | 1–5, si el modelo lo admite |
| Temperatura | Lectura recibida del equipo |
| Conexión | Si la última lectura del equipo ha sido correcta |
| Bytes de firmware y errores | Datos técnicos exactos; deshabilitados por defecto |

**Encender la chimenea activa el modo manual y los parámetros disponibles de calor y llama, como el botón de la app.** Para usar únicamente la decoración, utiliza Llama y mantén la calefacción apagada. Apagar Calefacción no equivale a poner toda la chimenea en espera.

El dispositivo muestra fabricante y modelo cuando la API los proporciona. Las funciones dependen de las capacidades de cada modelo; un parámetro ausente no se sustituye por valores inventados.

### Controles experimentales

En las opciones de la integración puedes activar **Crear controles experimentales**. Se crean deshabilitados y debes habilitar cada entidad que quieras probar:

- Presets de color de llama según la paleta del modelo.
- Activación y duración del temporizador.
- Volumen y archivo de sonido.
- Escala de temperatura del dispositivo.

Estas escrituras siguen pendientes de validación física. El rango 0–255 del sonido es el rango del byte, **no una garantía de niveles de volumen soportados**. No se exponen controles de sonido si el modelo no declara esa capacidad.

## Celsius y Fahrenheit

La API transmite temperaturas y consignas en **Celsius**, incluso cuando el equipo muestra Fahrenheit. La integración convierte los valores una sola vez al entrar o salir de la capa de presentación.

La opción **Unidad preferida** permite `auto`, `C` o `F`. Automática sigue la preferencia de visualización recibida del dispositivo, con Celsius si no se recibe. Esta opción no escribe nada en la chimenea.

Las tarjetas de climatización respetan el sistema de unidades de Home Assistant. Elegir Fahrenheit en las opciones no fuerza una tarjeta contraria al sistema global de Home Assistant. El cambio físico de escala es un control experimental independiente.

La consigna se limita al intervalo de la app: mínimo 15 °C; máximo 30.6 °C en familias Optiflame/OLF identificadas o 32.9 °C en las demás. Los límites se convierten cuando corresponde y pueden requerir ajustes si se valida otro modelo.

## Actualización y disponibilidad

- Una lectura compartida por chimenea cada 30 segundos mientras tenga entidades escuchando.
- Lectura nueva antes de cada orden y otra después para confirmar el estado.
- El inventario y las capacidades se vuelven a consultar al cargar o recargar la integración. Para incorporar otra chimenea, utiliza Reconfigurar en el menú de la entrada.
- Una chimenea desconectada no interrumpe las demás. Sus controles quedan no disponibles y el sensor Conexión indica la pérdida de lectura.
- Una orden no confirmada muestra un error. No se repite automáticamente: consulta el estado antes de intentarlo de nuevo.

El cambio de opciones permite recargar la integración sin reiniciar Home Assistant. Para actualizar sus archivos, utiliza **Ajustes → Actualizaciones** en Marketplace y reinicia Home Assistant para aplicar la actualización; en HACS sigue sus indicaciones de reinicio.

## Acceso y renovación

El usuario introduce la contraseña únicamente en el sitio oficial de Microsoft/B2C. La integración guarda access token y refresh token en la configuración de Home Assistant, utiliza el nuevo refresh token si hay rotación y conserva el acceso tras reinicios. No almacena la contraseña.

Se renueva antes de caducar o ante el rechazo del access token. Si la renovación deja de ser válida, Home Assistant solicita **volver a autenticar**. Hazlo con la misma cuenta para mantener los dispositivos y entidades.

No se añaden acciones, condiciones o disparadores propios: se usan las acciones y cambios de estado estándar de las entidades de Home Assistant.

## Ayuda y documentación técnica

- [Instalación y vinculación](docs/installation.md).
- [Funcionamiento, autenticación y API](docs/technical.md).
- [Problemas frecuentes y diagnósticos](docs/troubleshooting.md).
- [Contrato OpenAPI de dispositivos](docs/openapi.json) y [Azure B2C](docs/b2c.openapi.json).
- [Compatibilidad y límites](docs/compatibility.md).

## Eliminar la integración

Elimina la entrada desde **Ajustes → Dispositivos y servicios**. Después, si ya no la necesitas, desinstala el repositorio desde Marketplace o HACS y reinicia cuando se te indique. Esto elimina la configuración local de la integración; no borra tu cuenta ni desvincula la chimenea de la app oficial.

## Identidad visual y licencia

El icono corresponde a la aplicación Flame Connect y fue facilitado por el usuario como referencia de identificación. Las marcas e imágenes pertenecen a sus titulares; no están cubiertas por la licencia MIT del código original de este proyecto. Su uso no implica afiliación ni respaldo del fabricante.
