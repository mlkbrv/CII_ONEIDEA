"""
Checks of the printable QR sheet builder (app/services/qr_pdf.py).

Run from the project root:
    python -m tests.test_qr_pdf

No database needed. Covers: every supported grid produces the right number
of pages, and every QR on a 20-per-page sheet decodes back to its code.
"""
import re
import secrets
import sys

from app.services.qr_pdf import GRIDS, build_pdf

CODES = [f"PB-{secrets.token_hex(8).upper()}" for _ in range(45)]


def page_count(data: bytes) -> int:
    return len(re.findall(rb"/Type /Page\b", data))


def check_page_counts() -> list[tuple[str, bool]]:
    results = []
    for per_page in GRIDS:
        data = build_pdf([(code, 50, "SKU-1") for code in CODES], per_page)
        expected = -(-len(CODES) // per_page)
        results.append((f"{per_page} per page -> {expected} pages", page_count(data) == expected))
    return results


def check_decodes() -> list[tuple[str, bool]]:
    try:
        import cv2
        import numpy as np
        import pymupdf
    except ImportError:
        return []

    document = pymupdf.open(stream=build_pdf([(code, 50, "SKU-1") for code in CODES[:20]], 20), filetype="pdf")
    width, height = document[0].rect.width, document[0].rect.height
    margin, columns, rows = 28.0, 4, 5
    cell_w, cell_h = (width - 2 * margin) / columns, (height - 2 * margin) / rows
    decoded = []
    for slot in range(20):
        column, row = slot % columns, slot // columns
        clip = pymupdf.Rect(
            margin + column * cell_w,
            margin + row * cell_h,
            margin + (column + 1) * cell_w,
            margin + (row + 1) * cell_h,
        )
        png = document[0].get_pixmap(dpi=150, clip=clip).tobytes("png")
        image = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
        value, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
        decoded.append(value)
    return [("all 20 QR codes decode to their code", decoded == CODES[:20])]


def main() -> int:
    results = check_page_counts() + check_decodes()
    for name, ok in results:
        print(("PASS" if ok else "FAIL"), name)
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
