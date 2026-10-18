from collections.abc import Sequence
from io import BytesIO

import segno
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

GRIDS: dict[int, tuple[int, int]] = {
    1: (1, 1),
    4: (2, 2),
    6: (2, 3),
    12: (3, 4),
    20: (4, 5),
    24: (4, 6),
    35: (5, 7),
}

MARGIN = 28.0
FOOTER_FONT = 7
CODE_FONT = "Courier-Bold"
LABEL_FONT = "Helvetica"


def _ascii(text: str) -> str:
    return text.encode("latin-1", "ignore").decode("latin-1").strip()


def _draw_qr(pdf: canvas.Canvas, data: str, x: float, y: float, size: float) -> None:
    matrix = segno.make(data, error="m", micro=False).matrix
    modules = len(matrix)
    step = size / modules
    pdf.setFillColorRGB(0, 0, 0)
    for row_index, row in enumerate(matrix):
        top = y + size - row_index * step
        column = 0
        while column < modules:
            if not row[column]:
                column += 1
                continue
            start = column
            while column < modules and row[column]:
                column += 1
            pdf.rect(
                x + start * step,
                top - step - 0.15,
                (column - start) * step,
                step + 0.3,
                stroke=0,
                fill=1,
            )


def _fit_font(font: str, text: str, width: float, maximum: float) -> float:
    return min(maximum, width * 0.94 / (stringWidth(text, font, 1) or 1))


def build_pdf(entries: Sequence[tuple[str, int, str]], per_page: int) -> bytes:
    columns, rows = GRIDS[per_page]
    page_width, page_height = A4
    cell_width = (page_width - 2 * MARGIN) / columns
    cell_height = (page_height - 2 * MARGIN) / rows
    pages = max(1, -(-len(entries) // per_page))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle("QR codes")

    for index, (code, coins, label) in enumerate(entries):
        slot = index % per_page
        if slot == 0 and index > 0:
            pdf.showPage()
        column, row = slot % columns, slot // columns
        left = MARGIN + column * cell_width
        bottom = page_height - MARGIN - (row + 1) * cell_height

        pdf.setStrokeColorRGB(0.7, 0.7, 0.7)
        pdf.setLineWidth(0.5)
        pdf.setDash(2, 3)
        pdf.rect(left, bottom, cell_width, cell_height, stroke=1, fill=0)
        pdf.setDash()

        padding = min(cell_width, cell_height) * 0.07
        text_height = min(cell_height * 0.24, 110)
        qr_size = min(cell_width - 2 * padding, cell_height - text_height - 2 * padding)
        qr_x = left + (cell_width - qr_size) / 2
        _draw_qr(pdf, code, qr_x, bottom + text_height + padding / 2, qr_size)

        pdf.setFillColorRGB(0, 0, 0)
        code_size = _fit_font(CODE_FONT, code, cell_width - 2 * padding, 24)
        pdf.setFont(CODE_FONT, code_size)
        pdf.drawCentredString(left + cell_width / 2, bottom + text_height * 0.55, code)

        caption = f"{coins} coins"
        safe_label = _ascii(label)
        if safe_label:
            caption = f"{caption}  |  {safe_label}"
        caption_size = _fit_font(LABEL_FONT, caption, cell_width - 2 * padding, code_size * 0.9)
        pdf.setFont(LABEL_FONT, caption_size)
        pdf.setFillColorRGB(0.25, 0.25, 0.25)
        pdf.drawCentredString(left + cell_width / 2, bottom + text_height * 0.2, caption)

        if slot == per_page - 1 or index == len(entries) - 1:
            pdf.setFont(LABEL_FONT, FOOTER_FONT)
            pdf.setFillColorRGB(0.5, 0.5, 0.5)
            pdf.drawCentredString(page_width / 2, 12, f"Page {index // per_page + 1} of {pages}")

    pdf.save()
    return buffer.getvalue()
