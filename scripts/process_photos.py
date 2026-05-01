import cv2, numpy as np, img2pdf, os, requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def cleanup(img_bytes):
    # Load image from bytes
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: return None

    # 1. Convert to Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Rescale for better OCR/Readability (DPI increase)
    # This doubles the resolution to help sharpen tiny text
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # 3. Denoising (Removes the 'grainy' look from phone cameras)
    denoised = cv2.medianBlur(gray, 3)

    # 4. Advanced Thresholding (Gaussian gives smoother edges than Mean)
    # This creates a crisp black-and-white look
    processed = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 15, 12
    )

    # 5. Sharpening the 'Ink'
    # This makes the letters slightly bolder and easier to see
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)

    _, buffer = cv2.imencode(".jpg", processed, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return buffer.tobytes()

def run():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    client = WebClient(token=token)
    
    response = client.conversations_history(channel=channel_id, limit=10)
    messages = response.get("messages", [])
    
    target_msg = None
    for m in messages:
        if "files" in m and "bot_id" not in m:
            reactions = m.get('reactions', [])
            has_check = any(r['name'] == 'white_check_mark' for r in reactions)
            if not has_check:
                target_msg = m
                break
    
    if not target_msg:
        print("No new documents found.")
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
        
        client.files_upload_v2(
            channel=channel_id,
            file=file_path,
            title=file_name,
            initial_comment=f"✅ **{file_name}** Sharpness Enhanced!\n📄 Total Pages: **{len(pdf_pages)}**"
        )

        try:
            client.reactions_add(channel=channel_id, name="white_check_mark", timestamp=target_msg["ts"])
        except SlackApiError:
            pass

if __name__ == "__main__":
    run()
            client.reactions_add(
                channel=channel_id,
                name="white_check_mark",
                timestamp=target_msg["ts"]
            )
        except SlackApiError as e:
            print(f"Reaction failed (check permissions): {e.response['error']}")

if __name__ == "__main__":
    run()
