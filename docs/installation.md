# Instalación y vinculación de la cuenta

Integración **no oficial**. Antes de empezar, comprueba que tu chimenea Wi-Fi puede consultarse desde la app original de Flame Connect y que la cuenta tiene acceso.

## Instalar desde Marketplace (Home Assistant 2026.11 o posterior)

1. Accede como administrador a **Ajustes → Marketplace** y acepta el aviso de contenido comunitario.
2. Pulsa **Añadir desde enlace (Add from link)** e introduce `https://github.com/smarquina/Flame-Connect-HA`.
3. Si se solicita, conecta tu cuenta de GitHub siguiendo el código y enlace que muestra Home Assistant. Esta conexión permite consultar el repositorio personalizado y sus actualizaciones; es independiente del acceso a Flame Connect.
4. Confirma con **Añadir**. Si no identifica el tipo automáticamente, selecciona **Integración** y confirma de nuevo.
5. Abre la ficha del repositorio y pulsa **Instalar**, revisa la versión y confirma. Sigue el aviso de reinicio si aparece.
6. Continúa con la configuración que abre Home Assistant o entra en **Ajustes → Dispositivos y servicios → Añadir integración → Flame Connect (unofficial)**.

Estas instrucciones permiten añadir el proyecto por enlace; no implican que esté incluido en el catálogo predeterminado ni que Home Assistant lo certifique o le dé soporte. La versión mínima comprobada de Flame Connect sigue siendo **2026.10.4**; el flujo de Marketplace descrito corresponde a la documentación de **2026.11**, sin afirmar una validación de ejecución en esa versión.

### Versiones beta

Marketplace ofrece versiones estables por defecto. Para recibir prepublicaciones, abre el dispositivo del repositorio en **Ajustes → Dispositivos y servicios → Marketplace**, habilita la entidad **Pre-release**, deshabilitada por defecto, y activa su interruptor. Para elegir una versión disponible, utiliza el menú de la ficha del repositorio → **Instalar otra versión (Install another version)**. La versión debe estar publicada en GitHub; un PR en borrador no equivale a una publicación instalable.

## Instalar con HACS (Home Assistant 2026.10.4)

Añade `https://github.com/smarquina/Flame-Connect-HA` como repositorio personalizado de tipo **Integración**. Descarga una versión y reinicia Home Assistant. Añade **Flame Connect (unofficial)** desde **Ajustes → Dispositivos y servicios**.

Al actualizar Home Assistant a **2026.11**, Marketplace migra automáticamente las instalaciones, los repositorios personalizados y las entidades de actualización de HACS. HACS deja de instalarse por separado y el acceso pasa a **Ajustes → Marketplace**. No hace falta volver a vincular Flame Connect por este cambio del gestor.

Referencias oficiales: [transición de HACS a Marketplace](https://hacs.xyz/docs/marketplace/) y [uso de Marketplace](https://next.home-assistant.io/integrations/marketplace/).

## Vincular desde un ordenador

El proveedor registra una dirección de retorno móvil `msal…://auth`, no un retorno web de Home Assistant. Por eso el primer acceso utiliza un asistente ejecutado **en tu ordenador**. Home Assistant genera el verificador PKCE y realiza el canje. El asistente solo abre Chrome y recoge el código de autorización de un solo uso.

1. En Home Assistant elige `normal` para teléfono/correo o `social` para una identidad externa.
2. Deja abierto el paso de vinculación y copia su **enlace oficial de acceso**. Caduca en 10 minutos.
3. Descarga el ZIP del repositorio correspondiente a la versión instalada y descomprímelo en tu ordenador.
4. Con Node.js 22.15 o posterior instalado, abre una terminal en esa carpeta y ejecuta:

   ```sh
   node tools/link/link.mjs
   ```

5. Pega el enlace cuando lo solicite. El asistente valida que pertenece al proveedor oficial y abre un perfil temporal aislado de Chrome.
6. Introduce tus credenciales exclusivamente en la página oficial. El asistente no pide ni guarda la contraseña.
7. Tras completar el acceso, copia el retorno `msal…://auth?code=…&state=…` que aparece en la terminal al campo protegido de Home Assistant.
8. Confirma y selecciona al menos una chimenea Wi-Fi. Elige `auto`, `C` o `F` para la unidad preferida y termina.

No compartas el retorno: contiene un código de un solo uso. No es un JWT ni una contraseña. No utilices el enlace de un intento anterior. Si hay un error, utiliza el nuevo enlace mostrado por Home Assistant.

El navegador temporal se cierra y su perfil se elimina al terminar. Home Assistant valida estado, PKCE, firma de los tokens, emisor, expiración y la identidad correspondiente. La cuenta no se guarda hasta consultar correctamente su lista de chimeneas.

### Localizar el navegador

Se busca Chrome, Edge o Chromium en rutas habituales de macOS y Linux. Para otra ruta, o en Windows, configura `FLAME_CHROME_PATH` con la ruta completa del ejecutable antes de iniciar el asistente.

macOS/Linux:

```sh
FLAME_CHROME_PATH='/ruta/al/navegador' node tools/link/link.mjs
```

PowerShell:

```powershell
$env:FLAME_CHROME_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
node tools/link/link.mjs
```

No ejecutes el asistente dentro de Home Assistant OS ni reutilices un perfil personal del navegador. Para cancelar, cierra la ventana oficial; vuelve a comenzar la vinculación si la transacción caduca.

## Parámetros de configuración

| Campo | Uso |
|---|---|
| Tipo de cuenta | Política B2C normal o social |
| URL nativa de retorno | Resultado de un solo uso obtenido por el asistente |
| Chimeneas | Equipos Wi-Fi de la cuenta que se crearán como dispositivos |
| Unidad preferida | `auto`, `C` o `F`; no modifica la escala del equipo |

## Opciones posteriores

**Unidad preferida:** cambia la presentación nativa de las entidades, respetando las conversiones de Home Assistant. No cambia el significado Celsius de los valores de la API.

**Crear controles experimentales:** añade color, temporizador, sonido y escala según capacidades. Se crean deshabilitados para habilitarlos individualmente desde las entidades del dispositivo. Cambiar esta opción no envía órdenes.

La lista se selecciona durante el alta. Para cambiarla, abre el menú de la entrada y elige **Reconfigurar**: vuelve a consultar la cuenta y permite seleccionar los equipos sin eliminar la entrada. La reautenticación conserva la selección existente.

## Reautenticación

Cuando Home Assistant solicite volver a autenticar, abre el aviso y repite la vinculación con **la misma cuenta**. No elimines la integración ni pegues un JWT manualmente. Los identificadores y la selección de dispositivos se mantienen.

## Actualizar o eliminar

En Marketplace, las nuevas versiones aparecen en **Ajustes → Actualizaciones**. Revisa las notas, conserva una copia de seguridad y aplica la actualización. Reinicia Home Assistant para cargar los archivos nuevos; un aviso en **Ajustes → Sistema → Reparaciones** lo recuerda. En Home Assistant 2026.10.4, actualiza mediante HACS y sigue su indicación de reinicio.

Para eliminar, borra primero la entrada de Flame Connect en **Dispositivos y servicios** y después abre la ficha del repositorio en Marketplace → menú → **Desinstalar**. Si sigue configurada, Marketplace permite **Ver integración** para eliminar la configuración o **Eliminar y desinstalar (Delete and uninstall)** en un paso; esto también elimina sus dispositivos y entidades de Home Assistant. Atiende el aviso de reinicio. Con HACS, elimina la entrada y después su descarga.

No se eliminan chimeneas ni la cuenta del fabricante. Quitar un repositorio de **Añadir desde enlace** solo gestiona su presencia en la lista; utiliza **Desinstalar** para retirar sus archivos.
