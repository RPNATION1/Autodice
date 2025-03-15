# Auto Apply to Dice Jobs with Gradio 🚀

Welcome to **Auto Apply to Dice Jobs**! This Python project automates job applications on [Dice.com](https://www.dice.com) for "Easy Apply" listings using Selenium, wrapped in a sleek Gradio web interface. Whether you're hunting for your dream job or just want to save time, this tool applies to jobs for you and tracks your progress! 🎉

---

## Features ✨

- **Automated Job Applications** 🤖: Logs into Dice.com and applies to "Easy Apply" jobs effortlessly.
- **Gradio Web Interface** 🌐: A browser-based UI to input details, upload resumes, and monitor logs.
- **Resume Management** 📄: Upload and store resumes in a dedicated `resumes` folder.
- **Application History** 📜: Tracks applied jobs in `history.json` to prevent duplicates.
- **Tabbed Layout** 📑: Separate tabs for applying and viewing your application history.
- **Secure Credentials** 🔒: Stores your Dice username and password in a `.env` file.
- **Custom Port & LAN Sharing** 🌍: Runs on port `1877` with `share=True` for local network access.

---

## How It Works 🛠️

This tool uses **Selenium** to simulate a browser, logging into Dice.com, searching for jobs based on your keywords, and applying with your uploaded resume. **Gradio** provides a web interface, making it easy to use without touching the command line. With `share=True`, you can access it from any device on your local LAN (e.g., your phone or another computer) via `http://your-local-ip:1877`. Pretty cool, right? 😎

---

## Prerequisites 📋

Before diving in, ensure you have:

- **Python 3.7+** 🐍: Installed and in your PATH. Check with `python --version`.
- **Google Chrome** 🌍: Required for Selenium’s WebDriver to work.
- **Git** 🗂️: For cloning this repository.
- **Local Network** 🌐: Optional, for LAN sharing (ensure devices are on the same Wi-Fi/network).

---

## Setup Instructions ⚙️

### 1. Clone the Repository 📥
Grab the code from GitHub:
```bash
git clone https://github.com/yourusername/Auto-Apply-to-Dice-Gradio.git
cd Auto-Apply-to-Dice-Gradio
pip install gradio selenium webdriver_manager python-dotenv
