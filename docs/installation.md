# Instalación y vinculación de la cuenta

Integración **no oficial**. Antes de empezar, comprueba que tu chimenea Wi-Fi puede consultarse desde la app original de Flame Connect y que la cuenta tiene acceso.

## Instalar con HACS

Añade `https://github.com/smarquina/Flame-Connect-HA` como repositorio personalizado de tipo Integración. Descarga una versión y reinicia Home Assistant. Añade **Flame Connect (unofficial)** desde Ajustes → Dispositivos y servicios.

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

Actualiza a través de HACS y atiende su indicación de reinicio. Antes de cambiar de versión conserva una copia de seguridad habitual de Home Assistant.

Para eliminar, borra la entrada de Dispositivos y servicios y después la descarga de HACS si lo deseas. No se eliminan chimeneas de la cuenta del fabricante.
