# Ford Charge Station Pro Local for Home Assistant (`local_fcsp`)

**Author:** Nikki Gordon-Bloomfield  
**Based on:** [Eric Pullen’s `fcsp-api`](https://github.com/ericpullen/fcsp-api)

---

## ⚡ What is this?

A Home Assistant **custom integration** that polls your **Ford Charge Station Pro (FCSP)** over the **local network** — no cloud required.

It wraps the excellent [fcsp-api](https://github.com/ericpullen/fcsp-api) Python library and surfaces status, power flow, and inverter data (if present) as **native sensors** in Home Assistant.

---

## 🛠️ Features

- 🔌 Detects vehicle connection & charging status  
- ⚡️ Monitors home power flow (Intelligent Backup Power)  
- 🏠 Shows inverter status and details (if connected)  
- 🕒 Adds “Last Updated” sensors showing relative time (e.g., _“2 minutes ago”_)  
- 🧪 Optional debug sensors with JSON output for developers  
- 🛡️ 100% local, no cloud dependency  
- 🧰 MDI icons and clean device grouping in the UI  

---

## 🚨 Requirements & Caveats

- Your **FCSP must be accessible over your local network** (IP address required).
- The **developer key (`devkey`) is currently universal** — it’s auto-filled during setup.
- Inverter sensors will only show up if an inverter is detected.
- This is a personal project, not an official or commercial tool — use at your own risk.

---

## 📦 Installation

### ✅ HACS (Recommended)

1. Go to **HACS → Integrations → Custom Repositories**
2. Add: `https://github.com/Aminorjourney/fcsp-local-for-home-assistant`
3. Choose **Integration**
4. Install → Reboot Home Assistant

### 📁 Manual

1. Copy the entire `fcsp_local/` folder into `config/custom_components/`  
2. Restart Home Assistant  
3. Go to **Settings → Devices & Services → Add Integration**  
4. Search for **"Ford Charge Station Pro Local"** and follow the setup wizard

---

## 🔍 Available Sensors

| Sensor Name           | Description                                        | Icon                       | Prefix                       |
|------------------------|----------------------------------------------------|-----------------------------|-------------------------------|
| **Info**               | Model, serial, firmware, IP address, etc.         | `mdi:ev-plug-ccs1` / `mdi:home-import-outline` | `sensor.ford_charge_station_pro_` / `sensor.home_integration_system_` |
| **Status**             | EV state: Idle, Charging, etc.                    | `mdi:ev-station`            | `sensor.ford_charge_station_pro_status`     |
| **State**              | Inverter status (Off, Powering Home, etc.)        | `mdi:sine-wave`             | `sensor.home_integration_system_state`      |
| **Last Updated**       | How fresh the data is ("x minutes ago")           | `mdi:update`                | `sensor.<device>_last_updated`              |
| **Raw Data** (optional) | Full cleaned JSON output for nerds                | `mdi:magnify`               | `sensor.<device>_raw_data`                  |
| **System Info** (optional) | Charger config, network info, device summary     | `mdi:file-document`         | `sensor.config_status`, etc.                |

> 💡 Sensor names may vary slightly in Home Assistant but are always prefixed with `ford_charge_station_pro` or `home_integration_system`.

---

## 🧪 Debug Mode

When enabled during setup:

- Adds sensors showing raw JSON data for charger, inverter, and system internals
- Useful for troubleshooting, reverse-engineering, or future development

Disable debug mode to hide them.

---

## 🔄 Polling & Updates

- The default polling interval is **30 seconds**
- You can change it via the integration options menu
- To update, just pull the latest code and restart Home Assistant

---

## 👩‍💻 Developer Notes

- Uses `DeviceInfo` to register the **FCSP** and (optionally) the **Inverter**
- All sensors are tied to their respective device for better UI grouping
- Time parsing uses Home Assistant’s built-in `dt` helpers
- Raw inverter firmware is converted to readable **hex string** (`01 02 03…`)
- Null characters, extra whitespace, and junk are removed from sensor fields

---

## 📜 License & Disclaimer

MIT License — see the `LICENSE` file.

This project is unofficial, unsupported, and likely imperfect. It may break, behave oddly, or do weird stuff.  
Use at your own risk — and please don’t sue me if it melts your FCSP.

---

## 🙏 Thanks

- 🙌 [Eric Pullen](https://github.com/ericpullen) for building `fcsp-api`
- ❤️ The Home Assistant devs and community
- 🔌 EV folks everywhere who just want good tools that don’t need cloud

---

## 📣 Contact

Built by **Nikki Gordon-Bloomfield** from [Transport Evolved](https://youtube.com/transportevolved)

- GitHub issues? 👉 [fcsp-local-integration/issues](https://github.com/Aminorjourney/fcsp-local-integration/issues)
- Mastodon: [@Aminorjourney@lgbtqia.space](https://lgbtqia.space/@Aminorjourney)
