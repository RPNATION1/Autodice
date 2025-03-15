# Auto Apply to Dice Jobs with Gradio 🚀

Welcome to **Auto Apply to Dice Jobs**! This Python project automates job applications on [Dice.com](https://www.dice.com) for "Easy Apply" listings with Selenium and a robust Gradio web interface. Manage resumes with metadata, fine-tune job settings, and track applications—all on your local network! 🎉

---

## Features ✨

- **Automated Applications** 🤖: Applies to Dice.com "Easy Apply" jobs seamlessly.
- **Gradio Web UI** 🌐: Tabs for applying, history, resume management, and job settings.
- **Resume Management** 📄: Tracks resumes with metadata (name, date, notes) in `resumes.json`.
- **Cookie Persistence** 🍪: Reuses login sessions via `username_dice_cookies.pkl`.
- **Detailed History** 📜: Logs sessions with keywords and jobs in `history.json`.
- **Custom Search** 🔍: Filters by keywords, blacklist, location, and employment type.
- **Job Settings** ⚙️: Saves defaults in `settings.json`.
- **LAN Sharing** 🌍: Runs on port `1877` with `share=True`.

---

## How It Works 🛠️

**Selenium** powers a custom Chrome browser to log into Dice.com, search, and apply. **Gradio** hosts a web interface at `http://127.0.0.1:1877`, shareable on your LAN (e.g., `http://192.168.1.x:1877`). Cookies save login effort, `resumes.json` tracks resume details, and settings/history keep your job hunt organized! 😎

---

## Prerequisites 📋

- **Python 3.7+** 🐍: Check with `python --version`.
- **Git** 🗂️: To clone the repo.
- **Local Network** 🌐: Optional, for LAN sharing.

---

## Setup Instructions ⚙️

### 1. Clone the Repository 📥
```bash
git clone https://github.com/yourusername/Auto-Apply-to-Dice-Gradio.git
cd Auto-Apply-to-Dice-Gradio
