import cv2, numpy as np, img2pdf, os, requests, datetime
from slack_sdk import WebClient

def cleanup(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cleaned = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY, 11, 11)
    _, buffer = cv2.imencode(".jpg", cleaned)
    return buffer.tobytes()

def run():
    token = os.getenv("SLACK_BOT_TOKEN")
    url_env = os.getenv("FILE_URL")
    channel_id = os.getenv("CHANNEL_ID")
    client = WebClient(token=token)
    pdf_pages = []

    # 1. Handle Trigger Type
    if not url_env:
        response = client.conversations_history(channel=channel_id, limit=5)
        for msg in response["messages"]:
            if "files" in msg:
                urls = [f['url_private'] for f in msg['files'] if f['filetype'] in ['jpg', 'png', 'jpeg']]
                break
    else:
        urls = url_env.split(",")

    # 2. Process Images
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {token}'})
    for url in urls:
        r = session.get(url.strip())
        if r.status_code == 200:
            processed = cleanup(r.content)
            if processed: pdf_pages.append(processed)

    if pdf_pages:
        # 3. Create Unique Serial Name
        os.makedirs("Scans", exist_ok=True)
        count = len([f for f in os.listdir("Scans") if f.endswith('.pdf')]) + 1
        file_name = f"Document_{count:03d}.pdf" # Result: Document_001.pdf
        file_path = os.path.join("Scans", file_name)

        with open(file_path, "wb") as f:
            f.write(img2pdf.convert(pdf_pages))

        # 4. SEND BACK TO SLACK
        print(f"Uploading {file_name} back to Slack...")
        client.files_upload_v2(
            channel=channel_id,
            file=file_path,
            title=file_name,
            initial_comment="✅ Here is the final scanned PDF!"
        )

if __name__ == "__main__":
    run()
