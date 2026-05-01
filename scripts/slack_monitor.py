import os
import requests
from slack_sdk import WebClient

client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

def send_to_github(file_data):
    url = "https://api.github.com/repos/ahmedullah378/ahmedullah378.github.io/dispatches"
    headers = {"Authorization": f"token {os.environ.get('GH_PAT')}"}
    payload = {
        "event_type": "new_photo",
        "client_payload": {
            "file_url": file_data['url_private'],
            "sender": file_data.get('user', 'Ahmed')
        }
    }
    requests.post(url, json=payload, headers=headers)

# Test run: checks latest message
response = client.conversations_history(channel="C0B1ERPAVGR")
for msg in response["messages"]:
    if "files" in msg:
        send_to_github(msg["files"][0])
        print("Signal sent to GitHub!")
        break
