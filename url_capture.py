import os

def get_chrome_url_mac():
    script = 'tell application "Google Chrome" to return URL of active tab of front window'
    url = os.popen(f"osascript -e '{script}'").read().strip()
    return url

print(f"Current URL: {get_chrome_url_mac()}")
