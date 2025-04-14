import requests

import time

def current_milli_time():
    return round(time.time() * 1000)

def lap_run(runner : int):
    session = requests.Session()
    data = session.get("https://goldfish-app-auqrj.ondigitalocean.app/csrf/")

    session.headers.update({"X-CSRFToken": data.cookies["csrftoken"]})
    data = session.post("https://goldfish-app-auqrj.ondigitalocean.app/new_entry/", data={"time": current_milli_time(), "runner": runner})

    return data.text