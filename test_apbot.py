from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# --- Setup Chrome driver ---
chrome_options = Options()
chrome_options.add_experimental_option("detach", True)  # Keeps Chrome open until script ends
service = Service(r"F:\Chatbotproject\APbot\chromedriver-win64\chromedriver.exe") 
driver = webdriver.Chrome(service=service, options=chrome_options)

# --- Open APBot ---
driver.get("http://127.0.0.1:5000")  # Change to your APBot local or deployed URL
time.sleep(4)  # Let page load

buttons_text = [
    "server",
    "access issues",
    "reports & tracking",
    "inventory",
    "others",
    "AGM",
    "connectivity issues",
    "scanning issues"
]

for btn_text in buttons_text:
    try:
        # Wait for button to exist in DOM
        button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, f"//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{btn_text.lower()}')]")
            )
        )

        # Scroll button into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)

        # Wait until clickable and click
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(button))
        button.click()

        print(f"Clicked: {btn_text}")
        time.sleep(2)

    except Exception as e:
        print(f"Could not click '{btn_text}': {e}")