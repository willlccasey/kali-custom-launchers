# Kali Custom Launchers (Index)

Catalog and install links for **standalone** Kali Linux desktop launcher repos.  
Each app lives in its own repository so you can install only what you need.

## Quick install (one app)

```bash
gh repo clone willlccasey/kali-wifite   # example
cd kali-wifite && ./install.sh
```

See **[APPS.md](APPS.md)** for the full list with descriptions and clone URLs.

## Standalone repos (24 apps)

| Category | Repos |
|---|---|
| Wi-Fi | [kali-wifite](https://github.com/willlccasey/kali-wifite) · [kali-jam-fi](https://github.com/willlccasey/kali-jam-fi) · [kali-wifi-pentest-kit](https://github.com/willlccasey/kali-wifi-pentest-kit) · [kali-wifi-cards](https://github.com/willlccasey/kali-wifi-cards) · [kali-network-reset](https://github.com/willlccasey/kali-network-reset) · [kali-chasing-your-tail-ng](https://github.com/willlccasey/kali-chasing-your-tail-ng) · [kali-ip-mac-changer](https://github.com/willlccasey/kali-ip-mac-changer) |
| SDR / GSM | [kali-hackrf-tools](https://github.com/willlccasey/kali-hackrf-tools) · [kali-imsi-catcher](https://github.com/willlccasey/kali-imsi-catcher) · [kali-sdrtrunk](https://github.com/willlccasey/kali-sdrtrunk) · [kali-urh](https://github.com/willlccasey/kali-urh) |
| Bluetooth | [kali-bluetooth-tools](https://github.com/willlccasey/kali-bluetooth-tools) · [kali-spam-jam](https://github.com/willlccasey/kali-spam-jam) · [kali-bettercap-ble](https://github.com/willlccasey/kali-bettercap-ble) · [kali-nrf-connect](https://github.com/willlccasey/kali-nrf-connect) · [kali-nrf-ble-pentest](https://github.com/willlccasey/kali-nrf-ble-pentest) · [kali-sniffer-usb-manager](https://github.com/willlccasey/kali-sniffer-usb-manager) · [kali-ubertooth-util](https://github.com/willlccasey/kali-ubertooth-util) |
| Privacy | [kali-tor-browser](https://github.com/willlccasey/kali-tor-browser) |
| Grok | [kali-grok-launchers](https://github.com/willlccasey/kali-grok-launchers) |
| Utilities | [kali-intercept](https://github.com/willlccasey/kali-intercept) · [kali-viking-gps](https://github.com/willlccasey/kali-viking-gps) · [kali-ocr-image](https://github.com/willlccasey/kali-ocr-image) · [kali-github-launcher-sync](https://github.com/willlccasey/kali-github-launcher-sync) |

## Linux Mint tools (separate)

| Repo | Purpose |
|---|---|
| [youtube-ripper](https://github.com/willlccasey/youtube-ripper) | YouTube downloader |
| [web-ripper](https://github.com/willlccasey/web-ripper) | Web page archiver |
| [usb-drive-repair](https://github.com/willlccasey/usb-drive-repair) | USB drive repair |

## Publish / update from your machine

Use the **GitHub Launcher Sync** desktop app or:

```bash
~/bin/gh-launcher-sync/split-packages.sh    # build all packages locally
~/bin/gh-launcher-sync/publish-packages.sh  # push each repo to GitHub
```

For authorized use on systems you own or have permission to test.