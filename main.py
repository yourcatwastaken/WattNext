from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from datetime import datetime, timedelta
import time
import winsound
import json

options = Options()
options.add_argument('--headless=new')
driver = webdriver.Chrome(options=options)

try:
    while True:
        try:
            now = datetime.now()
            print(f"Checking schedule at: {now.strftime('%H:%M')}")

            with open('config.json') as file:
                config_data = json.load(file)
            user_queue = config_data['data'].get('queue', '1.1')
            sound_enabled = config_data['data']['use_sound']
            alert_window = config_data['data'].get('alert_threshold_mins', 60)

            driver.get('https://off.energy.mk.ua/')
            wait = WebDriverWait(driver, timeout=15)

            target_index = None
            schedule_queue = wait.until(EC.visibility_of_all_elements_located((By.TAG_NAME, 'th')))
            for index, header in enumerate(schedule_queue):
                if user_queue in header.text:
                    target_index = index
                    print(f'Requested queue located at column index: {target_index}')
                    break

            if target_index is None:
                print(f'Error: Could not find queue {user_queue} on the page.')
                time.sleep(600)
                continue

            rows = wait.until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'tabSchedule-row')))
            for row in rows:
                td = row.find_elements(By.TAG_NAME, 'td')
                if target_index is not None and len(td) > target_index:
                    time_range = td[0].text
                    start_time_str = time_range.split('-')[0]
                    end_time_str = time_range.split('-')[1]
                    today_start = datetime.strptime(start_time_str, '%H:%M')
                    today_end = datetime.strptime(end_time_str, '%H:%M')
                    outage_time = now.replace(hour=today_start.hour, minute=today_start.minute, second=0)
                    end_time = now.replace(hour=today_end.hour, minute=today_end.minute, second=0)
                    if end_time_str == '00:00':
                        end_time += timedelta(days=1)

                    minutes_until_start = (outage_time - now).total_seconds() / 60
                    minutes_until_end = (end_time - now).total_seconds() / 60

                    status = td[target_index].get_attribute('class')
                    if 'item-probably' in status or 'item-off' in status:
                        if outage_time <= now < end_time:
                            h, m = divmod(int(minutes_until_end), 60)
                            time_text = f'{h}h {m}m' if h > 0 else f'{m}m'
                            print(f'!!! STATUS: Power is currently off. Ends in {time_text} (at {end_time_str}) !!!')
                            break
                        elif 0 < minutes_until_start <= alert_window:
                            print(f'!!! ALERT: Outage starting in {int(minutes_until_start)} minutes (at {start_time_str}) !!!')
                            if sound_enabled:
                                for i in range(5):
                                    winsound.Beep(1500, 500)
                            break
            time.sleep(600)

        except Exception as E:
            print(f'Error: {E}. Retrying in 60s...')
            time.sleep(60)

finally:
    print('Closing browser...')
    driver.quit()