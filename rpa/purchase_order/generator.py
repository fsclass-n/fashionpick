"""발주서(Excel / PDF) 생성기.

입력 po 딕셔너리 형식:
{po_no, created_at(str), template('standard'|'simple'), total_amount,
 store{name, manager, phone, address}, supplier{name, contact_name, phone, email, address},
 items[{order_no, product_name, option, quantity, wholesale_price, source_url}]}
"""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

KOREAN_FONT = "HYGothic-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))

COLUMNS = [("No", "no"), ("주문번호", "order_no"), ("상품명", "product_name"), ("옵션", "option"),
           ("수량", "quantity"), ("도매단가", "wholesale_price"), ("금액", "amount")]
WIDTHS = {"no": 6, "order_no": 22, "product_name": 40, "option": 18, "quantity": 8, "wholesale_price": 12, "amount": 14}
MONEY = {"wholesale_price", "amount"}


def _columns(po: dict) -> list[tuple[str, str]]:
    return [c for c in COLUMNS if not (po.get("template") == "simple" and c[1] == "order_no")]


def _rows(po: dict) -> list[dict]:
    return [{**item, "no": i, "amount": item["quantity"] * item["wholesale_price"]}
            for i, item in enumerate(po["items"], start=1)]


def _info(po: dict) -> list[list[str]]:
    store, supplier = po["store"], po["supplier"]
    return [
        ["발주번호", po["po_no"], "발주일시", po["created_at"]],
        ["수신(공급처)", supplier["name"], "발신(발주처)", store["name"]],
        ["담당자", supplier.get("contact_name", ""), "담당자", store.get("manager", "")],
        ["연락처", supplier.get("phone", ""), "연락처", store.get("phone", "")],
        ["이메일", supplier.get("email", ""), "주소", store.get("address", "")],
    ]


def build_excel(po: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "발주서"
    cols = _columns(po)
    thin = Side(style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols))
    ws["A1"] = "발 주 서 (PURCHASE ORDER)"
    ws["A1"].font = Font(size=18, bold=True)
    ws["A1"].alignment = Alignment(horizontal="center")

    info = _info(po)
    for r, row in enumerate(info, start=3):
        for col, value, bold in zip((1, 2, 4, 5), row, (True, False, True, False)):
            ws.cell(row=r, column=col, value=value).font = Font(bold=bold)

    header_row = 3 + len(info) + 1
    for c, (title, key) in enumerate(cols, start=1):
        cell = ws.cell(row=header_row, column=c, value=title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="111111")
        cell.alignment = Alignment(horizontal="center")
        cell.border = border
        ws.column_dimensions[cell.column_letter].width = WIDTHS[key]
    for r, row in enumerate(_rows(po), start=header_row + 1):
        for c, (_, key) in enumerate(cols, start=1):
            cell = ws.cell(row=r, column=c, value=row.get(key, ""))
            cell.border = border
            if key in MONEY:
                cell.number_format = "#,##0"
    total_row = header_row + len(po["items"]) + 1
    ws.cell(row=total_row, column=len(cols) - 1, value="합계").font = Font(bold=True)
    total = ws.cell(row=total_row, column=len(cols), value=po["total_amount"])
    total.font, total.number_format = Font(bold=True), "#,##0"

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_pdf(po: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm,
                            bottomMargin=15 * mm, title=f"발주서 {po['po_no']}")
    title = ParagraphStyle("title", fontName=KOREAN_FONT, fontSize=20, alignment=1, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=title, fontSize=9)
    body = ParagraphStyle("body", fontName=KOREAN_FONT, fontSize=9, leading=12)
    cols = _columns(po)

    info = Table([[Paragraph(str(v), body) for v in row] for row in _info(po)],
                 colWidths=[25 * mm, 65 * mm, 25 * mm, 65 * mm])
    info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F2F2")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F2F2F2")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    data = [[t for t, _ in cols]]
    for row in _rows(po):
        data.append([Paragraph(f"{row[k]:,}" if k in MONEY else str(row.get(k, "")), body) for _, k in cols])
    data.append([""] * (len(cols) - 2) + ["합계", f"{po['total_amount']:,}"])
    total_w = sum(WIDTHS[k] for _, k in cols)
    items = Table(data, colWidths=[WIDTHS[k] / total_w * 180 * mm for _, k in cols], repeatRows=1)
    items.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), KOREAN_FONT, 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -2), 0.4, colors.HexColor("#999999")),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    doc.build([Paragraph("발 주 서", title), Paragraph("PURCHASE ORDER", sub), Spacer(1, 6 * mm), info,
               Spacer(1, 6 * mm), items, Spacer(1, 8 * mm),
               Paragraph("위와 같이 발주하오니 납기 내 출고 부탁드립니다.", body)])
    return buf.getvalue()
