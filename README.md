# FCSP Local Integration for Home Assistant

**Author:** Nikki Gordon-Bloomfield  
**Based on:** [Eric Pullen's fcsp-api](https://github.com/ericpullen/fcsp-api)

---

## ⚡ What is this?

This is a Home Assistant **custom integration** that acts as a wrapper around Eric Pullen's excellent Python library for the **Ford Charge Station Pro (FCSP)**.  
It allows local polling of your FCSP to expose its **charging status**, **inverter behavior**, and **device metrics** as sensors within Home Assistant — all without relying on the cloud.

---

## 🛠️ Features

- Monitors EV connection and charging status
- Detects when power is flowing to the home (Intelligent Backup Power)
- Optionally shows inverter details (if attached)
- Custom MDI icons for visual clarity
- Optional debug sensors for JSON dumps
- Fully local: no internet or cloud calls

---

## 🚨 Important Notes

- **Not a professional coder!**  
  This project is a weekend hack, not an enterprise product. Use it at your own risk.

- **Your FCSP must be accessible over the local network**, and you must know its IP address.

- The **Developer Key (`devkey`) is the same for all units**. It will be pre-filled during setup — don’t change it unless you *really* know what you're doing.

---

## 📦 Installation

### ✅ HACS (Recommended)

1. Go to **HACS > Integrations > Custom Repositories**  
2. Paste in: `https://github.com/Aminorjourney/fcsp-local-integration`  
3. Choose Category: **Integration**  
4. Install → Restart Home Assistant

### 📁 Manual

1. Copy the entire `fcsp_local/` folder into your Home Assistant `custom_components/` directory.  
2. Restart Home Assistant.  
3. Go to **Settings > Devices & Services > Add Integration**, search for **"Ford Charge Station Pro Local"**, and complete the setup.

---

## 🧠 Exposed Sensors

| Sensor Name        | Description                                  | Icon                        | Entity ID Prefix         |
|--------------------|----------------------------------------------|-----------------------------|-------------------------|
| `station_info`      | Basic charger metadata (serial, model, IP)   | `mdi:ev-plug-ccs1`          | `sensor.local_fcsp_`     |
| `status`            | Charge/discharge status (Idle, Charging…)   | `mdi:ev-station`            | `sensor.local_fcsp_`     |
| `inverter_info`     | Inverter info if attached                    | `mdi:home-import-outline`   | `sensor.local_fcsp_`     |
| `system_state`      | Raw inverter system state code               | `mdi:transmission-tower`    | `sensor.local_fcsp_`     |
| JSON debug sensors  | Optional detailed JSON output for nerds      | `mdi:file-document`         | `sensor.local_fcsp_`     |

*Note: All sensors are prefixed with `local_fcsp_` in Home Assistant.*

---

## 🧪 Debug Mode

Enable **debug mode** during setup to expose extra sensors showing raw JSON data from the charger and inverter systems. Useful for troubleshooting or development.

---

## 🔄 Updating

- This integration uses a polling interval of **60 seconds** by default.
- To update, just pull the latest code and restart Home Assistant.

---

## 👩‍💻 Developer Info

This integration creates a `DeviceInfo` entry for:  
- The **Ford Charge Station Pro**, using the `mdi:ev-plug-ccs1` icon.  
- The **Inverter/Home Integration System** (if attached), using `mdi:home-import-outline`.

All sensors are associated with these devices, allowing clean grouping in the UI.

---

## 📜 License & Disclaimer

MIT License — see `LICENSE` file.

This integration is provided **as-is**, with no warranty or support. I am not responsible for any fried fuses, tripped breakers, or weird Home Assistant behavior.

---

## 🙏 Thanks

- Huge thanks to [Eric Pullen](https://github.com/ericpullen) for building `fcsp-api`  
- To the Home Assistant devs for making local integrations easy  
- To the EV community for pushing boundaries

---

## 📣 Contact

Built by **Nikki Gordon-Bloomfield** from [Transport Evolved](https://youtube.com/transportevolved) — not a professional coder, just someone who loves EVs, Home Assistant, and making stuff work better.

You can open issues or ideas via the [GitHub issues page](https://github.com/Aminorjourney/fcsp-local-integration/issues).

You can also find me on Mastodon: [@Aminorjourney@lgbtqia.space](https://lgbtqia.space/@Aminorjourney)
