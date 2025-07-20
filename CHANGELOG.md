# Changelog

All notable changes to this project will be documented in this file.

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
