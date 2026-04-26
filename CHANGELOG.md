# Changelog

All notable changes to this project will be documented in this file.

## [2026.4.0] - 2026-04-25

> ⚠️ **BREAKING CHANGES** — please read before updating.
> 
> - **Grid Status** (was: Power Cut) — states changed from `"On"`/`"Off"` to `"Power Cut"`/`"Grid Connected"`/`"Unknown"`
> - **Intelligent Backup Power** (was: HIS Status) — entity ID will change
> - **Station Password** (was: Passcode) — entity ID will change  
> - **Info and Raw Data sensors removed** — replaced by individual entities; automations referencing `"See Attributes"` or `"Click To View"` will break
> 
> A full HA restart is required after updating.

### Changed

- **Changed Versioning system to reflect HA's preferred versioning** 

  Home Assistant now prefers using a yyyy.m.patch system (year, month, release version) - and V0.4.0 has become 2026.4.0. 

- **Full sensor refactor — individual entities replace attribute-based sensors**  
  Home Assistant's UI no longer surfaces entity attributes in the More Info dialog for standard sensor entities. They now need their own entities in order to be viewable anywhere but Developer tools - which was the major reason for this rewrite. 

- **`DeviceInfo` is now a live `@property`**  
  Previously populated once at entity construction time (before coordinator data arrived), `device_info` is now a property that reads from live coordinator data. Serial number, firmware versions, catalogue number, and configuration URL all populate correctly after the first successful poll.

- **`DeviceInfo` populated from real API data**  
  Charge station device entry now includes model ID (`catalogNo`), serial number (`traceNo`), hardware version (`vHw`), system firmware (`vSystem`), and a `configuration_url` pointing to the device's local HTTPS interface. HIS device entry includes vendor, model, serial number, and firmware version from `inverter_info`.

- **Coordinator simplified to four endpoints**  
  `get_status()` and `get_device_summary()` are no longer called — both internally re-fetched endpoints the coordinator already calls, causing redundant network traffic every poll cycle. All data they provided is now derived directly from `charger_info`, `inverter_info`, `config_status`, and `network_info`.

- **WiFi management and Bluetooth pairing endpoints excluded by design**  
  These are POST requests that trigger side effects on the device (WiFi scan, BLE pairing mode). They will never be polled automatically. I've never got these to safely work, but if you have ideas? Get involved :) 

### Added

- New charge station sensors: Hardware Version, WiFi MAC Address, Bluetooth MAC Address, Passcode, Catalogue Number, Serial Number
- New HIS sensors: Inverter Model, Inverter Vendor
- Raw debug sensors renamed for clarity: Raw Charger Data, Raw Inverter Data, Raw Config Status, Raw Network Info

### Removed

- "Info" and "Raw Data" attribute-based sensors (replaced by individual entities above)
- `FCSP Device Summary` debug sensor (endpoint no longer polled)

### Installation notes

A full HA restart is required. Please note the following breaking changes that may affect existing automations:

- **`Info` and `Raw Data` sensors are gone** — automations referencing their states (`"See Attributes"` / `"Click To View"`) will need updating to reference the new individual entities.
- **Power Cut sensor renamed to Grid Status** — the entity ID will change. Automations checking for `"On"` or `"Off"` states need updating to `"Power Cut"` and `"Grid Connected"` respectively. 
- **HIS Status sensor renamed to Intelligent Backup Power** — update any automations referencing the old entity ID.
- **Passcode sensor renamed to Station Password** — update any automations or dashboard cards referencing the old entity ID.

---

## [v0.3.5] - 2026-04-23

### Fixed

- **Attributes no longer showing for FCSP or Home Integration System sensors**  
  The root cause was a duplicate coordinator: `sensor.py` was defining and instantiating its own `FCSPDataUpdateCoordinator` class, separate from the `FcspDataUpdateCoordinator` created by `__init__.py`. The sensor coordinator was never actually connected to the one doing data fetching, so attribute data simply wasn't flowing through. This version removes the duplicate coordinator entirely — sensors now use the single shared coordinator created at integration setup.

- **`coordinator.py` was only calling `get_status()`**  
  The coordinator in `coordinator.py` was fetching only a single endpoint (`get_status()`), which doesn't include `charger_info`, `network_info`, `config_status`, `device_summary`, or `inverter_info`. It now calls all endpoints individually, matching the full data model the sensors expect.

- **`Last Updated` sensor now correctly reflects coordinator update time**  
  Previously referenced a per-device timestamp dict that only existed on the now-removed duplicate coordinator. Now correctly reads `_last_update_dt` from the shared coordinator.

### Changed

- **Single coordinator architecture**  
  There is now one coordinator for the entire integration, created in `__init__.py` and shared across all platforms. `sensor.py` no longer creates its own.

### Installation Instructions

- **Version 0.3.x**  
  Updating from v0.3.x should be possible via HACS or manual drag-and-drop. A Home Assistant restart is required.

---

## [v0.3.2] - 2025-09-14

### Added

- **New Binary Sensor for Online Status**  
  Thanks to an update to the original API ([Eric Pullen’s `fcsp-api`](https://github.com/ericpullen/fcsp-api)), we can now poll for online status directly, with logging recording any errors during connections.

- **Logic to Eliminate 'Fake' Entity Data**  
  If an FCSP is connected to a Home Integration System, it will properly represent the system's unique information. In stand-alone installations without a Home Integration System, the FCSP produces 'dummy' data for the Home Integration System, which previously created 'fake' sensors. New logic now strips these out, ensuring the integration only creates sensors for real devices.

- **Refuse Collection Logic to Remove Pre-Existing 'Fake' Sensors**  
  Given the new logic, we also remove any sensors created with previous versions of this integration that *may not* exist. This includes removing the old Binary Sensor for Power Cut detection, replaced by the *new* Power Cut Detection sensor.

### Changed

- **Replaced Binary Power Cut Sensor with Quasi-Binary Sensor**  
  The Binary Sensor for power cut detection couldn't conditionally appear if a Home Integration System was attached. It’s now replaced with a quasi-binary sensor, allowing "create only if it exists" logic for Home Integration System sensors, and *should* prevent creation of sensors not paired with a real device.

### Installation Instructions

- **Version 0.3.x**  
  Updating from v0.3.x should be possible via HACS or manual drag-and-drop (see installation instructions).

- **Version 0.2.x or Older**  
  Updating from earlier versions may leave orphaned or renamed sensors in Home Assistant. To resolve:  
  1. Manually remove affected entities from the UI; or  
  2. Remove and re-add the integration via the UI (recommended, especially when using new config options).

---

## [v0.3.1] - 2025-08-16

### Changed

- **Refactoring, Simplifying Binary Sensor, Improving Reliability**  
  The previous `binary_sensor.py` for power cut detection wasn't reliable. Detection logic has been moved into `coordinator.py`, reducing complexity and improving detection reliability. Since this only applies if a Home Integration System is installed, standalone FCSP users may see no difference.

### Still In Progress / Known Issues

- **Standalone FCSP (no Home Integration System)**  
  Config flow bugs may still cause 'phantom' Home Integration Systems to appear even without an inverter. The Binary Sensor issues for power cut detection are now resolved, but further improvements may be made.

### Installation Instructions

- **Version 0.3.0**  
  Updating from v0.3.0 should be possible via HACS or manual drag-and-drop.

- **Version 0.2.x or Older**  
  Orphaned or renamed sensors may remain. To resolve:  
  1. Manually remove affected entities from the UI; or  
  2. Remove and re-add the integration via the UI.

---

## [v0.3.0] - 2025-08-04

### Added

- **User-Configurable Date Stamps**  
  Last updated timestamps now display in human-readable format. Users can select between 12-hour or 24-hour clocks via the integration config.

- **New Binary Sensor Logic for Power Cut Detection**  
  Previous versions failed to reliably populate this sensor. This version introduces explicit handling and correct data sourcing.

- **Version Reporting for Home Integration System**  
  Inverter firmware/software revisions are now parsed from hex and displayed in `Major.Minor.Patch` format (e.g., `1.1.36`).  
  Appears in `Home Integration System > Info > Firmware`, while the original hex string remains in `Home Integration System > Raw Data > Firmware (Hex)`.

### Changed

- **Raw Info Reporting Renamed**  
  Sensors for raw inverter and charger data now use the label `Raw Data` for clarity and consistency.

- **V2H Attached Flag Renamed**  
  In `Charger Info`, the `Home Integration Attached` flag is now labeled `V2H Attached`.

### Fixed

- **Fallback Status Handling for Older FCSP Firmware**  
  Older FCSP builds use text-based inverter status rather than numerical codes. `coordinator.py` now includes a fallback for both formats, improving compatibility.

### Still In Progress / Known Issues

- **Standalone FCSP Setup**  
  Dummy values may still appear for Home Integration sensors on systems without an inverter attached. Future updates will include logic to detect and suppress placeholder values or restructure the setup flow.

### Installation Instructions

- **Sensor Cleanup Required After Update**  
  Updating from earlier versions may leave orphaned or renamed sensors. To resolve:  
  1. Manually remove affected entities from the UI; or  
  2. Remove and re-add the integration via the UI.

---

## [v0.2.4] - 2025-07-19

### Added

- **Power Cut Detection Binary Sensor (Home Integration System Only)**  
  Detects grid power outages via the Home Integration System. Reports `True`/`False` for power cut status, enabling automations such as graceful shutdowns when UPS notifications are absent. Future updates will add V2G capabilities.

- **Cached Data Support for Faster Startup**  
  Uses cached data on startup to avoid blocking Home Assistant while waiting for fresh data, improving startup speed and network robustness.

### Fixed

- **HACS Integration Bug**  
  Fixed a critical bug causing HACS to fail loading the integration. Stability is now significantly improved.

---

*This is an early version (v0.2.4) — please test thoroughly and provide feedback!*

Nikki. x

