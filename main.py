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
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import shutil

# Load environment variables
load_dotenv()
DEFAULT_USERNAME = os.getenv("DICE_USERNAME", "")
DEFAULT_PASSWORD = os.getenv("DICE_PASSWORD", "")

# Custom Chrome and Chromedriver paths
CHROME_BINARY_PATH = os.path.expanduser("~/chrome-for-testing/chrome-linux64/chrome")
CHROMEDRIVER_PATH = os.path.expanduser("~/chrome-for-testing/chromedriver-linux64/chromedriver")

# File paths
RESUME_DIR = "resumes"
HISTORY_FILE = "history.json"
COOKIES_FILE_BASE = "dice_cookies.pkl"

# Ensure directories and files exist
if not os.path.exists(RESUME_DIR):
    os.makedirs(RESUME_DIR)
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w") as f:
        json.dump({}, f)

# Cookie handling functions
def load_cookies(driver, username):
    cookie_file = f"{username}_{COOKIES_FILE_BASE}"
    if os.path.exists(cookie_file):
        with open(cookie_file, "rb") as f:
            cookies = pickle.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
        return True
    return False

def save_cookies(driver, username):
    cookie_file = f"{username}_{COOKIES_FILE_BASE}"
    with open(cookie_file, "wb") as f:
        pickle.dump(driver.get_cookies(), f)

def delete_cookies(username):
    cookie_file = f"{username}_{COOKIES_FILE_BASE}"
    if os.path.exists(cookie_file):
        os.remove(cookie_file)

# Main application function
def apply_to_dice(username, password, keywords, blacklist, resume_file, location, employment_type, cache_path="", wait_s=5):
    keywords = keywords.split()
    blacklist = blacklist.split() if blacklist else []
    output_log = []

    # Handle resume file
    if not resume_file:
        return "Error: Please upload a resume file.", ""
    resume_path = os.path.join(RESUME_DIR, os.path.basename(resume_file.name))
    shutil.copy(resume_file.name, resume_path)

    # Load history
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
    user_history = history.get(username, {"all_applied_job_ids": [], "sessions": []})
    all_applied_job_ids = set(user_history["all_applied_job_ids"])

    # Build search URL with additional parameters
    SEARCH_URL_WITHOUT_PAGE = (
        f"https://www.dice.com/jobs?q={' '.join(keywords)}&countryCode=US&radius=30&radiusUnit=mi"
        f"&page=%s&pageSize=100&filters.postedDate=ONE"
        f"&filters.employmentType={employment_type}&filters.easyApply=true"
        f"&location={location}&language=en"
    )

    # Initialize WebDriver
    options = Options()
    options.binary_location = CHROME_BINARY_PATH
    if cache_path:
        options.add_argument(f"user-data-dir={cache_path}")
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, options=options)
    wait = WebDriverWait(driver, wait_s)

    # Cookie-based login
    driver.get("https://www.dice.com")
    if load_cookies(driver, username):
        driver.get("https://www.dice.com/dashboard")
        try:
            wait.until(EC.presence_of_element_located((By.ID, "email")))  # If this appears, cookies failed
            output_log.append("Cookies invalid, logging in manually.")
        except:
            output_log.append("Logged in with cookies.")
    else:
        driver.get("https://www.dice.com/dashboard/login")
        try:
            elem = wait.until(EC.presence_of_element_located((By.ID, "email")))
            elem.send_keys(f"{username}\t{password}{Keys.RETURN}")
            output_log.append("Logged in successfully.")
            save_cookies(driver, username)
        except Exception as e:
            output_log.append(f"Login failed: {str(e)}")
            driver.quit()
            return "\n".join(output_log), ""

    # New session data
    session_data = {
        "keywords": keywords,
        "blacklist": blacklist,
        "location": location,
        "employment_type": employment_type,
        "applied_jobs": [],
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    # Iterate through job pages
    for page_number in count(1):
        search_url = SEARCH_URL_WITHOUT_PAGE % page_number
        driver.get(search_url)
        try:
            search_cards = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.search-card"))
            )
        except Exception as e:
            output_log.append(f"No jobs found on page {page_number}: {str(e)}.")
            break

        job_urls = []
        for card in search_cards:
            link = card.find_element_by_css_selector("a.card-title-link")
            job_id = link.get_attribute("id")
            if job_id in all_applied_job_ids:
                continue
            try:
                ribbon = card.find_element_by_css_selector("span.ribbon-inner")
                if ribbon.text == "applied":
                    continue
            except:
                pass
            job_urls.append((job_id, link.text, link.get_attribute("href")))

        for job_id, job_text, job_url in job_urls:
            output_log.append(f"Processing: {job_text}")
            if not all(kw.lower() in job_text.lower() for kw in keywords):
                output_log.append("Skipped: Missing keywords.")
                continue
            if any(kw.lower() in job_text.lower() for kw in blacklist):
                output_log.append("Skipped: Blacklisted word found.")
                continue

            driver.get(job_url)
            try:
                apply_container = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "dhi-wc-apply-button"))
                )
                wait.until(
                    EC.text_to_be_present_in_element(
                        (By.CSS_SELECTOR, "dhi-wc-apply-button"), "Apply Now"
                    )
                )
                driver.execute_script(
                    "arguments[0].shadowRoot.querySelector('button').click();",
                    apply_container,
                )

                resume_radio = wait.until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "input#upload-resume-radio"))
                )
                daily_limit = driver.find_element_by_css_selector("div[id^=googleCaptchaSection]")
                if daily_limit.is_displayed():
                    output_log.append("Daily limit reached. Stopping.")
                    break

                apply_now_button = driver.find_element_by_css_selector("button#submit-job-btn")
                resume_radio.click()
                resume_file_input = driver.find_element_by_css_selector("input#upload-resume-file-input")
                resume_file_input.send_keys(resume_path)

                is_captcha_on = driver.find_element_by_css_selector('input[name="isGoogleCaptchaOn"]')
                driver.execute_script("arguments[0].setAttribute('value','false')", is_captcha_on)
                apply_now_button.click()
                output_log.append(f"Applied to {job_text}.")
                all_applied_job_ids.add(job_id)
                session_data["applied_jobs"].append({
                    "job_id": job_id,
                    "job_title": job_text,
                    "application_date": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
            except Exception as e:
                output_log.append(f"Failed to apply to {job_text}: {str(e)}")

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
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
    user_history = history.get(username, {"all_applied_job_ids": [], "sessions": []})
    if not user_history["sessions"]:
        return "No history found.", ""

    output = [f"Total Jobs Applied: {len(user_history['all_applied_job_ids'])}"]
    session_details = []
    for i, session in enumerate(user_history["sessions"]):
        if session_filter == "All" or session_filter == f"Session {i+1}":
            session_str = (
                f"\nSession {i+1} ({session['start_time']}):\n"
                f"  Keywords: {', '.join(session['keywords'])}\n"
                f"  Blacklist: {', '.join(session['blacklist']) if session['blacklist'] else 'None'}\n"
                f"  Location: {session['location']}\n"
                f"  Employment Type: {session['employment_type']}\n"
                f"  Applied Jobs ({len(session['applied_jobs'])}):"
            )
            for job in session["applied_jobs"]:
                session_str += f"\n    - {job['job_title']} (ID: {job['job_id']}, Date: {job['application_date']})"
            output.append(session_str)
            session_details.append(f"Session {i+1}: {len(session['applied_jobs'])} jobs")
    
    return "\n".join(output), "\n".join(session_details)

# Gradio Interface
with gr.Blocks(title="Auto Apply to Dice Jobs") as demo:
    gr.Markdown("# Auto Apply to Dice Jobs 🎯")
    gr.Markdown("Automate your job applications on Dice.com with advanced features!")

    with gr.Tabs():
        # Apply Tab
        with gr.TabItem("Apply"):
            with gr.Row():
                with gr.Column():
                    username_input = gr.Textbox(label="Dice Username", value=DEFAULT_USERNAME)
                    password_input = gr.Textbox(label="Dice Password", type="password", value=DEFAULT_PASSWORD)
                    keywords_input = gr.Textbox(label="Keywords", placeholder="e.g., software engineer python")
                    blacklist_input = gr.Textbox(label="Blacklist (optional)", placeholder="e.g., senior manager")
                    location_input = gr.Textbox(label="Location", placeholder="e.g., New York, NY")
                    employment_type = gr.Dropdown(
                        label="Employment Type", 
                        choices=["FULL_TIME", "PART_TIME", "CONTRACTS", "THIRD_PARTY"], 
                        value="FULL_TIME"
                    )
                    resume_input = gr.File(label="Upload Resume (PDF)")
                    cache_input = gr.Textbox(label="Cache Path (optional)", placeholder="e.g., /path/to/cache")
                    wait_input = gr.Slider(1, 10, value=5, label="Wait Time (seconds)")
                    submit_btn = gr.Button("Start Applying")
                
                with gr.Column():
                    output_log = gr.Textbox(label="Application Log", lines=15, interactive=False)
                    applied_count = gr.Textbox(label="Jobs Applied This Session", interactive=False)

            submit_btn.click(
                fn=apply_to_dice,
                inputs=[username_input, password_input, keywords_input, blacklist_input, resume_input, 
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
                return gr.update(choices=["All"] + [f"Session {i+1}" for i in range(len(sessions))])
            
            history_username.change(update_session_filter, inputs=history_username, outputs=session_filter)
            history_btn.click(
                fn=view_history,
                inputs=[history_username, session_filter],
                outputs=[history_output, session_summary]
            )

# Launch on port 1877 with LAN sharing
demo.launch(server_port=1877, share=True)
