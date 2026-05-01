import cv2, numpy as np, img2pdf, os, requests

def cleanup(img_bytes):
    try:
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Apply the high-contrast "CamScanner" filter
        cleaned = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 11)
        _, buffer = cv2.imencode(".jpg", cleaned)
        return buffer.tobytes()
    except Exception as e:
        print(f"Cleanup error: {e}")
        return None

def run():
    # Get details from GitHub environment
    urls = os.getenv("FILE_URL", "").split(",")
    token = os.getenv("SLACK_BOT_TOKEN")
    pdf_pages = []

    # Create Scans folder
    os.makedirs("Scans", exist_ok=True)

    # Use a persistent session for better reliability
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {token}'})

    for url in urls:
        if not url.strip(): continue
        print(f"Downloading: {url}")
        r = session.get(url.strip())
        if r.status_code == 200:
            processed = cleanup(r.content)
            if processed: pdf_pages.append(processed)
        else:
            print(f"Download failed: {r.status_code}")

    if pdf_pages:
        output_path = "Scans/document.pdf"
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(pdf_pages))
        print(f"Success! {len(pdf_pages)} pages saved to {output_path}")
    else:
        print("Error: No images were successfully processed.")
        exit(1)

if __name__ == "__main__":
    run()
