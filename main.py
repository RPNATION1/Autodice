import json
import os
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

# Load environment variables from .env
load_dotenv()
DEFAULT_USERNAME = os.getenv("DICE_USERNAME", "")
DEFAULT_PASSWORD = os.getenv("DICE_PASSWORD", "")

# Ensure resumes folder exists
RESUME_DIR = "resumes"
if not os.path.exists(RESUME_DIR):
    os.makedirs(RESUME_DIR)

# History file for tracking applied jobs
HISTORY_FILE = "history.json"
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w") as f:
        json.dump({}, f)

# Function to handle job application logic
def apply_to_dice(username, password, keywords, blacklist, resume_file, cache_path="", wait_s=5):
    keywords = keywords.split()
    blacklist = blacklist.split() if blacklist else []
    output_log = []

    # Handle resume file
    if not resume_file:
        return "Error: Please upload a resume file."
    resume_path = os.path.join(RESUME_DIR, os.path.basename(resume_file.name))
    shutil.copy(resume_file.name, resume_path)  # Save uploaded resume to resumes folder

    # Load history
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
    user_history = history.get(username, [])

    # Build search URL
    SEARCH_URL_WITHOUT_PAGE = f"https://www.dice.com/jobs?q={' '.join(keywords)}&countryCode=US&radius=30&radiusUnit=mi&page=%s&pageSize=100&filters.postedDate=ONE&filters.employmentType=THIRD_PARTY&filters.easyApply=true&language=en"

    # Initialize WebDriver
    options = Options()
    if cache_path:
        options.add_argument(f"user-data-dir={cache_path}")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    wait = WebDriverWait(driver, wait_s)

    # Log in
    driver.get("https://www.dice.com/dashboard/login")
    try:
        elem = wait.until(EC.presence_of_element_located((By.ID, "email")))
        elem.send_keys(f"{username}\t{password}{Keys.RETURN}")
        output_log.append("Logged in successfully.")
    except Exception as e:
        output_log.append(f"Login skipped or failed: {str(e)}. Continuing.")

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
            if job_id in user_history:
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
                output_log.append("Skipped: Missing keywords in job title.")
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
                    output_log.append("Daily application limit reached. Stopping.")
                    driver.quit()
                    break

                apply_now_button = driver.find_element_by_css_selector("button#submit-job-btn")
                resume_radio.click()
                resume_file_input = driver.find_element_by_css_selector("input#upload-resume-file-input")
                resume_file_input.send_keys(resume_path)

                is_captcha_on = driver.find_element_by_css_selector('input[name="isGoogleCaptchaOn"]')
                driver.execute_script("arguments[0].setAttribute('value','false')", is_captcha_on)
                apply_now_button.click()
                output_log.append(f"Successfully applied to {job_text}.")
                user_history.append(job_id)
            except Exception as e:
                output_log.append(f"Failed to apply to {job_text}: {str(e)}")

            # Update history
            history[username] = user_history
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f)

    driver.quit()
    return "\n".join(output_log)

# Function to display application history
def view_history(username):
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
    user_history = history.get(username, [])
    if not user_history:
        return "No application history found for this user."
    return f"Applied to {len(user_history)} jobs:\n" + "\n".join(user_history)

# Gradio Interface with Tabs
with gr.Blocks(title="Auto Apply to Dice Jobs") as demo:
    gr.Markdown("# Auto Apply to Dice Jobs")
    gr.Markdown("Automate job applications on Dice.com with Easy Apply.")

    with gr.Tabs():
        with gr.TabItem("Apply"):
            with gr.Row():
                with gr.Column():
                    username_input = gr.Textbox(label="Dice Username", value=DEFAULT_USERNAME)
                    password_input = gr.Textbox(label="Dice Password", type="password", value=DEFAULT_PASSWORD)
                    keywords_input = gr.Textbox(label="Keywords", placeholder="e.g., software engineer python")
                    blacklist_input = gr.Textbox(label="Blacklist (optional)", placeholder="e.g., senior manager")
                    resume_input = gr.File(label="Upload Resume (PDF)")
                    cache_input = gr.Textbox(label="Cache Path (optional)", placeholder="e.g., /path/to/cache")
                    wait_input = gr.Slider(1, 10, value=5, label="Wait Time (seconds)")
                    submit_btn = gr.Button("Start Applying")
                with gr.Column():
                    output_log = gr.Textbox(label="Application Log", lines=20, interactive=False)
            submit_btn.click(
                fn=apply_to_dice,
                inputs=[username_input, password_input, keywords_input, blacklist_input, resume_input, cache_input, wait_input],
                outputs=output_log
            )

        with gr.TabItem("History"):
            with gr.Row():
                with gr.Column():
                    history_username = gr.Textbox(label="Dice Username", value=DEFAULT_USERNAME)
                    history_btn = gr.Button("View History")
                with gr.Column():
                    history_output = gr.Textbox(label="Application History", lines=20, interactive=False)
            history_btn.click(
                fn=view_history,
                inputs=history_username,
                outputs=history_output
            )

# Launch the interface
demo.launch()
