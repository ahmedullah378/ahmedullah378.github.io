import cv2, numpy as np, img2pdf, os, requests
from slack_sdk import WebClient

def cleanup(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # High-quality document filter
    cleaned = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY, 11, 11)
    _, buffer = cv2.imencode(".jpg", cleaned)
    return buffer.tobytes()

def run():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    client = WebClient(token=token)
    
    # 1. Fetch Slack messages
    response = client.conversations_history(channel=channel_id, limit=10)
    messages = response.get("messages", [])
    
    # Find latest message with files that isn't from the bot and hasn't been processed
    target_msg = None
    for m in messages:
        if "files" in m and "bot_id" not in m:
            has_check = any(r['name'] == 'white_check_mark' for r in m.get('reactions', []))
            if not has_check:
                target_msg = m
                break
    
    if not target_msg:
        return

    urls = [f['url_private'] for f in target_msg['files'] if f['mimetype'].startswith('image/')]
    
    # 2. Process images
    pdf_pages = []
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {token}'})
    for url in urls:
        r = session.get(url)
        if r.status_code == 200:
            processed = cleanup(r.content)
            if processed: pdf_pages.append(processed)

    if pdf_pages:
        os.makedirs("Scans", exist_ok=True)
        # Unique serial naming: Document_001, Document_002, etc.
        count = len([f for f in os.listdir("Scans") if f.endswith('.pdf')]) + 1
        file_name = f"Document_{count:03d}.pdf"
        file_path = f"Scans/{file_name}"

        with open(file_path, "wb") as f:
            f.write(img2pdf.convert(pdf_pages))
        
        # 3. Upload back to Slack with the page count for your records
        client.files_upload_v2(
            channel=channel_id,
            file=file_path,
            title=file_name,
            initial_comment=f"✅ **{file_name}** is ready!\n📄 Total Pages: **{len(pdf_pages)}**"
        )

        # 4. Mark as processed
        client.reactions_add(
            channel=channel_id,
            name="white_check_mark",
            timestamp=target_msg["ts"]
        )

if __name__ == "__main__":
    run()
        client.files_upload_v2(
            channel=channel_id,
            file=file_path,
            title=file_name,
            initial_comment=f"✅ **{file_name}** ({len(pdf_pages)} pages) processed.\nCost: {len(pdf_pages) * COST_PER_PAGE} Taka."
        )

        client.reactions_add(channel=channel_id, name="white_check_mark", timestamp=target_msg["ts"])

if __name__ == "__main__":
    run()
