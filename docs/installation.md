# Installation and account linking

This is an **unofficial** integration. Check that your Wi-Fi fireplace is accessible through the original Flame Connect app and that your account has access to it.

## Install from the Marketplace (Home Assistant 2026.11 or later)

1. As an administrator, open **Settings → Marketplace** and accept the community-content notice.
2. Select **Add from link** and enter `https://github.com/smarquina/Flame-Connect-HA`.
3. If prompted, connect GitHub using the code and link shown by Home Assistant. This connection lets the Marketplace read the custom repository and its updates; it is separate from your Flame Connect login.
4. Select **Add**. If the type is not identified automatically, choose **Integration** and confirm again.
5. Open the repository page, select **Install**, review the version, and confirm. Follow any restart instructions.
6. Continue with the configuration opened by Home Assistant, or open **Settings → Devices & services → Add integration → Flame Connect (unofficial)**.

Adding the repository by link does not imply inclusion in the default catalog, certification, or support by Home Assistant. Flame Connect's tested baseline remains **2026.10.4**; these Marketplace instructions follow the **2026.11** documentation and do not claim runtime validation on that version.

### Beta releases

The Marketplace offers stable releases by default. To receive pre-releases, open the repository device under **Settings → Devices & services → Marketplace**, enable the disabled **Pre-release** entity, and turn its switch on. To choose an available version, open the repository page menu → **Install another version**. The version must be published on GitHub; a draft PR is not an installable release.

## Install with HACS (Home Assistant 2026.10.4)

Add `https://github.com/smarquina/Flame-Connect-HA` as a custom repository of type **Integration**. Download a version and restart Home Assistant. Add **Flame Connect (unofficial)** under **Settings → Devices & services**.

When upgrading Home Assistant to **2026.11**, the Marketplace automatically migrates HACS installations, custom repositories, and update entities. HACS is no longer installed separately; use **Settings → Marketplace**. This change of installer does not require linking your Flame Connect account again.

Official references: [HACS to Marketplace migration](https://hacs.xyz/docs/marketplace/) and [using the Marketplace](https://next.home-assistant.io/integrations/marketplace/).

## Link from your computer

The provider registers a native mobile return address, `msal…://auth`, rather than a Home Assistant web callback. Initial linking therefore uses an assistant running **on your computer**. Home Assistant generates the PKCE verifier and exchanges the code. The desktop assistant only opens Chrome and captures the one-use authorization code.

1. In Home Assistant, select **Phone or email** (`normal`) or **External identity provider** (`social`).
2. Leave the linking step open and copy its complete **official authorization URL**. Paste it into the desktop assistant in step 5; do not open it directly in Firefox or your usual browser. It expires in 10 minutes.
3. Download and extract the repository ZIP matching your installed version on your computer.
4. With Node.js 22.15 or later installed, open a terminal in that folder and run:

   ```sh
   node tools/link/link.mjs
   ```

5. Paste the link when prompted. The assistant validates the official provider and opens an isolated temporary Chrome profile.
6. Enter your credentials only on the official page. The assistant does not request or store your password.
7. After login, copy the `msal…://auth?code=…&state=…` return shown in the terminal into Home Assistant's protected field.
8. Confirm, select at least one Wi-Fi fireplace, choose Automatic, Celsius, or Fahrenheit, and finish.

Do not share the return URL: it contains a one-use code. It is not a JWT or password. Do not reuse a link from a previous attempt. After an error, use the new link shown by Home Assistant.

The desktop assistant must own the temporary login window to capture the native return. Opening the authorization URL directly in your regular browser does not provide this capture. A generic B2C `400 Bad Request` does not establish whether credentials are incorrect: start a new linking attempt and use the assistant's temporary window. If it still fails there, report only the assistant's sanitized error message.

The temporary browser closes and its profile is removed when finished. Home Assistant validates state, PKCE, token signatures, issuer, expiry, and account identity. The account is saved only after its fireplace list is successfully retrieved.

### Locate your browser

Chrome, Edge, and Chromium are searched for in common macOS and Linux paths. For another path, or on Windows, set `FLAME_CHROME_PATH` to the browser executable's full path before starting the assistant.

macOS/Linux:

```sh
FLAME_CHROME_PATH='/path/to/browser' node tools/link/link.mjs
```

PowerShell:

```powershell
$env:FLAME_CHROME_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
node tools/link/link.mjs
```

Do not run the assistant inside Home Assistant OS or reuse your personal browser profile. Close the official login window to cancel; start linking again if the transaction expires.

## Language

Setup, options, entity labels, selectable values, and errors are translated into **English and Spanish**. Change the interface language in your Home Assistant user profile. Backend-generated entity names follow Home Assistant's system language; user-defined names and account-provided fireplace names are preserved. The integration needs no separate language option, and its automation values are language-independent. The desktop assistant and this documentation use English.

## Configuration parameters

| Field | Purpose |
|---|---|
| Account type | Normal phone/email or social B2C policy |
| Native return URL | One-use result captured by the desktop assistant |
| Fireplaces | Account Wi-Fi devices to create in Home Assistant |
| Preferred temperature unit | `auto`, `C`, or `F`; does not change the physical display scale |

## Options after setup

**Preferred temperature unit:** changes entities' native presentation while respecting Home Assistant's conversions. It does not change the Celsius meaning of API temperatures.

**Create experimental controls:** adds color, countdown, sound, and display-scale controls according to capabilities. Entities start disabled and can be enabled individually. Changing this option sends no commands.

Fireplaces are selected during setup. To change the selection, open the configuration entry menu and choose **Reconfigure**. This retrieves the account's current list without deleting the entry. Reauthentication preserves the selection.

## Reauthentication

When Home Assistant requests reauthentication, open the notice and repeat linking with **the same account**. Do not delete the integration or paste a JWT manually. Device identifiers and the selected fireplaces are preserved.

## Update or remove

Marketplace updates appear under **Settings → Updates**. Review the release notes, keep a backup, and install the update. Restart Home Assistant to load the new files; **Settings → System → Repairs** provides a reminder. On Home Assistant 2026.10.4, update through HACS and follow its restart instructions.

To remove the integration, first delete its entry under **Devices & services**, then open the repository page in the Marketplace → menu → **Uninstall**. If still configured, the Marketplace offers **View integration** or **Delete and uninstall**; deleting the setup also removes its Home Assistant devices and entities. Follow the restart notice. With HACS, delete the entry and then its download.

This does not delete fireplaces or your manufacturer account. Removing a repository from **Add from link** only manages its listing; use **Uninstall** to remove its files.
