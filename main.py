import json
import os
import pickle
from datetime import datetime
from itertools import count
from time import sleep
import gradio as gr
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv
import shutil

# Load environment variables
load_dotenv()
DEFAULT_USERNAME = os.getenv("DICE_USERNAME", "")
DEFAULT_PASSWORD = os.getenv("DICE_PASSWORD", "")

# Custom Chrome and Chromedriver paths (adjustable via env vars for flexibility)
CHROME_BINARY_PATH = os.getenv("CHROME_BINARY_PATH", os.path.expanduser("~/chrome-for-testing/chrome-linux64/chrome"))
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", os.path.expanduser("~/chrome-for-testing/chromedriver-linux64/chromedriver"))

# File paths
RESUME_DIR = "resumes"
HISTORY_FILE = "history.json"
SETTINGS_FILE = "settings.json"
RESUMES_FILE = "resumes.json"
COOKIES_FILE_BASE = "dice_cookies.pkl"

# Ensure directories and files exist
os.makedirs(RESUME_DIR, exist_ok=True)
for file in [HISTORY_FILE, SETTINGS_FILE, RESUMES_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f, indent=2)

# Cookie handling functions
def load_cookies(driver, username):
    cookie_file = f"{username}_{COOKIES_FILE_BASE}"
    if os.path.exists(cookie_file):
        try:
            with open(cookie_file, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
            return True
        except Exception as e:
            print(f"Failed to load cookies: {e}")
    return False

def save_cookies(driver, username):
    cookie_file = f"{username}_{COOKIES_FILE_BASE}"
    try:
        with open(cookie_file, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
    except Exception as e:
        print(f"Failed to save cookies: {e}")

def delete_cookies(username):
    cookie_file = f"{username}_{COOKIES_FILE_BASE}"
    if os.path.exists(cookie_file):
        os.remove(cookie_file)

# Main application function
def apply_to_dice(username, password, keywords, blacklist, resume_name, location, employment_type, cache_path="", wait_s=5):
    if not all([username, password, keywords, resume_name, location, employment_type]):
        return "Error: All fields except blacklist and cache path are required.", 0

    keywords = keywords.split()
    blacklist = blacklist.split() if blacklist else []
    output_log = []
    session_data = {
        "keywords": keywords,
        "blacklist": blacklist,
        "location": location,
        "employment_type": employment_type,
        "applied_jobs": [],
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    # Load and validate resume
    with open(RESUMES_FILE, "r") as f:
        resumes_data = json.load(f)
    resume_path = os.path.join(RESUME_DIR, resume_name)
    if not os.path.exists(resume_path) or resume_name not in resumes_data:
        return "Error: Selected resume not found.", 0

    # Load history
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
    user_history = history.get(username, {"all_applied_job_ids": [], "sessions": []})
    all_applied_job_ids = set(user_history["all_applied_job_ids"])

    # Build search URL
    search_query = "+".join(keywords)  # Dice uses + for spaces in query
    SEARCH_URL_WITHOUT_PAGE = (
        f"https://www.dice.com/jobs?q={search_query}&countryCode=US&radius=30&radiusUnit=mi"
        f"&page=%s&pageSize=100&filters.postedDate=ONE"
        f"&filters.employmentType={employment_type}&filters.easyApply=true"
        f"&location={location}&language=en"
    )

    # Initialize WebDriver
    options = Options()
    options.binary_location = CHROME_BINARY_PATH
    if cache_path:
        options.add_argument(f"user-data-dir={cache_path}")
    try:
        driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, options=options)
    except Exception as e:
        return f"Error: Failed to initialize Chrome driver: {e}", 0
    wait = WebDriverWait(driver, wait_s)

    # Login process
    driver.get("https://www.dice.com")
    if load_cookies(driver, username):
        driver.get("https://www.dice.com/dashboard")
        try:
            wait.until(EC.presence_of_element_located((By.ID, "email")))
            output_log.append("Cookies invalid, attempting manual login.")
        except TimeoutException:
            output_log.append("Logged in with cookies.")
    if "Logged in with cookies" not in "\n".join(output_log):
        driver.get("https://www.dice.com/dashboard/login")
        try:
            email_elem = wait.until(EC.presence_of_element_located((By.ID, "email")))
            email_elem.send_keys(username)
            password_elem = driver.find_element(By.ID, "password")
            password_elem.send_keys(password + Keys.RETURN)
            wait.until(EC.url_contains("dashboard"))
            output_log.append("Logged in successfully.")
            save_cookies(driver, username)
        except Exception as e:
            output_log.append(f"Login failed: {e}")
            driver.quit()
            return "\n".join(output_log), 0

    # Job application loop
    for page_number in count(1):
        search_url = SEARCH_URL_WITHOUT_PAGE % page_number
        driver.get(search_url)
        try:
            search_cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.search-card")))
        except TimeoutException:
            output_log.append(f"No more jobs found on page {page_number}.")
            break

        job_urls = []
        for card in search_cards:
            try:
                link = card.find_element(By.CSS_SELECTOR, "a.card-title-link")
                job_id = link.get_attribute("id")
                if job_id in all_applied_job_ids:
                    continue
                try:
                    ribbon = card.find_element(By.CSS_SELECTOR, "span.ribbon-inner")
                    if ribbon.text.lower() == "applied":
                        continue
                except NoSuchElementException:
                    pass
                job_urls.append((job_id, link.text, link.get_attribute("href")))
            except Exception as e:
                output_log.append(f"Error processing job card: {e}")

        if not job_urls:
            output_log.append(f"No new jobs to apply on page {page_number}.")
            break

        for job_id, job_text, job_url in job_urls:
            output_log.append(f"Processing: {job_text}")
            job_text_lower = job_text.lower()
            if not all(kw.lower() in job_text_lower for kw in keywords):
                output_log.append("Skipped: Missing keywords.")
                continue
            if any(bl.lower() in job_text_lower for bl in blacklist):
                output_log.append("Skipped: Blacklisted word found.")
                continue

            driver.get(job_url)
            try:
                apply_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "dhi-wc-apply-button")))
                wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "dhi-wc-apply-button"), "Apply Now"))
                driver.execute_script("arguments[0].shadowRoot.querySelector('button').click();", apply_container)

                resume_radio = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input#upload-resume-radio")))
                try:
                    daily_limit = driver.find_element(By.CSS_SELECTOR, "div[id^=googleCaptchaSection]")
                    if daily_limit.is_displayed():
                        output_log.append("Daily application limit reached.")
                        break
                except NoSuchElementException:
                    pass

                resume_radio.click()
                resume_file_input = driver.find_element(By.CSS_SELECTOR, "input#upload-resume-file-input")
                resume_file_input.send_keys(resume_path)
                apply_now_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button#submit-job-btn")))
                apply_now_button.click()
                wait.until(EC.staleness_of(apply_now_button))  # Ensure application submitted
                output_log.append(f"Applied to {job_text}.")
                all_applied_job_ids.add(job_id)
                session_data["applied_jobs"].append({
                    "job_id": job_id,
                    "job_title": job_text,
                    "application_date": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
            except Exception as e:
                output_log.append(f"Failed to apply to {job_text}: {e}")

    # Update history
    if session_data["applied_jobs"]:
        user_history["sessions"].append(session_data)
    user_history["all_applied_job_ids"] = list(all_applied_job_ids)
    history[username] = user_history
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    driver.quit()
    return "\n".join(output_log), len(session_data["applied_jobs"])

# History display function
def view_history(username, session_filter="All"):
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    except Exception as e:
        return f"Error loading history: {e}", ""
    user_history = history.get(username, {"all_applied_job_ids": [], "sessions": []})
    if not user_history["sessions"]:
        return "No application history found.", ""

    output = [f"Total Jobs Applied: {len(user_history['all_applied_job_ids'])}"]
    session_details = []
    for i, session in enumerate(user_history["sessions"]):
        session_label = f"Session {i+1} ({session['start_time']})"
        if session_filter == "All" or session_filter == session_label:
            session_str = (
                f"\n{session_label}:\n"
                f"  Keywords: {', '.join(session['keywords'])}\n"
                f"  Blacklist: {', '.join(session['blacklist']) if session['blacklist'] else 'None'}\n"
                f"  Location: {session['location']}\n"
                f"  Employment Type: {session['employment_type']}\n"
                f"  Applied Jobs ({len(session['applied_jobs'])}):"
            )
            for job in session["applied_jobs"]:
                session_str += f"\n    - {job['job_title']} (ID: {job['job_id']}, Date: {job['application_date']})"
            output.append(session_str)
            session_details.append(f"{session_label}: {len(session['applied_jobs'])} jobs")

    return "\n".join(output), "\n".join(session_details)

# Resume management functions
def load_resumes():
    try:
        with open(RESUMES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_resumes(resumes_data):
    with open(RESUMES_FILE, "w") as f:
        json.dump(resumes_data, f, indent=2)

def get_resume_list():
    return list(load_resumes().keys())

def upload_resume(resume_file):
    if not resume_file:
        return "Error: No file uploaded.", None
    resumes_data = load_resumes()
    original_name = os.path.basename(resume_file.name)
    current_name = original_name
    new_path = os.path.join(RESUME_DIR, current_name)
    if os.path.exists(new_path):
        base, ext = os.path.splitext(original_name)
        for i in count(1):
            current_name = f"{base}_{i}{ext}"
            new_path = os.path.join(RESUME_DIR, current_name)
            if not os.path.exists(new_path):
                break
    shutil.copy(resume_file.name, new_path)
    resumes_data[current_name] = {
        "original_name": original_name,
        "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notes": ""
    }
    save_resumes(resumes_data)
    return f"Uploaded: {current_name}", gr.Dataframe(
        value=[[k, v["original_name"], v["upload_date"], v["notes"]] for k, v in resumes_data.items()],
        headers=["Current Name", "Original Name", "Upload Date", "Notes"],
        interactive=False
    )

def rename_resume(current_name, new_name):
    if not current_name or not new_name:
        return "Error: Both current and new names are required.", None
    resumes_data = load_resumes()
    if current_name not in resumes_data:
        return "Error: Resume not found.", None
    old_path = os.path.join(RESUME_DIR, current_name)
    new_path = os.path.join(RESUME_DIR, new_name)
    if not os.path.exists(old_path):
        return "Error: Resume file missing.", None
    if os.path.exists(new_path):
        return "Error: New name already exists.", None
    os.rename(old_path, new_path)
    resumes_data[new_name] = resumes_data.pop(current_name)
    save_resumes(resumes_data)
    return f"Renamed {current_name} to {new_name}", gr.Dataframe(
        value=[[k, v["original_name"], v["upload_date"], v["notes"]] for k, v in resumes_data.items()],
        headers=["Current Name", "Original Name", "Upload Date", "Notes"],
        interactive=False
    )

def delete_resume(resume_name):
    if not resume_name:
        return "Error: No resume selected.", None
    resumes_data = load_resumes()
    if resume_name not in resumes_data:
        return "Error: Resume not found.", None
    resume_path = os.path.join(RESUME_DIR, resume_name)
    if os.path.exists(resume_path):
        os.remove(resume_path)
    del resumes_data[resume_name]
    save_resumes(resumes_data)
    return f"Deleted {resume_name}", gr.Dataframe(
        value=[[k, v["original_name"], v["upload_date"], v["notes"]] for k, v in resumes_data.items()],
        headers=["Current Name", "Original Name", "Upload Date", "Notes"],
        interactive=False
    )

def update_resume_notes(resume_name, notes):
    if not resume_name:
        return "Error: No resume selected.", None
    resumes_data = load_resumes()
    if resume_name not in resumes_data:
        return "Error: Resume not found.", None
    resumes_data[resume_name]["notes"] = notes.strip()
    save_resumes(resumes_data)
    return f"Updated notes for {resume_name}", gr.Dataframe(
        value=[[k, v["original_name"], v["upload_date"], v["notes"]] for k, v in resumes_data.items()],
        headers=["Current Name", "Original Name", "Upload Date", "Notes"],
        interactive=False
    )

# Settings management functions
def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
        return settings.get("default_settings", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_settings(keywords, blacklist, location, employment_type):
    settings = {
        "default_settings": {
            "keywords": keywords.strip(),
            "blacklist": blacklist.strip(),
            "location": location.strip(),
            "employment_type": employment_type
        }
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
    return "Settings saved successfully!"

def reset_settings():
    default_settings = {}
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"default_settings": default_settings}, f, indent=2)
    return "Settings reset to default.", default_settings

# Gradio Interface
with gr.Blocks(title="Auto Apply to Dice Jobs") as demo:
    gr.Markdown("# Auto Apply to Dice Jobs 🎯")
    gr.Markdown("Automate your job applications on Dice.com with ease!")

    with gr.Tabs():
        # Apply Tab
        with gr.TabItem("Apply"):
            settings = load_settings()
            with gr.Row():
                with gr.Column():
                    username_input = gr.Textbox(label="Dice Username", value=DEFAULT_USERNAME, placeholder="your@email.com")
                    password_input = gr.Textbox(label="Dice Password", type="password", value=DEFAULT_PASSWORD)
                    keywords_input = gr.Textbox(label="Keywords", value=settings.get("keywords", ""), placeholder="e.g., python developer")
                    blacklist_input = gr.Textbox(label="Blacklist (optional)", value=settings.get("blacklist", ""), placeholder="e.g., senior intern")
                    location_input = gr.Textbox(label="Location", value=settings.get("location", ""), placeholder="e.g., Remote")
                    employment_type = gr.Dropdown(
                        label="Employment Type",
                        choices=["FULL_TIME", "PART_TIME", "CONTRACTS", "THIRD_PARTY"],
                        value=settings.get("employment_type", "FULL_TIME")
                    )
                    resume_dropdown = gr.Dropdown(label="Select Resume", choices=get_resume_list(), interactive=True)
                    cache_input = gr.Textbox(label="Cache Path (optional)", placeholder="/path/to/cache")
                    wait_input = gr.Slider(1, 15, value=5, step=1, label="Wait Time (seconds)")
                    submit_btn = gr.Button("Start Applying")

                with gr.Column():
                    output_log = gr.Textbox(label="Application Log", lines=15, interactive=False)
                    applied_count = gr.Textbox(label="Jobs Applied This Session", interactive=False)

            def refresh_resumes():
                return gr.update(choices=get_resume_list())

            resume_dropdown.change(refresh_resumes, outputs=resume_dropdown)
            submit_btn.click(
                fn=apply_to_dice,
                inputs=[username_input, password_input, keywords_input, blacklist_input, resume_dropdown,
                        location_input, employment_type, cache_input, wait_input],
                outputs=[output_log, applied_count]
            )

        # History Tab
        with gr.TabItem("History"):
            with gr.Row():
                with gr.Column():
                    history_username = gr.Textbox(label="Dice Username", value=DEFAULT_USERNAME)
                    session_filter = gr.Dropdown(label="Filter Sessions", choices=["All"], value="All")
                    history_btn = gr.Button("View History")

                with gr.Column():
                    history_output = gr.Textbox(label="Application History", lines=15, interactive=False)
                    session_summary = gr.Textbox(label="Session Summary", lines=5, interactive=False)

            def update_session_filter(username):
                with open(HISTORY_FILE, "r") as f:
                    history = json.load(f)
                sessions = history.get(username, {"sessions": []})["sessions"]
                choices = ["All"] + [f"Session {i+1} ({s['start_time']})" for i, s in enumerate(sessions)]
                return gr.update(choices=choices, value="All")

            history_username.change(update_session_filter, inputs=history_username, outputs=session_filter)
            history_btn.click(fn=view_history, inputs=[history_username, session_filter], outputs=[history_output, session_summary])

        # Resume Management Tab
        with gr.TabItem("Resume Management"):
            with gr.Row():
                with gr.Column():
                    resume_upload = gr.File(label="Upload New Resume", file_types=[".pdf", ".doc", ".docx"])
                    upload_btn = gr.Button("Upload")
                    resume_list = gr.Dropdown(label="Select Resume", choices=get_resume_list(), interactive=True)
                    new_name_input = gr.Textbox(label="New Resume Name", placeholder="e.g., resume_v2.pdf")
                    notes_input = gr.Textbox(label="Notes", placeholder="e.g., Tailored for tech roles")
                    rename_btn = gr.Button("Rename")
                    update_notes_btn = gr.Button("Update Notes")
                    delete_btn = gr.Button("Delete")

                with gr.Column():
                    resume_status = gr.Textbox(label="Status", interactive=False)
                    resume_table = gr.Dataframe(
                        value=[[k, v["original_name"], v["upload_date"], v["notes"]] for k, v in load_resumes().items()],
                        headers=["Current Name", "Original Name", "Upload Date", "Notes"],
                        interactive=False
                    )

            upload_btn.click(fn=upload_resume, inputs=resume_upload, outputs=[resume_status, resume_table])
            rename_btn.click(fn=rename_resume, inputs=[resume_list, new_name_input], outputs=[resume_status, resume_table])
            update_notes_btn.click(fn=update_resume_notes, inputs=[resume_list, notes_input], outputs=[resume_status, resume_table])
            delete_btn.click(fn=delete_resume, inputs=resume_list, outputs=[resume_status, resume_table])

        # Job Apply Settings Tab
        with gr.TabItem("Job Apply Settings"):
            with gr.Row():
                with gr.Column():
                    settings_keywords = gr.Textbox(label="Default Keywords", value=settings.get("keywords", ""), placeholder="e.g., python developer")
                    settings_blacklist = gr.Textbox(label="Default Blacklist", value=settings.get("blacklist", ""), placeholder="e.g., senior intern")
                    settings_location = gr.Textbox(label="Default Location", value=settings.get("location", ""), placeholder="e.g., Remote")
                    settings_employment = gr.Dropdown(
                        label="Default Employment Type",
                        choices=["FULL_TIME", "PART_TIME", "CONTRACTS", "THIRD_PARTY"],
                        value=settings.get("employment_type", "FULL_TIME")
                    )
                    save_settings_btn = gr.Button("Save Settings")
                    reset_settings_btn = gr.Button("Reset Settings")

                with gr.Column():
                    settings_status = gr.Textbox(label="Status", interactive=False)

            def reset_and_update():
                status, defaults = reset_settings()
                return (
                    status,
                    gr.update(value=defaults.get("keywords", "")),
                    gr.update(value=defaults.get("blacklist", "")),
                    gr.update(value=defaults.get("location", "")),
                    gr.update(value=defaults.get("employment_type", "FULL_TIME"))
                )

            save_settings_btn.click(
                fn=save_settings,
                inputs=[settings_keywords, settings_blacklist, settings_location, settings_employment],
                outputs=settings_status
            )
            reset_settings_btn.click(
                fn=reset_and_update,
                outputs=[settings_status, settings_keywords, settings_blacklist, settings_location, settings_employment]
            )

demo.launch(server_port=1877, share=True)
