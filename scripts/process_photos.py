import cv2, numpy as np, img2pdf, os, requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def cleanup(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Enhancement for fine text
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.medianBlur(gray, 3)
    processed = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 12)
    _, buffer = cv2.imencode(".jpg", processed, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return buffer.tobytes()

def run():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    client = WebClient(token=token)
    try:
        res = client.conversations_history(channel=channel_id, limit=10)
        messages = res.get("messages", [])
    except Exception: return

    target_msg = None
    for m in messages:
        if "files" in m and "bot_id" not in m:
            reactions = m.get('reactions', [])
            if not any(r['name'] == 'white_check_mark' for r in reactions):
                target_msg = m
                break

    if not target_msg: return

    urls = [f['url_private'] for f in target_msg['files'] if f['mimetype'].startswith('image/')]
    pdf_pages = []
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {token}'})
    
    for url in urls:
        r = session.get(url)
        if r.status_code == 200:
            proc = cleanup(r.content)
            if proc: pdf_pages.append(proc)

    if pdf_pages:
        os.makedirs("Scans", exist_ok=True)
        count = len([f for f in os.listdir("Scans") if f.endswith('.pdf')]) + 1
        name = f"Document_{count:03d}.pdf"
        path = f"Scans/{name}"
        with open(path, "wb") as f:
            f.write(img2pdf.convert(pdf_pages))
        
        client.files_upload_v2(channel=channel_id, file=path, title=name, initial_comment=f"✅ **{name}** ready (Sharpness++)\n📄 Pages: {len(pdf_pages)}")
        try:
            client.reactions_add(channel=channel_id, name="white_check_mark", timestamp=target_msg["ts"])
        except Exception: pass

if __name__ == "__main__":
    run()    
