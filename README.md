# Auto Apply to Dice Jobs with Gradio 🚀

Welcome to **Auto Apply to Dice Jobs**! This Python project automates job applications on [Dice.com](https://www.dice.com) for "Easy Apply" listings using Selenium and provides a user-friendly web interface with Gradio. Apply to jobs effortlessly and track your application history! 🎉

---

## Features ✨

- **Automated Job Applications** 🤖: Log in to Dice.com and apply to jobs with a single click.
- **Gradio Interface** 🌐: A web-based UI to input details and monitor progress.
- **Resume Storage** 📄: Upload and store resumes in a `resumes` folder.
- **History Tracking** 📜: Avoid re-applying to jobs with `history.json`.
- **Tabs** 📑: Separate tabs for applying and viewing history.
- **Secure Credentials** 🔒: Store Dice username and password in a `.env` file.

---

## Prerequisites 📋

Before you start, ensure you have the following:

- **Python 3.7+** 🐍: Installed and added to your PATH.
- **Google Chrome** 🌍: Required for Selenium WebDriver.
- **Git** 🗂️: To clone the repository.

---

## Setup Instructions 🛠️

### 1. Clone the Repository 📥
```bash
git clone https://github.com/yourusername/Auto-Apply-to-Dice-Gradio.git
cd Auto-Apply-to-Dice-Gradio

pip install gradio selenium webdriver_manager python-dotenv
