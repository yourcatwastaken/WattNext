from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from datetime import datetime, timedelta
import time, winsound, json, logging, os
from plyer import notification

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='outage.log', level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())
logging.getLogger('urllib3').setLevel(logging.ERROR)


def config():
    if not os.path.exists('config.json'):
        default_config = {
            "data": {
                "queue": "1.1",
                "use_sound": True,
                "alert_threshold_mins": 60,
                "notifs_during_outage": True,
                "outage_notifs_interval_mins": 60
            }
        }
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=4)
        logger.info('Created default config.json. Please edit it to your preferences.')

config()

options = Options()
options.add_argument('--headless=new')
driver = webdriver.Chrome(options=options)

def calculate_outage_times(time_range, current_time):
    start_time_str = time_range.split('-')[0]
    end_time_str = time_range.split('-')[1]
    today_start = datetime.strptime(start_time_str, '%H:%M')
    today_end = datetime.strptime(end_time_str, '%H:%M')
    outage_time = current_time.replace(hour=today_start.hour, minute=today_start.minute, second=0)
    end_time = current_time.replace(hour=today_end.hour, minute=today_end.minute, second=0)
    if end_time_str == '00:00':
        end_time += timedelta(days=1)
    mins_until_start = (outage_time - current_time).total_seconds() / 60
    mins_until_end = (end_time - current_time).total_seconds() / 60
    return outage_time, end_time, mins_until_start, mins_until_end, start_time_str, end_time_str

def alert_sound():
    for _ in range(5):
        winsound.Beep(1500, 500)

def send_notification(type, m_str, time_str):
    if type == 'soon':
        title = 'Power outage soon!'
        message = f'Outage starting in {int(m_str)} minutes (at {time_str}) !!!'
    elif type == 'active':
        title = 'Power is currently off!'
        message = f'Outage ends in {m_str} (at {time_str}) !!!'

    notification.notify(
        title = title,
        message = message,
        app_name = 'Outage alerts',
        app_icon = None,
        timeout = 10
    )
    return message

last_notif_time = datetime.min
last_known_end_time = ''
last_alerted_slot = ''

try:
    while True:
        try:
            current_time = datetime.now()
            logger.info(f"Checking schedule at: {current_time.strftime('%H:%M')}")

            with open('config.json') as file:
                config_data = json.load(file)
            user_queue = config_data['data'].get('queue') or '1.1'
            sound_enabled = config_data['data']['use_sound']
            alert_window = config_data['data'].get('alert_threshold_mins') or 60

            driver.get('https://off.energy.mk.ua/')
            wait = WebDriverWait(driver, timeout=15)

            target_index = None
            schedule_queue = wait.until(EC.visibility_of_all_elements_located((By.TAG_NAME, 'th')))
            for index, header in enumerate(schedule_queue):
                if user_queue and user_queue in header.text:
                    target_index = index
                    logger.info(f'Requested queue {user_queue} located at column index: {target_index}')
                    break

            if target_index is None:
                logger.error(f'Error: Could not find queue {user_queue} on the page.')
                time.sleep(60)
                continue

            rows = wait.until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'tabSchedule-row')))
            for row in rows:
                td = row.find_elements(By.TAG_NAME, 'td')
                if target_index is not None and len(td) > target_index:
                    time_range = td[0].text
                    out_ts, end_ts, m_start, m_end, start_str, end_str = calculate_outage_times(time_range, current_time)
                    status = td[target_index].get_attribute('class')
                    if 'item-probably' in status or 'item-off' in status:
                        if out_ts <= current_time < end_ts:
                            h, m = divmod(int(m_end), 60)
                            time_text = f'{h}h {m}m' if h > 0 else f'{m}m'
                            schedule_changed = (end_str != last_known_end_time)
                            active_notif_enabled = config_data['data'].get('notifs_during_outage', True)
                            interval = config_data['data'].get('outage_notifs_interval_mins') or 60
                            since_last = (current_time - last_notif_time).total_seconds() / 60
                            if schedule_changed or (active_notif_enabled and since_last >= interval):
                                msg = send_notification('active', time_text, end_str)
                                logger.info(f"{'SCHEDULE CHANGE!' if schedule_changed else ''} Sent notification: {msg}")
                                last_notif_time = current_time
                                last_known_end_time = end_str
                            break
                        elif 0 < m_start <= alert_window and time_range != last_alerted_slot:
                            last_alerted_slot = time_range
                            last_known_end_time = end_str
                            msg = send_notification('soon', m_start, start_str)
                            logger.info(f'Sent notification: {msg}')
                            if sound_enabled:
                                alert_sound()
                            break
            time.sleep(600)

        except Exception as E:
            logger.error(f'Error: {E}. Retrying in 60s...')
            time.sleep(60)

finally:
    logger.info('Closing browser...')
    driver.quit()