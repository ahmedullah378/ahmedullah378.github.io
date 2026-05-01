import os
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Credentials - These must be set in your GitHub Repo Secrets
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GH_PAT") 
REPO_OWNER = "ahmedullah378"
REPO_NAME = "ahmedullah378.github.io"

client = WebClient(token=SLACK_TOKEN)

def trigger_github_action(file_data):
    """Sends the trigger signal to GitHub Actions."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/dispatches"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "event_type": "process_image",
        "client_payload": {
            "file_url": file_data['url_private'],
            "channel": "pdf-cleaner",
            "sender": file_data.get('user', 'unknown')
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 204:
        print("Successfully triggered GitHub Action!")
    else:
        print(f"Failed to trigger GitHub: {response.status_code}")

def monitor_slack():
    """Checks the channel for new document uploads."""
    try:
        # Uses the channel ID from your workspace
        result = client.conversations_history(channel="C0B1ERPAVGR") 
        for message in result["messages"]:
            if "files" in message:
                for file in message["files"]:
                    # Only process common image formats
                    if file['filetype'] in ['jpg', 'jpeg', 'png']:
                        trigger_github_action(file)
                        return 
    except SlackApiError as e:
        print(f"Slack Error: {e}")

if __name__ == "__main__":
    monitor_slack()
  
