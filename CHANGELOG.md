# Changelog

All notable changes to this project will be documented in this file.

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

