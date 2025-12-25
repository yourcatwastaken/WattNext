from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from datetime import datetime, timedelta
now = datetime.now()
current_time_string = now.strftime('%H:%M')
print(f'Current time: {current_time_string}')

user_queue = str(input('Enter your queue: '))

options = Options()
options.add_argument('--headless=new')
driver = webdriver.Chrome(options=options)
driver.get('https://off.energy.mk.ua/')

wait = WebDriverWait(driver, timeout=10)
schedule_queue = wait.until(EC.visibility_of_all_elements_located((By.TAG_NAME, 'th')))
for index, header in enumerate(schedule_queue):
    if user_queue in header.text:
        target_index = index
        print(f'Requested queue located at column index: {target_index}')
        break

TR = wait.until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'tabSchedule-row')))
for row in TR:
    td = row.find_elements(By.TAG_NAME, 'td')
    if target_index is not None and len(td) > target_index:
        time_range = td[0].text
        start_time_str = time_range.split('-')[0]
        today = datetime.strptime(start_time_str, '%H:%M')
        outage_time = now.replace(hour=today.hour, minute=today.minute, second=0)
        time_diff = outage_time - now
        remaining = time_diff.total_seconds() / 60


        if 0 < remaining <= 60:
            status_cell = td[target_index]
            status = status_cell.get_attribute('class')
            if 'item-probably' in status or 'item-off' in status:
                print(f'!!! ALERT: Outage starting in {int(remaining)} minutes (at {start_time_str}) !!!')
                break

driver.quit()