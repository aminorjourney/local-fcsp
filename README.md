# ⚡ Ford Charge Station Pro Local for Home Assistant (`local_fcsp`)

**Author:** Nikki Gordon-Bloomfield  
**Based on:** [Eric Pullen’s `fcsp-api`](https://github.com/ericpullen/fcsp-api)

---

## 🚘 What Is This?

A Home Assistant **custom integration** for your **Ford Charge Station Pro (FCSP)** — 100% local, no Internet required.

It wraps [Eric Pullen’s `fcsp-api`](https://github.com/ericpullen/fcsp-api) Python library to surface charger and inverter data as native Home Assistant sensors.  
Status, power flow, raw JSON, and inverter metrics — all formatted cleanly for your dashboard.

---

## 🆕 What's New in v0.2.4

- **Power Cut Detection**: Added a binary sensor to monitor grid outages (Home Integration only).
- **Cache Support**: Speeds up startup and improves offline resilience.
- **HACS Bug Fixes**: Fixed critical bugs for smoother installation and operation.
___


## 🛠️ Features

- 🔌 Detects vehicle connection & charging status  
- ⚡ Shows Intelligent Backup Power (IBP) state  
- 🏠 Displays inverter details if installed  
- 🕒 “Last Updated” sensor shows time since last data change (e.g., _“2 minutes ago”_)  
- 🧪 Optional debug sensors with cleaned JSON output  
- 📦 MDI icons and device-level grouping for clean dashboards
- ** NEW ** Integrated power cut sensor based on Integration Data **Requires Home Integration V2G System**

---

## 🚨 Requirements

- Your **FCSP must be reachable over your local network** (IP required)
- The **developer key** is currently universal and pre-filled
- Inverter sensors only appear if an inverter is connected
- This is **not an official Ford product** — use it at your own risk

---

## 📦 Installation

### ✅ HACS (Recommended)

1. Go to **HACS → Integrations → Custom Repositories**
2. Add: `https://github.com/aminorjourney/local-fcsp`
3. Set category to **Integration**
4. Click **Install**
5. Reboot Home Assistant

### 📁 Manual Installation

1. Copy the `fcsp_local/` folder into `config/custom_components/`
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for **“Ford Charge Station Pro Local”** and follow the setup wizard

---

## 🔍 Available Sensors

> 💡 Sensor names may vary slightly in Home Assistant, but are always prefixed with:  
> - `sensor.ford_charge_station_pro_...`  
> - `sensor.home_integration_system_...`

| Sensor Name             | Description                                          | Icon                       |
|-------------------------|------------------------------------------------------|----------------------------|
| **Info**                | Model, serial, firmware, IP address, etc.            | `mdi:information`          |
| **Status**              | Charger status (Idle, Charging, Powering Home, etc.) | `mdi:ev-station`           |
| **State**               | Inverter state (Off, Powering Home, etc.)            | `mdi:sine-wave`            |
| **Last Updated**        | How recently the data changed                        | `mdi:update`               |
| **Info Raw JSON**       | Cleaned raw JSON for charger/inverter                | `mdi:file-search-outline`  |
| **Network Info**        | IP, MAC, and connectivity data                       | `mdi:access-point-network` |
| **Device Summary**      | Aggregated FCSP hardware metadata                    | `mdi:information-outline`  |

---

## 🧪 Debug Mode

If enabled during setup:

- Adds “Raw JSON” sensors for charger, inverter, and system internals
- Great for troubleshooting or reverse-engineering
- Turn it off if you prefer a cleaner sensor list

---

## 🔄 Polling & Updates

- Default polling interval is **60 seconds**
- You can reduce it (30 seconds works fine), but excessive polling may cause unreliable FCSP responses.  
  _Ask me how I know._ 💀

To update:
- Pull the latest version from GitHub
- Restart Home Assistant

---

## 🧭 Future Development

This integration doesn't (yet) expose **all** the data that [`fcsp-api`](https://github.com/ericpullen/fcsp-api) makes available — and it’s currently **read-only**.  
But future functionality **may** include:

- Manual control (start/stop charging)
- Adjustable current limit
- More sensors and attributes
- Event-based automation triggers

> 🧑‍💻 **Want to help?**  
> PRs are welcome! If you're handy with Python or Home Assistant development, fork it and send some love.  
> Even issue reports or ideas are super helpful.

---

## ❓ FAQ

**🔋 Does this let me start or stop charging?**  
Nope — this is a **passive sensor-only integration** for now. Starting/stopping charging is something that you can do through Ford's official smartphone **FordPass** app, and the developers of **FordPass-HA** [SquidBytes] and [marq24] are working on develping this functionality through `fordpass-ha` (https://github.com/marq24/ha-fordpass)  (While (https://github.com/itchannel/fordpass-ha) is the original, (https://github.com/marq24/ha-fordpass)is the EV and PHEV specific fork offering EV owners the most comprehensive feature-set at this time. 

**⚡ Can I change the current limit?**  
No. The integration reads the **hardware current limit** as set inside the unit at install.  
You *can* set a software limit, but only through FordPass at this time.

**🔮 Will it eventually control those things?**  
Maybe! Contributions welcome. The `fcsp-api` library *can* support more, but the integration currently prioritizes safe read-only polling.

**💥 Will this break my FCSP?**  
Probably not — but **don’t hammer it with short polling intervals**.  
Too-frequent polling can cause the FCSP to act weirdly (e.g., display `CF` fault codes).  
We recommend a **minimum of 30 seconds** between updates to keep it stable.

---

## 👩‍💻 Developer Notes

- `DeviceInfo` is used to register both the **FCSP** and (optionally) the **Inverter**
- All sensors are grouped with their respective hardware
- Time formatting uses Home Assistant’s `dt` utilities
- Inverter firmware is often non-printable — converted into clean hex strings (e.g., `01 1A FF`)
- Null bytes, whitespace, and junk strings are scrubbed automatically
- Charger faults (starting with `CF`) are returned as-is in **Status**

---

## ⚠️ Disclaimer

> This is a personal, unofficial project.  
> It's unsupported, unpolished, and occasionally weird.  
> It may break. It may misbehave. It may invite you to play Global Thermonuclear War.  
> Use at your own risk — and please don’t sue me if your FCSP starts speaking Klingon.

---

## 🙏 Thanks

- ❤️ [Eric Pullen](https://github.com/ericpullen) for building `fcsp-api`
- ❤️ [SquidBytes] and [marq24] from (https://github.com/marq24/ha-fordpass) and (https://github.com/itchannel/fordpass-ha) for working on `fordpass-ha`
- 🙌 Home Assistant devs and community
- 🚗 EV owners making the world cleaner, greener, and just a little bit smarter

---

## 📣 Contact

Built by **Nikki Gordon-Bloomfield** from [Transport Evolved](https://youtube.com/transportevolved)

- GitHub: [Issues Page](https://github.com/Aminorjourney/fcsp-local-integration/issues)  
- Mastodon: [@Aminorjourney@lgbtqia.space](https://lgbtqia.space/@Aminorjourney)
