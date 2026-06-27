# App Catalog

Desktop launchers and companion scripts collected from this Kali machine.  
Each entry includes a plain-language description of what the app does.

> **Note:** Some companion repos (`youtube-ripper`, `web-ripper`, `usb-drive-repair`) were created from a Linux Mint install and are documented separately — source not yet on this machine.

---

## GitHub repositories

| Repository | What it is |
|---|---|
| [kali-custom-launchers](https://github.com/willlccasey/kali-custom-launchers) | This repo — Kali desktop launchers + `~/bin` scripts |
| [youtube-ripper](https://github.com/willlccasey/youtube-ripper) | YouTube video downloader (Linux Mint origin) |
| [web-ripper](https://github.com/willlccasey/web-ripper) | Web page archiver / offline ripper (Linux Mint origin) |
| [usb-drive-repair](https://github.com/willlccasey/usb-drive-repair) | USB drive repair and recovery toolkit (Linux Mint origin) |
| [Kali-Youtube-ripper](https://github.com/willlccasey/Kali-Youtube-ripper) | Legacy YouTube ripper — superseded by `youtube-ripper` |

---

## Wi-Fi / wireless

| App | Launcher | What it does |
|---|---|---|
| **Wifite** | `Wifite.desktop` | Wi-Fi auditor — automated attacks plus offline handshake cracking without monitor mode. |
| **Jam-Fi** | `Jam-Fi.desktop` | Wi-Fi chaos tool — deauth, evil twin, MITM, CVE exploits, Karma, auto-pwn. |
| **WiFi Pentest Kit** | `WiFi-Pentest-Kit.desktop` | GUI for mehedishakeel/WiFi-Pentest-Kit — scanner, deauth, evil twin, beacon spam, handshake capture, WebUI simulator. |
| **WiFi Cards** | `WiFi-Cards.desktop` | Lists all WiFi adapters; shows protected vs attack-ready cards with fix suggestions. |
| **Network Reset** | `Network-Reset.desktop` | Resets network/monitor mode (ASUS-focused); brings cards down for a clean attack state. |
| **Chasing Your Tail NG** | `Chasing-Your-Tail-NG.desktop` | Wi-Fi probe-request analyzer for surveillance/stalking detection — Kismet, GPS, persistence scoring, KML/Google Earth reports. |
| **IP & MAC Changer** | `ip-mac-changer.desktop` | Menu-driven IP and MAC spoofing with rolling random mode. |

---

## SDR / radio / GSM

| App | Launcher | What it does |
|---|---|---|
| **HackRF Tools** | `HackRF-Tools.desktop` | Numbered menu for HackRF One — kalibrate, gqrx, SDR++, inspectrum, GR-GSM scanner/livemon/decode, GSMTAP to Wireshark. |
| **IMSI-Catcher** | `IMSI-Catcher.desktop` | GSM IMSI catcher menu — `simple_IMSI-catcher.py`, livemon, Wireshark; HackRF + gr-gsm friendly. |
| **SDRTrunk** | `sdrtrunk.desktop` | Trunked radio scanner for P25, DMR, NXDN, and similar modes. |
| **Universal Radio Hacker** | `urh.desktop` | Analyze, demodulate, and reverse-engineer wireless protocols. |

---

## Bluetooth / BLE

| App | Launcher | What it does |
|---|---|---|
| **Bluetooth Tools** | `Bluetooth-Tools.desktop` | Main Bluetooth pentest hub — numbered menu for btscanner, Kismet nRF, HackRF, sniffer manager, etc. |
| **Spam Jam** | `Spam-Jam.desktop` | BLE & Bluetooth attack toolkit — spam, jam, L2Ping, RFCOMM, mesh botnet. |
| **Bettercap BLE Launcher** | `Bettercap-BLE-Launcher.desktop` | Pick BT device (hci0 / Raytac-nRF / Ubertooth), then run bettercap BLE commands from a dropdown. |
| **Bettercap BLE Pentest** | `Bettercap-BLE-Pentest.desktop` | Bettercap BLE module + web UI for scanning, enumeration, characteristic writes, MITM-style attacks. |
| **nRF Connect** | `nRF-Connect.desktop` | Nordic Semiconductor GUI for BLE scanning and services/characteristics exploration. |
| **nRF BLE Pentest Suite** | `nRF-BLE-Pentest-Suite.desktop` | One-click stack: nRF Connect, Bettercap, Wireshark/Kismet, crackle, BlueZ tools. |
| **USB Manager** | `Sniffer-USB-Manager.desktop` | Switch between Ubertooth / Raytac-nRF / HackRF / onboard BT; one-click optimization and passwordless sudo. |
| **ubertooth-util** | `kali-ubertooth-util.desktop` | Graphical menu for Ubertooth tools — prepare dongle, USB exclusive mode, hci setup. |

---

## Privacy / Tor

| App | Launcher | What it does |
|---|---|---|
| **Tor Browser** | `tor-browser-onion.desktop` | Launches Tor Browser with smart Tor bootstrap. |
| **Tor Browser — New Identity** | `tor-browser-new-identity.desktop` | Launches Tor with a completely fresh circuit and identity. |

---

## Grok / AI coding

| App | Launcher | What it does |
|---|---|---|
| **Grok Build** | `grok-build.desktop` | Grok Build interactive coding agent (TUI). |
| **Grok Composer 2.5** | `grok-composer-2.5.desktop` | Grok Build with Composer 2.5 Fast model. |
| **Grok Build (YOLO)** | `grok-yolo.desktop` | Grok Build in always-approve / YOLO mode. |

---

## Utilities

| App | Launcher | What it does |
|---|---|---|
| **INTERCEPT** | `INTERCEPT.desktop` | One-click local web server for INTERCEPT — auto-opens browser, passwordless sudo, kills stale processes. |
| **Viking GPS** | `Viking-GPS.desktop` | Live OpenStreetMap GPS tracker for u-blox USB via gpsd; installs Viking on first launch. |
| **OCR Image** | `ocr-image.desktop` | Open a JPEG/image and copy recognized text to clipboard. |
| **GitHub Launcher Sync** | `GitHub-Launcher-Sync.desktop` | Collects custom launchers/scripts and pushes to GitHub via `gh` CLI. |

---

## Companion scripts (`bin/`)

| Path | Powers |
|---|---|
| `launch-hackrf-menu.sh` | HackRF Tools terminal menu |
| `launch-imsi-catcher-menu.sh` | IMSI-Catcher menu |
| `bluetooth-menu.sh` / `bluetooth-zenity.sh` | Bluetooth Tools GUI menus |
| `bettercap-ble-launcher.sh` | Bettercap BLE Launcher |
| `sniffer-usb-manager/` | USB Manager Python GUI + priv-helper |
| `wifite-launcher/` | Wifite Python GUI |
| `wifi-pentest-kit/` | WiFi Pentest Kit Python UI |
| `jam-fi/` | Jam-Fi launcher |
| `spam-jam/` | Spam Jam launcher |
| `cyt-ng/` | Chasing Your Tail NG full project |
| `viking-gps/` | Viking GPS launcher |
| `ip-mac-changer.sh` | IP & MAC Changer |
| `show-wifi-cards.sh` | WiFi Cards display |
| `nrfconnect.sh` / `nrf-ble-pentest-menu.sh` | nRF Connect + BLE pentest suite |
| `tor-browser-onion` / `tor-browser-new-identity` | Tor Browser launchers |
| `ocr-image` | OCR image tool |
| `gh-launcher-sync/` | GitHub sync scripts |
| `grok-build` / `grok-composer` / `grok-launch` | Grok app wrappers |

---

## On desktop, not yet in repo

| App | What it does |
|---|---|
| **PortaPack SD Flash** | Flashes Mayhem v2.4.0 to PortaPack SD card (Morse + Hopper). |

---

## Linux Mint tools (separate repos)

These were set up from a Linux Mint install. Source code is not on this Kali machine yet.

| Repo | Intended purpose |
|---|---|
| **youtube-ripper** | Download and save YouTube videos (audio/video formats). |
| **web-ripper** | Archive web pages for offline viewing. |
| **usb-drive-repair** | Diagnose, repair, partition, and recover USB drives. |