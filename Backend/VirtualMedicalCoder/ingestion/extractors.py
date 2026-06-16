"""
ingestion/extractors.py

The file-type routing controller.
Each function downloads the file from its cloud URL and extracts raw text.

Dependencies:
    pip install PyMuPDF pytesseract pillow openai-whisper requests

System dependencies:
    - Tesseract OCR:  sudo apt install tesseract-ocr
    - ffmpeg (for Whisper audio): sudo apt install ffmpeg
"""

import io
import logging
import tempfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Download file from cloud URL
# ─────────────────────────────────────────────────────────────────────────────

def fetch_file_from_url(url: str) -> bytes:
    """
    Downloads the file at the given URL and returns its raw bytes.
    Raises an exception if the download fails or the file is too large.
    """
    MAX_FILE_SIZE_MB = 50
    MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download file from cloud: {e}")

    # Stream the download and enforce the size limit
    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > MAX_BYTES:
            raise RuntimeError(f"File exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB.")
        chunks.append(chunk)

    return b"".join(chunks)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2a: PDF extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from a PDF using PyMuPDF (fitz).

    PyMuPDF is very fast — it reads the PDF's embedded text layer directly.
    If a page has no embedded text (i.e. it's a scanned image inside a PDF),
    PyMuPDF will return an empty string for that page. In that case,
    we fall back to OCR on those pages.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF not installed. Run: pip install PyMuPDF")

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise RuntimeError(f"Could not open PDF: {e}")

    pages_text = []
    scanned_pages = []

    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()

        if text:
            # Page has real embedded text
            pages_text.append(f"--- Page {page_num + 1} ---\n{text}")
        else:
            # Page is likely a scanned image — mark it for OCR fallback
            scanned_pages.append((page_num, page))

    # OCR fallback for scanned pages
    if scanned_pages:
        logger.info(f"PDF has {len(scanned_pages)} scanned page(s) — running OCR on them.")
        for page_num, page in scanned_pages:
            # Render the page as a high-resolution image
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            ocr_text = _ocr_image_bytes(img_bytes)
            pages_text.append(f"--- Page {page_num + 1} (OCR) ---\n{ocr_text}")

    doc.close()
    return "\n\n".join(pages_text)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2b: Image extraction (OCR)
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_image(file_bytes: bytes) -> str:
    """
    Runs Tesseract OCR on an image and returns the extracted text.
    Tesseract must be installed on the system.
    """
    return _ocr_image_bytes(file_bytes)


def _ocr_image_bytes(image_bytes: bytes) -> str:
    """
    Internal helper: runs Tesseract OCR on raw image bytes.
    Used both for standalone images and for scanned PDF pages.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise RuntimeError("pytesseract and Pillow not installed. Run: pip install pytesseract pillow")

    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise RuntimeError(f"Could not open image: {e}")

    # PSM 6 = assume a single uniform block of text — best for medical documents
    config = "--psm 6 --oem 3"
    text = pytesseract.image_to_string(image, config=config)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Step 2c: Audio extraction (Speech-to-Text via Whisper)
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_audio(file_bytes: bytes) -> str:
    """
    Transcribes audio using OpenAI Whisper (local model).
    Whisper runs entirely on your server — no API call needed.
    Requires ffmpeg to be installed on the system.
    """
    try:
        import whisper
    except ImportError:
        raise RuntimeError("openai-whisper not installed. Run: pip install openai-whisper")

    # Write audio bytes to a temp file because Whisper needs a file path
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # "base" model is a good balance of speed and accuracy for FYP
        # Use "medium" or "large" for better accuracy in production
        model = whisper.load_model("base")
        result = model.transcribe(tmp_path, language="en")
        return result["text"].strip()
    except Exception as e:
        raise RuntimeError(f"Whisper transcription failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)  # Clean up temp file


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Main router — decides which extractor to call
# ─────────────────────────────────────────────────────────────────────────────

def route_and_extract(file_url: str, file_type: str) -> str:
    """
    Main entry point.
    1. Downloads the file from cloud storage.
    2. Routes to the correct extractor based on file_type.
    3. Returns the raw extracted text.

    file_type must be one of: "pdf", "image", "audio"
    """
    logger.info(f"Fetching file from cloud: {file_url}")
    file_bytes = fetch_file_from_url(file_url)

    logger.info(f"Routing to extractor for file type: {file_type}")

    if file_type == "pdf":
        return extract_text_from_pdf(file_bytes)

    elif file_type == "image":
        return extract_text_from_image(file_bytes)

    elif file_type == "audio":
        return extract_text_from_audio(file_bytes)

    else:
        raise ValueError(f"Unknown file type: {file_type}. Must be 'pdf', 'image', or 'audio'.")