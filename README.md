# Auto Apply to Dice Jobs with Gradio 🚀

Welcome to **Auto Apply to Dice Jobs**! This Python project automates job applications on [Dice.com](https://www.dice.com) for "Easy Apply" listings using Selenium and a sleek Gradio web interface. Say goodbye to repetitive clicking and hello to streamlined job hunting! 🎉 With custom Chrome/Chromedriver paths, cookie persistence, and detailed history tracking, this tool is your job search sidekick.

---

## Features ✨

- **Automated Applications** 🤖: Applies to Dice.com "Easy Apply" jobs with your resume.
- **Gradio Web UI** 🌐: User-friendly interface with tabs for applying and viewing history.
- **Resume Storage** 📄: Uploads and saves resumes in a `resumes` folder.
- **Cookie Persistence** 🍪: Saves login sessions to skip repeated logins.
- **Detailed History** 📜: Tracks sessions with keywords, locations, and applied jobs in `history.json`.
- **Custom Search** 🔍: Filter by keywords, blacklist, location, and employment type.
- **LAN Sharing** 🌍: Runs on port `1877` with `share=True` for local network access.

---

## How It Works 🛠️

This tool uses **Selenium** with a custom Chrome browser to log into Dice.com, search for jobs based on your criteria, and apply with your resume. **Gradio** powers a web interface accessible at `http://127.0.0.1:1877` or via your local IP on your LAN (e.g., `http://192.168.1.x:1877`). Cookies keep you logged in, and `history.json` logs every session—keywords, applied jobs, and all—making job hunting smarter and faster! 😎

---

## Prerequisites 📋

Before you start, ensure you have:

- **Python 3.7+** 🐍: Installed and in your PATH (`python --version` to check).
- **Git** 🗂️: For cloning the repo.
- **Local Network** 🌐: Optional, for LAN sharing (same Wi-Fi/network required).

---

## Setup Instructions ⚙️

### 1. Clone the Repository 📥
Get the code:
```bash
git clone https://github.com/yourusername/Auto-Apply-to-Dice-Gradio.git
cd Auto-Apply-to-Dice-Gradio
