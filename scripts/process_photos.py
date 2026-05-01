import cv2, numpy as np, img2pdf, os, requests, csv
from datetime import datetime
from slack_sdk import WebClient

COST_PER_PAGE = 3  # 3 Taka per page

def cleanup(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cleaned = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY, 11, 11)
    _, buffer = cv2.imencode(".jpg", cleaned)
    return buffer.tobytes()

def update_billing(page_count):
    """Logs the scan data for the weekly/monthly table"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    month_str = now.strftime("%B %Y")
    total_price = page_count * COST_PER_PAGE
    
    file_exists = os.path.isfile("Scans/billing_log.csv")
    with open("Scans/billing_log.csv", "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Month", "Pages", "Rate", "Total (Taka)"])
        writer.writerow([date_str, month_str, page_count, COST_PER_PAGE, total_price])

def run():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    client = WebClient(token=token)
    
    response = client.conversations_history(channel=channel_id, limit=10)
    messages = response.get("messages", [])
    
    target_msg = next((m for m in messages if "files" in m and "bot_id" not in m), None)
    if not target_msg or any(r['name'] == 'white_check_mark' for r in target_msg.get('reactions', [])):
        return

    urls = [f['url_private'] for f in target_msg['files'] if f['mimetype'].startswith('image/')]
    
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
        count = len([f for f in os.listdir("Scans") if f.endswith('.pdf')]) + 1
        file_name = f"Document_{count:03d}.pdf"
        file_path = f"Scans/{file_name}"

        with open(file_path, "wb") as f:
            f.write(img2pdf.convert(pdf_pages))
        
        # Log the pages for the billing table
        update_billing(len(pdf_pages))
        
        client.files_upload_v2(
            channel=channel_id,
            file=file_path,
            title=file_name,
            initial_comment=f"✅ **{file_name}** ({len(pdf_pages)} pages) processed.\nCost: {len(pdf_pages) * COST_PER_PAGE} Taka."
        )

        client.reactions_add(channel=channel_id, name="white_check_mark", timestamp=target_msg["ts"])

if __name__ == "__main__":
    run()
