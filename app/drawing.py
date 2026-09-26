"""Load drawings (PDF or image) into a PIL image. The original file is never modified."""
import hashlib
import io
from dataclasses import dataclass, field

import pymupdf as fitz
from PIL import Image

RENDER_DPI = 200
API_MAX_EDGE = 2000          # long edge of the copy sent to Claude
API_MAX_BYTES = 4_500_000    # stay under the 5 MB per-image limit


@dataclass
class Drawing:
    filename: str
    sha256: str
    page: int
    page_count: int
    image: Image.Image  # full-resolution raster used for overlay/crops
    pdf_text: list = field(default_factory=list)  # exact text spans (vector PDFs only)


def load_drawing(filename: str, data: bytes, page: int = 0) -> Drawing:
    sha = hashlib.sha256(data).hexdigest()
    if filename.lower().endswith(".pdf"):
        doc = fitz.open(stream=data, filetype="pdf")
        page = max(0, min(page, doc.page_count - 1))
        pix = doc[page].get_pixmap(dpi=RENDER_DPI, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        count = doc.page_count
        from .perception import pdf_tokens
        text = pdf_tokens(doc[page], RENDER_DPI / 72)
    else:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        page, count, text = 0, 1, []
    return Drawing(filename, sha, page, count, img, text)


def api_image_bytes(img: Image.Image) -> tuple[bytes, str]:
    """Downscaled copy for the API. Returns (bytes, media_type)."""
    im = img.copy()
    im.thumbnail((API_MAX_EDGE, API_MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    if buf.tell() <= API_MAX_BYTES:
        return buf.getvalue(), "image/png"
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue(), "image/jpeg"


def to_pixels(box, img: Image.Image) -> tuple[int, int, int, int]:
    """Normalised 0-1000 BBox -> (x0, y0, x1, y1) pixels on img, clamped."""
    W, H = img.size
    x0 = max(0, min(W, round(box.x * W / 1000)))
    y0 = max(0, min(H, round(box.y * H / 1000)))
    x1 = max(0, min(W, round((box.x + box.width) * W / 1000)))
    y1 = max(0, min(H, round((box.y + box.height) * H / 1000)))
    return x0, y0, max(x1, x0 + 1), max(y1, y0 + 1)
