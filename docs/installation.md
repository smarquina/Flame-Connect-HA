# Installation and account linking

This is an **unofficial** integration. Check that your Wi-Fi fireplace is accessible through the original Flame Connect app and that your account has access to it.

## Install from the Marketplace (Home Assistant 2026.11 or later)

[![Open Flame Connect in your Home Assistant Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=smarquina&repository=Flame-Connect-HA&category=integration)

The button opens the repository page in your instance. Confirm adding the custom repository if requested, install a published version, and restart when prompted. If the shortcut cannot add or open the repository on your version, use these steps:

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

[![Open Flame Connect in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=smarquina&repository=Flame-Connect-HA&category=integration)

Add `https://github.com/smarquina/Flame-Connect-HA` as a custom repository of type **Integration**. Download a version and restart Home Assistant. Add **Flame Connect (unofficial)** under **Settings → Devices & services**.

When upgrading Home Assistant to **2026.11**, the Marketplace automatically migrates HACS installations, custom repositories, and update entities. HACS is no longer installed separately; use **Settings → Marketplace**. This change of installer does not require linking your Flame Connect account again.

Official references: [HACS to Marketplace migration](https://hacs.xyz/docs/marketplace/) and [using the Marketplace](https://next.home-assistant.io/integrations/marketplace/).

The [My Home Assistant redirect definitions](https://github.com/home-assistant/my.home-assistant.io/blob/main/redirect.json) use `marketplace_repository` for the new Marketplace. The older `hacs_repository` redirect is retained as a legacy alias. If it redirects to an unsupported page on Home Assistant 2026.10.4, use HACS → Custom repositories as described above.

## Manual installation

1. Download and extract the source archive of the desired [published release](https://github.com/smarquina/Flame-Connect-HA/releases). For a beta, choose its pre-release explicitly.
2. Copy the archive's `custom_components/flame_connect` directory, including its contents, into your Home Assistant configuration directory under `custom_components/flame_connect`. Create `custom_components` if needed. Do not rename the integration directory to `flameconnect`.
3. The installed manifest must be at `<config>/custom_components/flame_connect/manifest.json`, with no extra nested repository folder. Use your installation's file-access method, such as an editor, file share, or SSH.
4. Restart Home Assistant to load the files, then add the integration below. For manual updates, replace the whole integration directory with the version you intend to install and restart again.

Reading documentation in a feature branch does not install that branch's code. Choose a release that includes the controls you want; draft PRs are not releases.

## Add the integration

After installation and restart:

[![Add the Flame Connect integration to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=flame_connect)

The shortcut uses the integration domain `flame_connect`. It opens setup on your own Home Assistant and does not install the component or configure an account automatically. Alternatively, open **Settings → Devices & services → Add integration → Flame Connect (unofficial)**. Continue with either sign-in method below.

## Link directly from Home Assistant

1. Choose **Email and password** and the **Phone or email** account type.
2. Enter your Flame Connect email address and password. This method supports email/password accounts; phone sign-in uses the browser alternative below.
3. Confirm, select at least one Wi-Fi fireplace, choose the preferred temperature unit, and finish.

Credentials are used once to complete the official B2C form over HTTPS. Neither email nor password is stored in the configuration entry; only the resulting tokens and selected fireplaces are saved. Temporary sign-in cookies are discarded when the request ends. No desktop assistant is required for this method.

If sign-in fails or requires external identity, additional verification, password reset, or account registration, select **Use browser linking instead**. Leave the credential fields empty when choosing this alternative. There are no automatic credential retries. Direct sign-in has automated coverage but still needs validation with your account.

## Browser linking from your computer

The provider registers a native mobile return address, `msal…://auth`, rather than a Home Assistant web callback. Browser linking uses an assistant running **on your computer** to capture that return. Home Assistant generates the PKCE verifier and exchanges the code. The desktop assistant only opens Chrome and captures the one-use authorization code.

1. In Home Assistant, choose **Browser with desktop assistant**, then **Phone or email** (`normal`) or **External identity provider** (`social`). External providers always use browser linking.
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

The temporary browser closes and its profile is removed when finished. The assistant communicates with it through private inherited pipes and does not open a browser debugging port. Home Assistant validates state, PKCE, token signatures, issuer, expiry, and account identity. The account is saved only after its fireplace list is successfully retrieved.

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

| Field as shown in English | Values and default | Where to obtain it / purpose |
|---|---|---|
| Sign-in method | Email and password (default), or Browser with desktop assistant | Choose how to authenticate. Phone sign-in and interactive challenges use the browser alternative. |
| Account type | Phone or email (default, `normal`), or External identity provider (`social`) | Use the method with which you registered in the original app. External providers always use browser linking. |
| Email | Your Flame Connect account email; empty by default | Use the same address as in the original app. Used only for direct sign-in; not saved. |
| Password | Your Flame Connect password; empty by default | The password for that account. Reset it using the official app/provider if forgotten. Not saved; external-provider passwords belong in hosted browser login. |
| Use browser linking instead | Off by default | Turn on to switch methods; email/password fields can stay empty. |
| Native return URL | One-use `msal…://auth?code=…&state=…` return | Copy from the desktop assistant for the current authorization transaction. Never enter a JWT or password here. |
| Fireplaces | At least one returned Wi-Fi fireplace; all returned compatible devices selected initially | The list comes from your authenticated account. Register the fireplace in the original app first. |
| Preferred temperature unit | Automatic (default, `auto`), C, or F | Automatic follows the physical display preference, falling back to Celsius when absent. Home Assistant display conversions still apply; the device scale is not changed. |

## Options after setup

Open **Settings → Devices & services → Flame Connect (unofficial) → Configure**. The available options are:

| Option as shown in English | Default | Accepted values and effect |
|---|---|---|
| Preferred temperature unit: auto / C / F | Automatic | `auto`, `C`, `F`. Changes entities' native presentation while respecting Home Assistant conversions. It does not change the Celsius meaning of API temperatures or the device display scale. |
| Create experimental controls | Off | On/off. Adds supported flame-color, countdown, sound, and display-scale controls. They start disabled; enable each entity individually. |

**Create experimental controls:** adds color, countdown, sound, and display-scale controls according to capabilities. Entities start disabled and can be enabled individually. Changing this option sends no commands.

Changing either option reloads the integration without restarting Home Assistant. Heating presets and Heating boost duration do not require experimental controls; their visibility depends on the model. See [the control guide](controls.md).

Fireplaces are selected during setup. To change the selection, open the configuration entry menu and choose **Reconfigure**. This retrieves the account's current list without deleting the entry. Reauthentication preserves the selection.

## Reauthentication

When Home Assistant requests reauthentication, open the notice and repeat linking with **the same account**. Do not delete the integration or paste a JWT manually. Device identifiers and the selected fireplaces are preserved.

## Update or remove

Marketplace updates appear under **Settings → Updates**. Review the release notes, keep a backup, and install the update. Restart Home Assistant to load the new files; **Settings → System → Repairs** provides a reminder. On Home Assistant 2026.10.4, update through HACS and follow its restart instructions.

To remove the integration, first delete its entry under **Devices & services**, then open the repository page in the Marketplace → menu → **Uninstall**. If still configured, the Marketplace offers **View integration** or **Delete and uninstall**; deleting the setup also removes its Home Assistant devices and entities. Follow the restart notice. With HACS, delete the entry and then its download.

This does not delete fireplaces or your manufacturer account. Removing a repository from **Add from link** only manages its listing; use **Uninstall** to remove its files.
