# Contributing to Ford Charge Station Pro Local (`local_fcsp`)

Thanks for your interest in contributing to `local_fcsp`! 🎉  
This is a custom Home Assistant integration designed to work *locally* with your Ford Charge Station Pro. The more eyes, ideas, and pull requests — the better!

---

## 👩‍💻 Ways to Contribute

- 🐛 **Bug Reports:** Found an issue? Open a [GitHub Issue](https://github.com/Aminorjourney/fcsp-local-integration/issues)
- 💡 **Feature Ideas:** Got something new in mind? Open a discussion in the Git. Know that it might take me (or anyone else) a while to respond. This is 100% a hobby project. 
- 🧼 **Refactoring:** Code cleanup and simplification is *very* welcome. If you can make it clearer, more maintainable, or more elegant — go for it!
- 📝 **Docs:** Typos, clearer wording, formatting fixes — all appreciated

---

## ⚙️ Local Development Setup

This integration follows standard Home Assistant custom component structure.

1. Clone the repository into your HA config:
    ```bash
    config/custom_components/local_fcsp/
    ```
2. Restart Home Assistant
3. Develop and test your changes in-place
4. Enable debug logging (optional, but helpful):
    ```yaml
    logger:
      default: info
      logs:
        custom_components.local_fcsp: debug
    ```

---

## ⚠️ Important: `fcsp_api` - at least the current iteration - is Synchronous

The underlying [fcsp-api](https://github.com/ericpullen/fcsp-api) library is **not async**, and attempts to force asynchronous behavior have previously led to very unstable results (timeouts, connection errors, random data loss, etc).

**Please don’t try to make it async without deep testing and discussion.**  
For now, all interaction happens safely inside a thread via `async_add_executor_job()`.

---

## ✅ Coding Guidelines

- Follow Home Assistant’s [Python style guide](https://developers.home-assistant.io/docs/development_guidelines/)
- Use `async_add_executor_job()` for all `fcsp` calls
- Comment generously (humor welcome, clarity essential)
- Prefer readability over cleverness
- Keep things modular and safe for threaded access
- Break large logic blocks into helper methods when possible

---

## 📋 Before Opening a PR

- ✅ Test your changes with real data or `hass.log`
- 🔍 Check for typos, formatting, and inline comments
- 🔧 Run `ruff` or `flake8` if you use linting tools
- 📝 Add a short description and reference any related issues
- 📸 Include screenshots or sensor data examples if it’s a UI/state change

---

## 🙅 Please Avoid

- Introducing breaking changes without discussion
- Excessive reformatting of unrelated code

---

## 🤝 Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/).  
Be kind, helpful, respectful — we’re here to make cool stuff together.

---

## 📣 Questions?

- Open an [issue](https://github.com/Aminorjourney/fcsp-local-integration/issues)
- Or ping [@Aminorjourney@lgbtqia.space](https://lgbtqia.space/@Aminorjourney) on Mastodon

Thanks for helping improve this integration — your contributions keep it charging ahead! 🚗⚡
