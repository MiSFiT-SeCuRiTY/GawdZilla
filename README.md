<div align="center">
 
  # ◤ GawdZilla 🛡️

**Open-source parental-control & device-management platform for Android**

Self-hosted · Cyberpunk dashboard · No third-party cloud · No telemetry · AGPL-3.0

**Created by MiSFiT SeCuRiTY**
</div>

---

<img width="1668" height="998" alt="Screenshot_2026-10-09_12_13_27" src="https://github.com/user-attachments/assets/582c4cdc-d10a-461b-947b-6e29cb1ebb8c" />

## 📖 About

GawdZilla is a self-hosted parental-control platform. A parent runs the control panel on their own PC, home server, or VPS and enrolls Android devices used by their minor children.

Data stays on infrastructure you control. GawdZilla is intended for parents managing devices they own or are authorized to administer. It is not a stealth or spying tool.

---

## ✨ Features

### 🖥️ Admin Dashboard
- Cyberpunk-themed web dashboard
- Admin and parent roles, CSRF protection, rate limiting, and hardened sessions
- Device, child, and policy management
- Live monitor with WebSocket event feed
- Audit log of administrative actions
- Manual and scheduled backups, including automatic backups every 6 hours
- Cloudflare Tunnel support through the launcher
- HTTPS-ready with self-signed certificate generation
- TOTP two-factor authentication

### 🛠️ Enrollment Builder
- Guided flow: Android version → architecture → child → capabilities → build
- Enrollment ZIP containing `manifest.json`, `consent.txt`, `README.txt`, and a token
- SHA-256 checksum for each build
- Build history, token management, and token revocation

### 📱 Android Agent
- Foreground service with a persistent, visible notification
- Device Admin and Device Owner provisioning options
- Device enrollment, heartbeat, and authenticated remote-command channel
- Screen-time lock and bedtime scheduling
- App allow/block policies through Android `DevicePolicyManager`
- Location tracking and geofence enter/exit events
- Per-app usage statistics
- Notification mirroring and clipboard synchronization
- Camera and microphone capture, with operating-system indicators
- Permission-gated SMS, contacts, and call-log access with an on-device consent screen

### 🎛️ Remote Commands
Supported command types include `ping`, `lock`, `sysinfo`, `usage`, `sms`, `contacts`, `call_log`, `camera`, `mic`, `settings`, `open_url`, `launch`, `app_block`, `policy_sync`, `block_uninstall`, `unblock_uninstall`, `device_owner_status`, `wipe_cache`, and `wipe_data`.

Use sensitive commands only on devices you own or are authorized to administer, with the required consent and permissions.

---

## 📂 Repository Structure

```
GawdZilla/
│
├── GawdZilla.py              ⭐ Main launcher (ASCII menu, tunnel control)
├── VERSION                   → 1.0.0
├── requirements.txt          Python dependencies
├── LICENSE                   AGPL-3.0
├── README.md                 You are here
├── Makefile                  make venv / install / run / pack
├── Dockerfile + docker-compose.yml
├── pack.sh + pack.bat        Build source ZIP for release
├── .gitignore
│
├── core/                     Backend logic
│   ├── config.py             Paths, ports, intervals
│   ├── db.py                 SQLite schema + helpers
│   ├── auth.py               bcrypt, TOTP, tokens
│   ├── builder.py            Enrollment ZIP generation
│   ├── backups.py            Auto/manual backup + scheduler
│   ├── certs.py              Self-signed TLS generator
│   ├── events.py             Event bus, metrics, alerts
│   └── security.py           Rate limits + helpers
│
├── server/                   Flask web server
│   ├── app.py                Factory, auth, security, WSGI
│   ├── routes_admin_pages.py All /admin/* HTML pages
│   ├── routes_builder.py     /admin/builder/*
│   ├── routes_device.py      /device/* (token auth)
│   ├── routes_api.py         /api/* JSON
│   ├── routes_ws.py          /ws/live WebSocket
│   └── routes_stubs.py       Supplementary routes
│
├── templates/                28 Jinja2 HTML pages
│   ├── base.html             Layout + sidebar
│   ├── login.html / password.html / totp.html
│   ├── dashboard.html / devices.html / children.html
│   ├── policies.html / location.html / apps.html / web.html
│   ├── monitor.html / charts.html / live_map.html
│   ├── sync.html / remote.html / terminal.html
│   ├── builder.html / builder_history.html / builder_tokens.html
│   ├── audit.html / backup.html / settings.html
│   └── enroll.html / provision.html / device_detail.html
│
├── static/                   Frontend assets
│   ├── css/cyberpunk.css     Neon + dark theme
│   ├── js/dashboard.js
│   └── vendor/               Leaflet, Chart.js (offline)
│
├── agents/                   Native agent source
│   └── android/              Kotlin + Gradle project
│       ├── app/src/main/java/com/misfit/gawdzilla/
│       │   ├── MainActivity.kt           Setup UI
│       │   ├── ConsentActivity.kt        Consent screen
│       │   ├── AgentService.kt           Foreground service
│       │   ├── ApiClient.kt              OkHttp REST
│       │   ├── Commands.kt               Command dispatch
│       │   ├── PolicyEngine.kt           Screen time + app rules
│       │   ├── LocationTracker.kt        GPS
│       │   ├── UsageReader.kt            App usage
│       │   ├── NotificationListener.kt   Mirror
│       │   ├── ClipboardWatcher.kt       Clipboard sync
│       │   ├── CameraCaptureActivity.kt
│       │   ├── MicCaptureActivity.kt
│       │   ├── SmsReader.kt / ContactsReader.kt / CallLogReader.kt
│       │   ├── DeviceAdminReceiver.kt
│       │   ├── SysInfo.kt / Prefs.kt
│       │   └── …
│       ├── app/src/main/AndroidManifest.xml
│       ├── app/src/main/res/             Layouts, strings, themes
│       ├── build.gradle / settings.gradle
│       └── gradlew / gradle/wrapper/
│
└── data/                     Runtime (gitignored except .gitkeep)
    ├── .gitkeep
    ├── logs/  backups/  builds/  media/  certs/  uploads/
```

---

## 🚀 Installation

### Requirements

- **Python 3.10+**
- Git
- *(Optional)* `cloudflared` for a public URL through Cloudflare Tunnel
- *(For building the Android agent)* **JDK 17 or 21 (not 22+)**, Android SDK API 34, and the Gradle wrapper included in the project

> ⚠️ Gradle 8.5 supports Java 17 and 21, **not** 22+.
> If `java -version` shows 22 or higher, install JDK 21 first:
> ```bash
> sudo apt install -y openjdk-21-jdk
> export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
> export PATH="$JAVA_HOME/bin:$PATH"
> ```

---

### 🐧 Linux / macOS

```bash
# 1. Clone
git clone https://github.com/MiSFiT-SeCuRiTY/GawdZilla.git
cd GawdZilla

# 2. Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Launch
python3 GawdZilla.py
```

---

### 🪟 Windows

```powershell
git clone https://github.com/MiSFiT-SeCuRiTY/GawdZilla.git
cd GawdZilla

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python GawdZilla.py
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

### 🐳 Docker

```bash
docker compose up -d
```

Open the dashboard at **http://localhost:7777/admin**.

---

> 🔒 **Security note:** the server listens on `0.0.0.0:7777` (all interfaces).
> On a public VPS, either restrict the port with a firewall:
> ```bash
> sudo ufw allow from <your-ip> to any port 7777
> ```
> or use Cloudflare Tunnel (launcher option 2) so nothing is exposed directly.

---

## 🎬 First Run

Launch GawdZilla:

```bash
python3 GawdZilla.py
```

The launcher menu provides:

```
[1] Start server  (localhost + LAN)
[2] Start server  + Cloudflare Tunnel (public URL)
[3] Stop server / disconnect tunnel
[4] Show status & URLs
[5] Open admin dashboard in browser
[6] Exit
```

1. Select **`1`** to start the server.
2. Open **http://127.0.0.1:7777/admin**.
3. Sign in with the initial credentials **`admin` / `admin`**.
4. Change the default password immediately when prompted.
5. Optionally enable TOTP 2FA in **Settings**.

> ⚠️ **Never leave default credentials in place or expose the dashboard publicly before securing the account and deployment.**

---

### ☁️ Cloudflare Tunnel (launcher option 2)

Install `cloudflared`:

**Linux (Kali / Ubuntu / Debian):**

```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -O /tmp/cloudflared
chmod +x /tmp/cloudflared
sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
```

**macOS:**

```bash
brew install cloudflared
```

**Windows:** download from
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

Then pick launcher option **`2`**. The public `trycloudflare.com` URL appears in the terminal within a few seconds.

---

### 📦 Building a source release

`./pack.sh` (Linux / macOS) or `pack.bat` (Windows) produces
`GawdZilla-v1.0.0.zip` — a clean source archive with no `.venv`,
no DB, no logs, no keystore. Use it for distribution or attach it
to a GitHub Release.

---

## 🎟️ Enrollment Workflow — From Build to Enrolled Device

Complete flow: **create a build → get a token → install the APK → enroll the device.**

### 1️⃣ Create a Build in the Dashboard

1. Log in to `http://127.0.0.1:7777/admin`
2. Sidebar → **▸ NEW BUILD** (magenta Builder section)
3. Fill the form:
   - **APP NAME:** `GawdZilla Agent` (default)
   - **ANDROID VERSION:** pick the child's Android version
   - **ARCHITECTURE:** `arm64-v8a` for most modern phones
   - **CHILD:** pick which child this device belongs to (or leave unassigned)
   - **SERVER URL:** `http://<your-server-LAN-IP>:7777` (e.g. `http://192.168.1.42:7777`)
   - **CAPABILITIES:** tick what the parent wants to enable
   - **NOTES:** optional, e.g. "Emma's school phone"
4. Click **⚙ BUILD ENROLLMENT PACKAGE**

### 2️⃣ What You Get

The Builder produces a ZIP in `data/builds/`:

```
gawdzilla-android-arm64-v8a-<build_id>.zip
├── manifest.json     full build metadata + capabilities
├── consent.txt       plain-language list of what will be shared
├── README.txt        install steps for this specific build
├── server.txt        the server URL
├── enroll_url.txt    full enrollment URL
└── token.txt         the enrollment token (GZ-XXXX-XXXX-XXXX)
```

Every build also gets a sidecar `.sha256` file for integrity verification.

### 3️⃣ Get the Enrollment Token

**Option A — from the ZIP:** open `token.txt` inside the downloaded ZIP.

**Option B — from the dashboard:** sidebar → **▸ TOKENS** (Builder section) → the top row shows the newest token. Copy the value that looks like `GZ-AB12-CD34-EF56`.

**Option C — create a token without a build (advanced):**

```bash
cd ~/Projects/GawdZilla
source .venv/bin/activate

python3 - << 'PYEOF'
from core import db, auth
tok = auth.new_enroll_token()
c = db.conn()
c.execute(
    "INSERT INTO enroll_tokens (token, platform, expires_at, used) VALUES (?,?,?,0)",
    (tok, "android", auth.token_expiry(7))
)
c.commit(); c.close()
print("TOKEN:", tok)
PYEOF
```

Tokens expire after **7 days** and can only be used **once**.

### 4️⃣ Build the APK

```bash
cd agents/android
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### 5️⃣ Configure the App on the Device

Open **GawdZilla Agent** on the child's Android device:

| Field | Value |
|---|---|
| **Server URL** | `http://<your-server-LAN-IP>:7777` (same Wi-Fi) |
| | `http://10.0.2.2:7777` (Android emulator) |
| | `https://<random>.trycloudflare.com` (public tunnel) |
| **Enrollment token** | paste the `GZ-…` token from step 3 |

Tap **Save**.

### 6️⃣ Start the Agent

1. Tap **Open consent screen**
2. Read the capability list
3. Tap **I agree — start agent**
4. Allow **Notifications** when prompted
5. Tap **Enable device admin** → **Activate**
6. Tap **Grant usage access** → enable GawdZilla Agent
7. Optionally tap **Grant notification access** → enable GawdZilla Agent

A persistent notification appears: **"GawdZilla Agent is active"**.

### 7️⃣ Verify Enrollment

Dashboard → **▸ DEVICES** → the phone appears with a green **Online** pill within ~30 seconds.

### 8️⃣ Test a Command

Sidebar → **▸ TERMINAL** → pick the device → type `ping` → Enter.

Expected within ~30 s:

```
gawdzilla> ping
[queued] ping
[result] {"id":1,"ok":true,"result":"pong"}
```

### 🔄 Re-enrollment

If the child uninstalls and reinstalls the app, create a **new token** — the old one is marked used. The device reuses the same row in the database once it enrolls again with a fresh token.

### 🚫 Revoking a Token

Sidebar → **▸ TOKENS** → click **REVOKE** on any active token. The token instantly becomes unusable for future enrollments.

### 🗑️ Removing a Device

Sidebar → **▸ DEVICES** → click **DEL** next to the device row.

Devices that go offline for more than 90 seconds automatically flip to **Offline** — you don't have to delete them manually, but the row stays until you do.

### ⏳ Token Expiry & Cleanup

- Tokens expire 7 days after creation
- Expired tokens are rejected by `/device/enroll`
- Used tokens cannot be reused
- To clean up old tokens, use the **REVOKE** button on each one, or delete the DB row via the API

---

## 🤖 Building the Android Agent

### Prerequisites (Kali / Ubuntu / Debian)

```bash
sudo apt install -y openjdk-21-jdk unzip wget

mkdir -p ~/Android/Sdk/cmdline-tools
cd ~/Android/Sdk/cmdline-tools
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O tools.zip
unzip tools.zip
mv cmdline-tools latest
rm tools.zip

export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools"

yes | sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

### Build a debug APK

```bash
cd agents/android
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME="$HOME/Android/Sdk"

./gradlew assembleDebug
```

Expected output: `app/build/outputs/apk/debug/app-debug.apk`

Install it with:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Signed release APK (optional)

```bash
# one-time keystore
keytool -genkeypair -v \
  -keystore gawdzilla.keystore -alias gawdzilla \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass gawdzilla123 -keypass gawdzilla123 \
  -dname "CN=GawdZilla, OU=MiSFiT SeCuRiTY"

cat > keystore.properties << 'EOF'
storeFile=gawdzilla.keystore
storePassword=gawdzilla123
keyAlias=gawdzilla
keyPassword=gawdzilla123
EOF

./gradlew assembleRelease
```

Output: `app/build/outputs/apk/release/app-release.apk`

> 🔒 `keystore.properties` and `*.keystore` are gitignored — do not commit them.

### Device Owner Mode

On a freshly provisioned device, Device Owner mode can be configured with ADB:

```bash
adb shell dpm set-device-owner com.misfit.gawdzilla/.DeviceAdminReceiver
```

Device Owner capabilities depend on Android version, provisioning state, and device policy. Provision only devices you own or are authorized to administer.

---

## 🔌 API Overview

### Device endpoints (token-authenticated)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/device/enroll` | One-time enrollment |
| `POST` | `/device/heartbeat` | Liveness and system information |
| `GET`  | `/device/command` | Poll queued commands |
| `POST` | `/device/command/result` | Submit command results |
| `POST` | `/device/location` | Location update and geofence check |
| `POST` | `/device/usage` | App usage snapshot |
| `POST` | `/device/notify` | Notification mirror |
| `POST` | `/device/clip` | Clipboard synchronization |
| `POST` | `/device/media` | Camera / microphone media upload |
| `POST` | `/device/sms` | SMS entries |
| `POST` | `/device/contacts` | Contacts list |
| `POST` | `/device/calllog` | Call log |
| `GET`  | `/device/policy` | Retrieve device policy |

### Dashboard endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/admin` | Dashboard |
| `GET`  | `/admin/{devices,children,policies,…}` | Dashboard pages |
| `POST` | `/admin/builder/create` | Create enrollment package |
| `POST` | `/admin/backup/export_json` | Export selected data |
| `WS`   | `/ws/live` | Live event stream |

---

## 🔐 Privacy, Safety & Legal Notice

GawdZilla is intended for parental control on devices used by your minor children and that you own or are authorized to administer.

- The Android agent displays a **persistent notification** while active.
- Camera and microphone use trigger **operating-system indicators**.
- **On-device consent** is required before monitoring begins.
- There is **no stealth mode, icon hiding, or antivirus-evasion** functionality.
- Sensitive data access depends on Android permissions and the consent granted on the device.

Installing or using monitoring software on another person's device without proper authorization or informed consent may violate local law. You are responsible for complying with the laws and regulations that apply in your jurisdiction.

---

## 🐛 Troubleshooting

| Problem | Suggested check |
|---|---|
| Port 7777 is already in use | `sudo fuser -k 7777/tcp` — identify the process first with `sudo ss -tlnp \| grep 7777` |
| Dashboard returns HTTP 500 | Check the server terminal for the traceback |
| Phone cannot reach the server | Confirm same Wi-Fi, use the server's LAN IP; test with `curl http://<server-ip>:7777/healthz` from the phone's browser |
| Android emulator cannot reach the server | Use `http://10.0.2.2:7777` instead of `127.0.0.1` |
| Agent appears offline | Reopen the app → Open consent screen → I agree; check network access and enrollment credentials |
| Pillow fails to build | `pip install "pillow>=11.0.0"` or `sudo apt install libjpeg-dev zlib1g-dev` |
| Gradle build fails on Java version | `sudo apt install openjdk-21-jdk` and set `JAVA_HOME` (see Requirements) |
| Xiaomi / HyperOS: "App not installed" | 1. Settings → About phone → tap **OS version** 7× to enable Developer options.<br>2. Settings → Additional settings → Developer options → turn **MIUI optimization** OFF (may need to tap *Reset to default values* 5× to reveal it).<br>3. Security app → App management → Permissions → gear icon → turn **USB install management** OFF. |
| Cloudflared not found | Install `cloudflared` (see **Cloudflare Tunnel** section) |

---

## 🤝 Contributing

Contributions are welcome for:

- Parental-control features
- Bug fixes
- UI improvements
- Documentation
- Android-version compatibility

Contributions that add **stealth, surveillance without consent, or evasion** features will be rejected. Do not disguise the app, hide its icon, bypass Android security protections, or enable silent access without a consent screen.

To contribute:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Follow the existing code style.
4. Test changes on at least one Android version when relevant.
5. Open a pull request with a clear description.

See also [`SECURITY.md`](SECURITY.md) for reporting vulnerabilities.

---

## 📜 License

GawdZilla is licensed under **AGPL-3.0**. See [LICENSE](LICENSE) for details.

Under the AGPL, modified versions made available to users over a network may need to provide those users access to the corresponding source code, subject to the license terms.

---

## 🙌 Credits

**Created by: MiSFiT SeCuRiTY**

- Python and Flask backend
- Cyberpunk-themed dashboard
- Kotlin Android agent
- OpenStreetMap and Leaflet
- Chart.js
- AGPL-3.0

---

<div align="center">

**⭐ If GawdZilla is useful to you, consider starring the repository. ⭐**

[github.com/MiSFiT-SeCuRiTY/GawdZilla](https://github.com/MiSFiT-SeCuRiTY/GawdZilla)

**Built with 🖤 by MiSFiT SeCuRiTY**

</div>
