# Changelog

All notable changes to this project will be documented in this file.

## [v0.3.1] - 2025-08-16

### Changed

- **Refactoring, Simplifying Binary Sensor, Improving Reliability **
  The previous binary_sensor.py for power cut detection wasn't reliably working, so it's now been refactored to push most of the detection logic into coordinator.py, reducing code complexity in binary_sensor.py and (at least in testing) far more reliably detecting a power cut.  Since this is only important if you have a Home Integration System installed, it might not be a big deal for you - but it was for me ;) 
  
### Still In Progress / Known Issues

- **Standalone FCSP (no Home Integration System) setup**  
  There's still a massive bug with the config flow that can result in 'phantom' home integration systems appearing even if you don't have one attached to your charge station pro. Hopefully now I've squished the Binary sensor issues for Power Cut detection... I can start working on this ;)

### Installation Instructions 

- **Version 0.3.0 **
  Updating from v 0.3.0 should be possible from HACS or manual drag and drop (see installation instructions). 

- **Version 0.2.x or Older **  
  Updating from earlier versions may leave orphaned or renamed sensors in Home Assistant.  
  To resolve:
  1. Manually remove affected entities from the UI; or  
  2. Remove and re-add the integration via the UI (recommended, especially when using new config options).

## [v0.3.0] - 2025-08-04

### Added

- **User-configurable date stamps**  
  Last updated timestamps now display in a human-readable format. Users can select between 12-hour or 24-hour clocks via the integration config.

- **New binary sensor logic for power cut detection**  
  Previous versions failed to reliably populate this sensor due to vague polling logic. This version introduces more explicit handling and correct data sourcing.

- **Version reporting for Home Integration System**  
  Inverter firmware/software revision is now parsed from its hex string and displayed in `Major.Minor.Patch` format (e.g., `1.1.36`).  
  This version string appears in `Home Integration System > Info > Firmware`, while the original cleaned hex string remains in `Home Integration System > Raw Data > Firmware (Hex)`.

### Changed

- **Raw info.json reporting renamed**  
  Sensors for raw inverter and charger data now use the label `Raw Data` for clarity and consistency.

- **V2H attached flag renamed**  
  In `Charger Info`, the `Home Integration Attached` flag is now labeled `V2H Attached`.

### Fixed

- **Fallback status handling for older FCSP firmware**  
  Older FCSP builds use text-based inverter status rather than numerical codes, breaking compatibility with power cut and status sensors.  
  `coordinator.py` now includes a fallback to support both data formats. This improves compatibility with owners that receive FCSP replacements running outdated software awaiting OTA updates.

### Still In Progress / Known Issues

- **Standalone FCSP (no Home Integration System) setup**  
  Dummy values may still appear for Home Integration sensors on systems without an inverter attached.  
  Future updates will include logic to detect and suppress known placeholder values or restructure the setup flow accordingly.

### Installation Instructions

- **Sensor cleanup required after update**  
  Updating from earlier versions may leave orphaned or renamed sensors in Home Assistant.  
  To resolve:
  1. Manually remove affected entities from the UI; or  
  2. Remove and re-add the integration via the UI (recommended, especially when using new config options).


## [v0.2.4] - 2025-07-19

### Added
- **Power Cut Detection Binary Sensor (Home Integration System only):**  
  A new binary sensor detects grid power outages via the Home Integration System.  
  Reports `True`/`False` for power cut status, enabling automations such as graceful shutdowns when UPS notifications are absent.  
  Future updates will add features like V2G capabilities.

- **Cached Data Support for Faster Startup:**  
  Uses cached data on startup to avoid blocking Home Assistant while waiting for fresh data.  
  Greatly improves startup speed and robustness during network interruptions.

### Fixed
- **HACS Integration Bug:**  
  Fixed a critical bug causing HACS to fail loading the integration.  
  Stability has improved significantly; users are encouraged to report any issues.

---

*This is an early version (v0.2.4) — please test thoroughly and provide feedback!*

Nikki. x
