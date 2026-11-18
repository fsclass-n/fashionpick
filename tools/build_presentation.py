"""docs/presentation.md 를 패션 에디토리얼 스타일 PPTX 로 생성한다.

실행 (저장소 루트):
    uv pip install --python .venv/Scripts/python.exe -r tools/requirements.txt
    .venv/Scripts/python tools/build_presentation.py
출력: docs/fashionpick_발표자료.pptx  (발표자 스크립트는 슬라이드 노트에 포함)

서체는 발표 PC 호환을 위해 Georgia(영문 타이틀) + 맑은 고딕(본문)을 사용한다.
"""
import os
import sys
import tempfile
from pathlib import Path

import segno
from playwright.sync_api import sync_playwright
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.placeholder import render  # noqa: E402

ASSETS = ROOT / "docs" / "assets"
OUT = ROOT / "docs" / "fashionpick_발표자료.pptx"

INK, PAPER, WHITE = "111111", "F7F5F0", "FFFFFF"
DARK, CREAM = "0E0D0C", "F4EFE6"
MUTED, LINE, SOFT = "767676", "E3DFD6", "EFECE6"
ACCENT, ACCENT_L, BURGUNDY, CAMEL = "B4532A", "E07A4F", "6D2233", "C9A27E"
DISPLAY, SANS, MONO = "Georgia", "맑은 고딕", "Consolas"
TOTAL = 17

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


# ---------------------------------------------------------------- helpers
def rgb(hex_):
    return RGBColor.from_string(hex_)


def _font(run, size, color=INK, bold=False, italic=False, font=SANS, spacing=None):
    f = run.font
    f.size, f.bold, f.italic, f.name = Pt(size), bold, italic, font
    f.color.rgb = rgb(color)
    rpr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set("typeface", SANS if font in (DISPLAY, MONO) and tag == "a:ea" else font)
    if spacing is not None:
        rpr.set("spc", str(spacing))


def text(slide, x, y, w, h, content, size=14, color=INK, bold=False, italic=False, font=SANS, align="l",
         anchor="t", spacing=None, line=1.15, para_space=0):
    """content: str | list[str | list[tuple(text, overrides)]] — 줄 단위 리스트, 줄 안에 서식 조각 가능."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    lines = content if isinstance(content, list) else [content]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        p.line_spacing = line
        p.space_after = Pt(para_space)
        for piece in (ln if isinstance(ln, list) else [ln]):
            t, o = (piece, {}) if isinstance(piece, str) else piece
            r = p.add_run()
            r.text = t
            _font(r, o.get("size", size), o.get("color", color), o.get("bold", bold), o.get("italic", italic),
                  o.get("font", font), o.get("spacing", spacing))
    return tb


def box(slide, x, y, w, h, fill=WHITE, line=None, radius=0.06, shape=MSO_SHAPE.ROUNDED_RECTANGLE, line_w=0.75):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    if fill:
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(fill)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(line_w)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    return s


def rule(slide, x, y, w, color=INK, weight=1.0):
    s = slide.shapes.add_connector(1, Inches(x), Inches(y), Inches(x + w), Inches(y))
    s.line.color.rgb = rgb(color)
    s.line.width = Pt(weight)
    return s


def picture(slide, path, x, y, w=None, h=None, frame=True, crop_bottom=0.0):
    if frame:
        from PIL import Image
        iw, ih = Image.open(path).size
        ratio = ih * (1 - crop_bottom) / iw
        w = w or h / ratio
        h = h or w * ratio
        box(slide, x - 0.04, y - 0.04, w + 0.08, h + 0.08, fill=WHITE, line=LINE, radius=0.02)
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)
    if crop_bottom:
        pic.crop_bottom = crop_bottom
        pic.height = Emu(int(pic.width * (pic.image.size[1] * (1 - crop_bottom)) / pic.image.size[0]))
    return pic


def chip(slide, x, y, label, fill=ACCENT, color=WHITE, size=10, w=None):
    w = w or 0.22 + len(label) * size * 0.0125
    s = box(slide, x, y, w, 0.3, fill=fill, radius=0.5)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(0.06)
    tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    _font(r, size, color, bold=True)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return w


def bg(slide, color):
    box(slide, 0, 0, 13.333, 7.5, fill=color, radius=0, shape=MSO_SHAPE.RECTANGLE)


def header(slide, no, eyebrow, title, mine=False, dark=False):
    fg, sub = (CREAM, "9B978E") if dark else (INK, MUTED)
    text(slide, 0.6, 0.42, 8, 0.3, f"No.{no:02d}  —  {eyebrow}", size=10, color=sub, bold=True, spacing=300)
    text(slide, 0.6, 0.72, 10.5, 0.8, title, size=28, color=fg, bold=True)
    text(slide, 10.9, 0.38, 1.83, 0.5, [[(f"{no:02d}", {"size": 26}), (f" / {TOTAL}", {"size": 12, "color": sub})]],
         font=DISPLAY, italic=True, color=fg, align="r")
    if mine:
        chip(slide, 11.35, 0.95, "발표자 담당", w=1.38)
    line = "3A3733" if dark else LINE
    rule(slide, 0.6, 6.98, 12.13, color=line, weight=0.75)
    text(slide, 0.6, 7.05, 4, 0.3, [[("fashionpick", {"font": DISPLAY, "italic": True, "size": 11, "color": fg}),
                                      ("  ●", {"size": 7, "color": ACCENT})]])
    text(slide, 7.7, 7.07, 5.03, 0.3, "From trend to order.  ·  김모란", size=9, color=sub, align="r", font=DISPLAY, italic=True)


def notes(slide, script):
    slide.notes_slide.notes_text_frame.text = script.strip()


def bullets(slide, x, y, w, h, items, size=13, color=INK, gap=6, marker="—"):
    lines = []
    for it in items:
        if isinstance(it, tuple):
            head, rest = it
            lines.append([(f"{marker} ", {"color": ACCENT, "bold": True}), (head, {"bold": True}), (rest, {"color": "444444"})])
        else:
            lines.append([(f"{marker} ", {"color": ACCENT, "bold": True}), it])
    return text(slide, x, y, w, h, lines, size=size, color=color, line=1.2, para_space=gap)


def card(slide, x, y, w, h, fill=WHITE, line=LINE):
    return box(slide, x, y, w, h, fill=fill, line=line, radius=0.04)


def table(slide, x, y, w, rows, col_w, size=11, row_h=0.42, head_fill=INK):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tbl = shape.table
    tbl.first_row = True
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(head_fill if r == 0 else (WHITE if r % 2 else "FBFAF7"))
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            tf.paragraphs[0].text = ""
            run = tf.paragraphs[0].add_run()
            run.text = val
            _font(run, size if r else size - 1, WHITE if r == 0 else (INK if c == 0 else "3A3A3A"), bold=(r == 0 or c == 0))
    return shape


def arrow(slide, x, y, w=0.4, h=0.3, color=MUTED, down=False):
    s = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW if down else MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(color)
    s.line.fill.background()
    return s


# ---------------------------------------------------------------- assets
tmp = Path(tempfile.mkdtemp(prefix="fp-pptx-"))


def build_assets():
    looks = {"outer": ("아우터", "베이지"), "top": ("상의", "블랙"), "dress": ("원피스", "버건디"),
             "bag": ("가방", "네이비"), "shoes": ("슈즈", "브라운"), "pants": ("하의", "그레이")}
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 800, "height": 1000})
        for key, (cat, color) in looks.items():
            page.set_content(f'<html><body style="margin:0">{render(key.encode().hex()[:12], cat, color, cat)}</body></html>')
            page.locator("svg").screenshot(path=str(tmp / f"look-{key}.png"))
        b.close()
    for name, url in {"github": "https://github.com/fsclass-n/fashionpick", "prod": "https://fashionpick.onrender.com",
                      "api": "https://fashionpick-api.onrender.com/docs"}.items():
        segno.make(url, error="m").save(str(tmp / f"qr-{name}.png"), scale=12, border=2, dark="#111111", light="#ffffff")


def qr(slide, name, x, y, label, size=1.15, dark=False):
    box(slide, x - 0.08, y - 0.08, size + 0.16, size + 0.16, fill=WHITE, radius=0.08)
    slide.shapes.add_picture(str(tmp / f"qr-{name}.png"), Inches(x), Inches(y), Inches(size), Inches(size))
    text(slide, x - 0.2, y + size + 0.16, size + 0.4, 0.3, label, size=9, color=CREAM if dark else MUTED, align="c", bold=True, spacing=100)


A = lambda n: ASSETS / n  # noqa: E731
L = lambda n: tmp / f"look-{n}.png"  # noqa: E731


# ---------------------------------------------------------------- slides
def s01():
    s = prs.slides.add_slide(BLANK)
    bg(s, DARK)
    box(s, -2.2, -2.8, 6.6, 6.6, fill="221410", shape=MSO_SHAPE.OVAL)
    text(s, 0.7, 0.62, 6.5, 0.3, "K-DIGITAL 심화 SEMI-PROJECT  ·  3조  ·  4인 팀", size=10, color="9B978E", bold=True, spacing=300)
    text(s, 0.7, 1.35, 6.6, 1.3, [[("fashionpick", {}), ("●", {"size": 22, "color": ACCENT})]], size=68, color=CREAM, font=DISPLAY, italic=True)
    text(s, 0.7, 2.72, 6.5, 0.7, "From trend to order.", size=32, color=ACCENT_L, font=DISPLAY, italic=True)
    text(s, 0.7, 3.55, 6.45, 0.8, "RPA 기반 패션 트렌드 분석 · 도매 소싱 · 발주 자동화 플랫폼", size=15.5, color=CREAM)
    rule(s, 0.7, 4.55, 5.6, color="3A3733")
    text(s, 0.7, 4.75, 6.2, 1.4, [
        [("TEAM   ", {"size": 9, "color": "9B978E", "bold": True, "spacing": 200}), "박미금(조장) · 김모란 · 이오리 · 홍기흥"],
        [("SPEAKER   ", {"size": 9, "color": "9B978E", "bold": True, "spacing": 200}), ("김모란", {"bold": True}),
         ("  —  백엔드 · RPA 파이프라인 · 데이터 분석", {"color": "C9C4BA"})],
    ], size=14, color=CREAM, line=1.6)
    text(s, 0.7, 6.55, 6.5, 0.4, "github.com/fsclass-n/fashionpick   ·   fashionpick.onrender.com", size=10, color="9B978E")
    # lookbook collage
    picture(s, L("outer"), 7.25, 0.7, w=3.2, frame=False)
    picture(s, L("dress"), 10.6, 0.7, w=1.55, frame=False)
    picture(s, L("top"), 10.6, 2.75, w=1.55, frame=False)
    text(s, 7.25, 4.85, 3.2, 0.3, "FW 26 LOOKBOOK  ·  OUTERWEAR EDIT", size=8, color="9B978E", bold=True, spacing=200)
    qr(s, "github", 10.75, 5.15, "GITHUB", size=1.0, dark=True)
    qr(s, "prod", 12.0, 5.15, "LIVE", size=1.0, dark=True)
    notes(s, """안녕하세요, fashionpick 팀에서 백엔드와 RPA 파이프라인, 데이터 분석을 맡은 김모란입니다.
fashionpick은 패션 쇼핑몰 운영자가 매일 손으로 하던 세 가지 일, 트렌드 파악, 도매 상품 찾기, 발주서 작성을 자동화한 플랫폼입니다. 한 줄로 줄이면 "From trend to order", 트렌드에서 주문까지 사람 손을 덜 타게 만드는 서비스입니다.
오늘은 기능 소개보다는 왜 이렇게 설계했는지, 그리고 배포하면서 실제로 막혔던 문제를 어떻게 풀었는지를 중심으로 말씀드리겠습니다.""")


def s02():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 2, "WHY · 배경 및 문제 정의", "운영자의 하루는 반복 수작업의 연속입니다")
    steps = [("01", "Trend", "트렌드", "감과 SNS 눈팅에 의존\n근거 데이터 없음", L("top")),
             ("02", "Sourcing", "소싱", "도매 사이트를 키워드마다 반복 검색\n이미지 수동 저장", L("bag")),
             ("03", "Order", "발주", "주문마다 공급처별 발주서를\n엑셀로 직접 작성·발송", L("shoes"))]
    for i, (n, en, ko, desc, img) in enumerate(steps):
        x = 0.6 + i * 4.1
        card(s, x, 1.75, 3.85, 3.55)
        picture(s, img, x + 2.55, 1.95, w=1.1, frame=False)
        text(s, x + 0.3, 1.95, 2, 0.6, n, size=30, color=ACCENT, font=DISPLAY, italic=True)
        text(s, x + 0.3, 2.65, 2.5, 0.5, [[(en, {"font": DISPLAY, "italic": True, "size": 22}), (f"   {ko}", {"size": 13, "color": MUTED})]])
        text(s, x + 0.3, 3.45, 3.3, 1.0, desc, size=13, color="3A3A3A", line=1.3)
        chip(s, x + 0.3, 4.7, "수작업", fill="F3DDD3", color=ACCENT, w=0.85)
        if i < 2:
            arrow(s, x + 3.88, 3.4, w=0.2, h=0.25, color=ACCENT)
    box(s, 0.6, 5.55, 12.13, 1.15, fill=INK, radius=0.05)
    text(s, 0.95, 5.68, 11.5, 0.95, [
        [("문제의 본질   ", {"color": ACCENT_L, "bold": True}), ("같은 일을 매일 반복하고, 단계 사이 데이터가 끊겨 있음", {"color": CREAM})],
        [("목표   ", {"color": ACCENT_L, "bold": True}), ("세 단계를 ", {"color": CREAM}), ("하나의 데이터 파이프라인", {"color": CREAM, "bold": True}),
         ("으로 연결", {"color": CREAM})],
    ], size=15, line=1.5, anchor="m")
    notes(s, """소규모 쇼핑몰 운영자의 하루를 보면 세 가지 반복 작업이 있습니다.
첫째, 뭐가 뜨는지를 감으로 판단합니다. 둘째, 그 키워드로 도매 사이트를 하나씩 검색하고 이미지를 저장합니다. 셋째, 주문이 들어오면 공급처마다 발주서를 엑셀로 만들어 보냅니다.
저희가 주목한 건 이 세 작업이 서로 연결된 데이터인데도 매번 사람이 옮겨 적는다는 점이었습니다. 트렌드 키워드가 소싱 검색어가 되고, 소싱한 상품이 주문이 되고, 주문이 발주서가 됩니다. 그래서 이걸 하나의 파이프라인으로 잇는 것을 목표로 잡았습니다.""")


def s03():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 3, "WHAT · 핵심 가치 및 솔루션", "세 가지 수작업을 자동화합니다")
    cols = [("① 트렌드 수집·분석", "감 · SNS 확인", "60분마다 자동 수집\n급상승 키워드 자동 하이라이트", L("pants")),
            ("② 도매 소싱·상품 등록", "키워드별 반복 검색\n이미지 수동 저장", "상위 키워드로 180분마다 자동 수집\n판매가·마진·상품명 추천 → 원클릭 등록", L("outer")),
            ("③ 발주 자동화", "주문마다 엑셀 작성\n메일 발송", "주문 즉시 공급처별 발주서(Excel/PDF)\n이메일·웹훅 발송 · 실시간 알림", L("dress"))]
    for i, (title, before, after, img) in enumerate(cols):
        x = 0.6 + i * 4.1
        picture(s, img, x, 1.75, w=1.25, frame=False)
        text(s, x + 1.45, 1.95, 2.45, 0.9, title, size=16, bold=True, line=1.2)
        text(s, x, 3.42, 3.85, 0.3, "BEFORE", size=9, color=MUTED, bold=True, spacing=250)
        box(s, x, 3.7, 3.85, 0.95, fill=SOFT, radius=0.08)
        text(s, x + 0.2, 3.78, 3.5, 0.8, before, size=12, color="555555", anchor="m", line=1.25)
        text(s, x, 4.8, 3.85, 0.3, "AFTER · fashionpick", size=9, color=ACCENT, bold=True, spacing=250)
        box(s, x, 5.08, 3.85, 1.25, fill=INK, radius=0.08)
        text(s, x + 0.2, 5.15, 3.5, 1.1, after, size=12, color=CREAM, anchor="m", line=1.3)
    text(s, 0.6, 6.52, 12.1, 0.35, "※ 작업 시간 절감 수치는 실측값이 없어 '운영자가 직접 하던 단계 → 확인·승인 단계'로 표현 [확인 필요]", size=10, color=MUTED)
    notes(s, """그래서 fashionpick은 세 가지를 자동화합니다.
트렌드는 60분마다 수집해서 급상승 키워드를 바로 보여 주고, 소싱은 상위 키워드로 180분마다 도매 상품을 모아 판매가와 마진, 상품명까지 추천해서 버튼 하나로 등록하게 했습니다. 주문이 들어오면 공급처별 발주서가 즉시 만들어지고 발송까지 이어집니다.
정확한 시간 절감은 실측하지 못해서 숫자로 말씀드리진 않겠습니다. 대신 운영자가 직접 하던 단계가 "확인하고 승인하는 일"로 줄어든다는 점을 강조드리고 싶습니다.""")


def s04():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 4, "ARCHITECTURE · 전체 시스템 구성", "프런트 · 백엔드 분리 배포 아키텍처")
    # diagram
    for i, (t, sub) in enumerate([("React (Vite) · Tailwind v4", "Netlify — 스테이징"), ("React (Vite) · Tailwind v4", "Render Static — 프로덕션")]):
        x = 0.6 + i * 3.95
        card(s, x, 1.75, 3.75, 0.85)
        text(s, x + 0.2, 1.83, 3.4, 0.7, [[(t, {"bold": True})], [(sub, {"color": MUTED, "size": 11})]], size=13, anchor="m")
    text(s, 0.6, 2.68, 7.7, 0.3, "REST (JWT Bearer)   ·   WebSocket /ws?token=", size=10, color=MUTED, align="c", bold=True)
    arrow(s, 4.3, 2.95, w=0.3, h=0.3, down=True, color=ACCENT)
    box(s, 0.6, 3.3, 7.7, 1.55, fill=INK, radius=0.05)
    text(s, 0.85, 3.4, 7.2, 1.4, [
        [("FastAPI  ", {"bold": True, "size": 16}), ("Render Docker · fashionpick-api.onrender.com", {"color": "C9C4BA", "size": 11})],
        [("routers   ", {"color": ACCENT_L, "bold": True, "size": 10}), ("auth · shop · trends · catalog · orders · admin · realtime", {"size": 11})],
        [("services  ", {"color": ACCENT_L, "bold": True, "size": 10}), ("trends · catalog · ordering · rpa_jobs · realtime", {"size": 11})],
        [("RPA       ", {"color": ACCENT_L, "bold": True, "size": 10}), ("asyncio 스케줄러 → 워커 스레드 → rpa/* (Playwright · Requests)", {"size": 11})],
    ], color=CREAM, line=1.35, anchor="m")
    arrow(s, 4.3, 4.93, w=0.3, h=0.3, down=True, color=ACCENT)
    for i, (t, sub) in enumerate([("TiDB Cloud", "운영 DB · MySQL 호환 · TLS"), ("SQLite", "로컬 · 테스트"), ("외부 연동", "데이터랩 · 랭킹·도매 · SMTP · 웹훅")]):
        x = 0.6 + i * 2.6
        box(s, x, 5.3, 2.5, 1.0, fill=SOFT, radius=0.06)
        text(s, x + 0.15, 5.36, 2.2, 0.9, [[(t, {"bold": True})], [(sub, {"color": MUTED, "size": 10})]], size=13, anchor="m")
    # rationale
    text(s, 8.75, 1.75, 4, 0.3, "DESIGN DECISIONS", size=10, color=ACCENT, bold=True, spacing=300)
    bullets(s, 8.75, 2.15, 4.0, 4.6, [
        ("프런트·백엔드 완전 분리", "\n정적 SPA는 CDN, API는 Docker 컨테이너"),
        ("프런트 2곳 배포", "\nNetlify = 스테이징 / Render Static = 프로덕션"),
        ("RPA 엔진 위치", "\nAPI 프로세스 안의 스케줄러 + 워커 스레드\n(무료 티어 단일 인스턴스에 맞춤)"),
        ("실시간 이벤트 통합", "\nWebSocket 하나로 주문·발주·트렌드·RPA"),
    ], size=12, gap=10)
    notes(s, """전체 구조입니다. 프런트는 React 정적 사이트라 Netlify와 Render Static 두 곳에 올렸고, 하나는 스테이징, 하나는 프로덕션으로 썼습니다.
백엔드는 FastAPI를 Docker 컨테이너로 Render에 올렸습니다. 컨테이너를 고른 이유는 RPA 때문입니다. Playwright가 쓰는 Chromium을 이미지에 같이 넣어야 했거든요.
제가 설계한 부분은 RPA 엔진 위치입니다. 별도 워커 서버를 두면 좋지만 무료 티어는 인스턴스가 하나라서, API 프로세스 안에 asyncio 스케줄러를 두고 무거운 수집은 워커 스레드로 돌렸습니다. 이 트레이드오프는 마지막 회고에서 다시 말씀드리겠습니다.""")


def s05():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 5, "TECH STACK · 선정 이유", "유명해서가 아니라, 문제에 맞춰 골랐습니다")
    table(s, 0.6, 1.75, 12.13, [
        ["기술", "고른 이유", "비교한 대안"],
        ["Playwright", "자바스크립트로 렌더링되는 랭킹·도매 페이지 수집, 빌드 시 Chromium을 이미지에 포함", "Requests만으로는 동적 페이지 불가"],
        ["FastAPI", "비동기 + WebSocket 기본 지원, /docs 자동 API 문서", "Flask (WebSocket 별도 구성 필요)"],
        ["TiDB Cloud", "MySQL 호환 서버리스, 무료 티어, TLS 필수", "관리형 MySQL (비용)"],
        ["SQLite (로컬·테스트)", "같은 SQLAlchemy 코드로 DATABASE_URL만 바꿔 전환, 테스트마다 임시 DB", "테스트도 클라우드 DB (느리고 운영 데이터 오염 위험)"],
        ["Tailwind v4", "디자인 토큰(@theme)과 @utility로 공통 규칙 관리, 다크 모드", "CSS 모듈 (토큰 공유 번거로움)"],
        ["pandas / NumPy", "스냅샷 비교·집계를 간결하게 표현", "순수 파이썬 반복문"],
    ], [2.4, 6.13, 3.6], size=12, row_h=0.62)
    notes(s, """기술은 "이게 유명해서"가 아니라 문제에 맞춰 골랐습니다.
수집 대상 페이지가 자바스크립트로 그려지기 때문에 Playwright가 필요했고, 그게 Docker 배포로 이어졌습니다. FastAPI는 WebSocket을 기본으로 지원해서 실시간 알림을 같은 서버에서 처리할 수 있었습니다.
DB는 운영은 TiDB, 로컬과 테스트는 SQLite로 나눴습니다. 코드는 그대로 두고 접속 주소만 바꾸게 만들어서, pytest는 매번 임시 SQLite로 돌고 운영 데이터는 건드리지 않습니다. 이 결정을 왜 했는지는 트러블슈팅에서 실제 사례로 말씀드리겠습니다.""")


def s06():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 6, "CORE ① · RPA PIPELINE", "RPA 수집 파이프라인", mine=True)
    x = 0.6
    for name, mins in (("trend_collect", "60분"), ("product_sourcing", "180분"), ("po_dispatch", "30분")):
        w = 1.85
        box(s, x, 1.75, w, 0.62, fill=INK, radius=0.15)
        text(s, x, 1.78, w, 0.56, [[(name, {"font": MONO, "size": 10, "color": CREAM})], [(mins, {"bold": True, "size": 12, "color": ACCENT_L})]],
             align="c", anchor="m", line=1.05)
        x += w + 0.1
    bullets(s, 0.6, 2.6, 5.6, 4.2, [
        ("asyncio 스케줄러", " → 주기마다 워커 스레드 실행, 같은 작업은 동시에 한 번만(락), 결과는 rpa_logs"),
        ("트렌드 수집", " — 네이버 데이터랩 쇼핑인사이트 API + Playwright 랭킹 페이지, 카테고리 7개 · 시드 키워드 43개"),
        ("도매 소싱", " — 상위 8개 키워드로 검색 → 상품명·가격·이미지·링크 추출 → source_url 기준 upsert"),
        ("크롤링 준수", " — robots.txt 확인, 도메인별 요청 간격 제한(기본 2초)"),
        ("RPA_MODE=demo/live", " — demo는 외부 접속 없이 전체 흐름 시연"),
    ], size=12, gap=9)
    picture(s, A("screen-admin.png"), 6.55, 1.75, w=6.15)
    text(s, 6.55, 5.72, 6.15, 0.5, [[("관리자 · RPA 모니터  ", {"bold": True}), ("/admin/rpa — 작업 주기 · 즉시 실행 · 실행 로그 · 성공률", {"color": MUTED})]], size=10)
    notes(s, """여기서부터 제가 직접 맡은 부분입니다.
RPA 작업은 세 개이고, 스케줄러가 주기를 보고 워커 스레드에서 실행합니다. 같은 작업이 겹쳐 실행되면 중복 데이터가 생기기 때문에 작업 이름 단위로 락을 걸었고, 성공이든 실패든 모든 실행을 로그로 남겨서 관리자 화면에서 볼 수 있게 했습니다.
소싱은 같은 상품이 여러 번 수집되는 게 문제였는데, 원본 링크를 기준으로 있으면 가격과 재고만 갱신하고 없으면 새로 넣는 upsert로 처리했습니다.
그리고 크롤링은 수집 전에 robots.txt를 확인하고 같은 도메인에는 2초 간격을 두도록 했습니다. 외부 사이트에 부담을 주지 않는 것도 기술 요구사항이라고 생각했습니다.""")


def s07():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 7, "CORE ② · ANALYSIS & PRICING", "트렌드 분석 · 가격 로직과 시각화", mine=True)
    formulas = [
        ("앵커 정규화", "요청마다 최댓값 100 정규화 → 카테고리 첫 키워드(앵커)를 매 요청에 포함",
         "(키워드 7일 평균 ÷ 앵커 7일 평균) × 50"),
        ("급상승 판정", "직전 스냅샷 대비", "점수 +15% 이상  또는  순위 +5 이상"),
        ("판매가 · 마진", "도매가 × 2.2 → 천 원 단위 올림 → 900원 엔딩",
         "39,500 → 86,900원 · 마진 54.5%"),
        ("상품명 추천", "같은 카테고리 상위 트렌드 키워드 조합", "[시즌] + 상품명 + 키워드 무드"),
    ]
    for i, (t, d, f) in enumerate(formulas):
        x, y = 0.6 + (i % 2) * 3.35, 1.75 + (i // 2) * 2.45
        card(s, x, y, 3.2, 2.3)
        text(s, x + 0.22, y + 0.18, 2.8, 0.4, t, size=15, bold=True)
        text(s, x + 0.22, y + 0.62, 2.8, 0.8, d, size=10.5, color="555555", line=1.25)
        box(s, x + 0.15, y + 1.55, 2.9, 0.58, fill=INK if i != 2 else ACCENT, radius=0.1)
        text(s, x + 0.2, y + 1.57, 2.8, 0.54, f, size=11, color=CREAM, bold=True, anchor="m", align="c", line=1.1)
    picture(s, A("screen-trends.png"), 7.45, 1.75, w=5.25)
    text(s, 7.45, 5.15, 5.25, 0.9, [[("Plotly 시각화  ", {"bold": True}), ("검색 지수 라인 · 카테고리 트리맵 · Top 12 바 · 점수 비례 워드클라우드", {"color": MUTED})],
                                     [("가격 계산은 pytest로 고정 (39,500 → 86,900)", {"color": ACCENT, "bold": True})]], size=10.5, line=1.4)
    notes(s, """분석 로직에서 제일 고민한 건 데이터랩의 정규화 방식이었습니다. 이 API는 한 번 요청할 때마다 그 안에서 가장 큰 값을 100으로 맞춰 줍니다. 그래서 요청을 나눠 보내면 요청끼리 점수를 비교할 수가 없습니다.
저는 카테고리마다 기준이 되는 앵커 키워드를 하나 정해서 매 요청에 같이 넣었습니다. 그러면 모든 키워드를 앵커 대비 비율로 바꿀 수 있어서 요청이 달라도 같은 척도로 비교할 수 있습니다.
급상승은 직전 수집 대비 점수가 15% 이상 오르거나 순위가 5계단 이상 오르면 표시합니다. 가격은 도매가에 2.2배를 하고 900원 단위로 끝나게 맞췄습니다. 39,500원짜리는 86,900원, 마진율 54.5%가 되고, 이 계산은 테스트 코드로 고정해 두었습니다.""")


def s08():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 8, "CORE ③ · ORDER → PURCHASE ORDER", "주문 → 발주 자동화와 실시간 알림")
    steps = ["회원 주문", "공급처별\n그룹핑", "대기 발주서\n병합 / 생성", "Excel · PDF\n생성", "이메일 · 웹훅\n발송", "상태 변경\n+ WebSocket"]
    for i, t in enumerate(steps):
        x = 0.6 + i * 2.04
        s_ = s.shapes.add_shape(MSO_SHAPE.CHEVRON if i else MSO_SHAPE.PENTAGON, Inches(x), Inches(1.75), Inches(2.0), Inches(0.85))
        s_.fill.solid()
        s_.fill.fore_color.rgb = rgb(INK if i % 2 == 0 else "2A2725")
        s_.line.fill.background()
        text(s, x + 0.3, 1.78, 1.5, 0.8, t, size=11, color=CREAM, bold=True, align="c", anchor="m", line=1.1)
    bullets(s, 0.6, 2.95, 5.6, 3.9, [
        ("공급처별 묶음", " — 해당 공급처의 '대기' 발주서에 합치거나 새로 생성"),
        ("발주서 문서", " — openpyxl(Excel) · ReportLab(한글 CID 폰트 PDF), 표준형 / 간단형 템플릿"),
        ("발송", " — SMTP 이메일(첨부) · 웹훅(JSON) · 수동(전화·팩스)"),
        ("상태 추적", " — 대기 → 발송 완료 → 입고 확인, 주문 상태와 연동"),
        ("WebSocket", " — 워커 스레드에서도 call_soon_threadsafe로 이벤트 루프에 안전하게 전달"),
        ("받는 대상 분리", " — 주문·발주·RPA → 관리자만 / 일반 회원 → 본인 주문 상태만"),
    ], size=12, gap=7)
    picture(s, A("screen-po.png"), 6.55, 2.95, w=6.15)
    notes(s, """발주 자동화와 실시간 알림은 홍기흥 님이 맡았고, 저는 백엔드 쪽에서 주문 데이터 모델과 연결을 같이 설계했습니다.
주문이 들어오면 상품을 공급처별로 나누고, 그 공급처에 아직 보내지 않은 발주서가 있으면 거기에 합칩니다. 공급처 입장에서는 발주서를 여러 장 받는 것보다 한 장으로 받는 게 편하기 때문입니다.
알림에서 까다로웠던 건 스레드였습니다. RPA는 워커 스레드에서 돌고 WebSocket은 이벤트 루프에서 돌기 때문에, 스레드에서 바로 보내면 안전하지 않습니다. 그래서 call_soon_threadsafe로 루프에 넘기도록 했습니다. 그리고 다른 회원의 주문 정보가 새지 않도록 이벤트를 받는 사람을 권한별로 나눴습니다.""")


def s09():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 9, "SECURITY · AUTH & RBAC", "인증 · 보안과 3단계 권한")
    picture(s, A("screen-login.png"), 0.6, 1.75, w=5.4)
    bullets(s, 0.6, 5.35, 5.5, 1.6, [
        ("PBKDF2-SHA256 31만 회", " 해시 · 대소문자·숫자·특수문자 8자 이상 (프런트·백엔드 동일)"),
        ("OAuth 3사", " — state = 서명된 JWT(10분), 리다이렉트 허용 목록, 인증된 이메일만 계정 연결"),
    ], size=10.5, gap=4)
    table(s, 6.45, 1.75, 6.28, [
        ["권한", "진입", "가능 범위"],
        ["일반 회원", "가입 · 소셜 · 테스트 로그인", "쇼핑 · 주문 · 마이페이지"],
        ["실제 관리자", ".env ADMIN_TOKEN (5회 실패 시 5분 잠금)", "전체 CRUD"],
        ["테스트 관리자", "테스트 관리자 로그인 버튼", "관리자 화면 조회만"],
    ], [1.45, 2.95, 1.88], size=11, row_h=0.55)
    text(s, 6.45, 4.15, 6.28, 0.3, "읽기 전용 · 두 겹 방어", size=10, color=ACCENT, bold=True, spacing=250)
    for i, (t, d) in enumerate([("① read_only_guard 미들웨어", "테스트 관리자의 모든 변경 요청(POST·PUT·PATCH·DELETE)을 API 진입 전 403"),
                                ("② require_admin", "변경 API마다 실제 관리자인지 다시 확인"),
                                ("③ WriteButton (화면)", "변경 버튼에 잠금 표시 + 비활성, 상단 읽기 전용 배너")]):
        y = 4.5 + i * 0.75
        box(s, 6.45, y, 6.28, 0.65, fill=INK if i < 2 else WHITE, line=None if i < 2 else LINE, radius=0.1)
        text(s, 6.65, y + 0.04, 5.9, 0.58, [[(t + "   ", {"bold": True, "color": ACCENT_L if i < 2 else ACCENT}),
                                               (d, {"color": CREAM if i < 2 else "3A3A3A"})]], size=11, anchor="m")
    notes(s, """인증과 권한은 홍기흥 님 담당이고, 저는 백엔드에서 권한 검사 구조를 같이 잡았습니다.
특히 말씀드리고 싶은 건 테스트 관리자입니다. 면접관분들이 관리자 화면을 바로 보실 수 있게 버튼 하나로 들어오는 계정을 만들었는데, 그 비밀번호는 공개돼 있는 셈이라 데이터를 바꿀 수 있으면 안 됩니다.
그래서 두 겹으로 막았습니다. 요청이 API에 닿기 전에 미들웨어가 테스트 관리자의 변경 요청을 전부 막고, 혹시 빠져나가도 각 변경 API가 실제 관리자인지 다시 확인합니다. 실제 관리자는 서버 환경 변수에 있는 토큰으로만 들어올 수 있고, 다섯 번 틀리면 5분 동안 잠깁니다.""")


def s10():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 10, "DEMO · USER FLOW", "메인에서 발주까지, 하나의 흐름")
    flow = [("screen-main.png", "메인 룩북", "처음 접속 시 메인 · 실시간 트렌드"),
            ("screen-detail.png", "상품 상세", "색상별 이미지 · 옵션 선택"),
            ("screen-order.png", "주문 완료", "주문 즉시 발주서 자동 생성"),
            ("screen-mypage.png", "마이페이지", "주문 접수 → 발주 → 입고 단계"),
            ("screen-po.png", "관리자 발주서", "실시간 팝업 · 공급처별 발주서")]
    w = 2.3
    for i, (img, t, d) in enumerate(flow):
        x = 0.6 + i * (w + 0.157)
        picture(s, A(img), x, 1.95, w=w)
        text(s, x, 3.52, w, 0.4, [[(f"{i + 1:02d}  ", {"font": DISPLAY, "italic": True, "color": ACCENT, "size": 16}), (t, {"bold": True})]], size=13)
        text(s, x, 3.95, w, 0.6, d, size=10.5, color=MUTED, line=1.2)
        if i < 4:
            arrow(s, x + w + 0.0, 2.55, w=0.15, h=0.2, color=ACCENT)
    box(s, 0.6, 4.9, 12.13, 1.45, fill=WHITE, line=LINE, radius=0.04)
    bullets(s, 0.9, 5.08, 11.6, 1.2, [
        ("처음 접속하면 메인 페이지", " — 룩북 캐러셀 · 실시간 트렌드 · NEW ARRIVALS · TREND PICKS"),
        ("주문 즉시", " 공급처별 발주서 자동 생성 → 관리자 화면 실시간 팝업, 회원에게는 상태 변경 실시간 알림"),
        ("공개 쇼핑몰 API 분리", " — 도매가 · 공급처 · 마진은 노출하지 않음"),
    ], size=12, gap=6)
    notes(s, """실제 흐름을 보여 드리겠습니다. 처음 들어오면 메인 페이지가 열리고, 룩북과 실시간 트렌드 키워드가 보입니다.
상품을 골라 색상과 사이즈를 선택하고 구매하면, 그 순간 백엔드에서 공급처별 발주서가 만들어지고 관리자 화면에는 신규 주문 팝업이 뜹니다. 회원은 마이페이지에서 주문이 어느 단계에 있는지 볼 수 있습니다.
백엔드 입장에서 신경 쓴 점은 쇼핑몰용 API를 따로 만든 겁니다. 관리자 API를 그대로 쓰면 도매가와 마진이 노출되기 때문에, 공개 API는 판매 등록된 상품의 판매 정보만 내려가도록 분리했습니다.
(라이브 데모가 가능하면 이 슬라이드에서 진행하고, 실패하면 캡처로 설명합니다.)""")


def s11():
    s = prs.slides.add_slide(BLANK)
    bg(s, "EFEBE3")
    header(s, 11, "LOOKBOOK · UI/UX DESIGN SYSTEM", "상용 패션몰 수준의 반응형 UI/UX")
    picture(s, A("screen-main.png"), 0.6, 1.75, w=6.0)
    picture(s, A("screen-mobile.png"), 7.0, 1.75, h=3.75)
    picture(s, A("screen-drawer.png"), 8.9, 1.75, h=3.75)
    bullets(s, 10.9, 1.85, 1.85, 4, ["햄버거 ↔ X 모션", "우측 슬라이딩 Drawer", "카테고리 가로 스크롤", "다크 모드"], size=11, gap=10)
    # design tokens
    y = 5.75
    text(s, 0.6, y, 2, 0.3, "COLOR", size=9, color=MUTED, bold=True, spacing=250)
    for i, (c, n) in enumerate([(INK, "Ink"), ("FFFFFF", "Paper"), (ACCENT, "Accent"), (BURGUNDY, "Burgundy"), (CAMEL, "Camel")]):
        dot = box(s, 0.6 + i * 0.62, y + 0.3, 0.42, 0.42, fill=c, line=LINE, shape=MSO_SHAPE.OVAL)
        dot.shadow.inherit = False
        text(s, 0.48 + i * 0.62, y + 0.75, 0.66, 0.2, n, size=7, color=MUTED, align="c")
    text(s, 3.95, y, 3, 0.3, "TYPOGRAPHY", size=9, color=MUTED, bold=True, spacing=250)
    text(s, 3.95, y + 0.25, 3.3, 0.7, [[("Aa ", {"font": DISPLAY, "italic": True, "size": 24}), ("Playfair Display", {"size": 10, "color": MUTED})],
                                        [("가 ", {"bold": True, "size": 18}), ("Pretendard 본문", {"size": 10, "color": MUTED})]], line=1.0)
    text(s, 7.0, y, 5.7, 0.3, "LAYOUT STANDARD", size=9, color=MUTED, bold=True, spacing=250)
    text(s, 7.0, y + 0.3, 5.7, 0.8, [["모든 페이지 공통 헤더 · 푸터 · 원형 To the Top"],
                                       [("그리드 2 · 3 · 4열  ·  상품 이미지 4:5  ·  카테고리 실루엣 SVG", {"bold": True})]], size=10.5, line=1.35)
    notes(s, """화면은 이오리 님이 맡았습니다. 목표는 W컨셉이나 29CM 같은 실제 패션몰처럼 보이는 것이었고, 그래서 헤더와 푸터를 모든 페이지에 똑같이 쓰고 여백, 글자 크기, 그리드 열 수를 규칙으로 정해 두었습니다.
모바일에서는 햄버거 버튼이 X로 바뀌면서 오른쪽에서 메뉴가 나옵니다.
제가 같이 결정한 건 상품 이미지입니다. 도매 사이트 이미지를 그대로 쓰면 저작권 문제가 생길 수 있어서, 데모에서는 서버가 카테고리별 옷 실루엣을 SVG로 그려서 내려주게 했습니다. 벡터라 해상도 문제도 없습니다.""")


def s12():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 12, "BACK OFFICE · ADMIN CONSOLE", "관리자 백오피스와 읽기 전용 모드")
    menus = [("대시보드", "오늘 주문 · 발주 대기 · 판매 등록 · 급상승, 실시간 이벤트 피드"),
             ("상품 소싱", "Masonry 갤러리 · 도매가·판매가·마진율 · 추천 상품명 원클릭 등록"),
             ("주문 · 발주", "공급처별 발주서 · 미리보기 · Excel/PDF · 발송 · 입고 확인"),
             ("RPA 작업", "주기 변경 · 즉시 실행 · 실행 로그 · 성공률 차트"),
             ("공급처", "수신 방식(이메일·웹훅·수동) · 발주 템플릿"),
             ("회원 권한", "일반 ⇄ 관리자 실시간 변경 · 본인 강등 / 테스트 관리자 승격 차단")]
    for i, (t, d) in enumerate(menus):
        x, y = 0.6 + (i % 2) * 2.95, 1.75 + (i // 2) * 1.62
        card(s, x, y, 2.8, 1.48)
        text(s, x + 0.2, y + 0.15, 2.4, 0.4, [[(f"{i + 1:02d}  ", {"font": DISPLAY, "italic": True, "color": ACCENT, "size": 14}), (t, {"bold": True})]], size=13)
        text(s, x + 0.2, y + 0.6, 2.45, 0.85, d, size=10, color="555555", line=1.25)
    picture(s, A("screen-members.png"), 6.65, 1.75, w=6.05)
    text(s, 6.65, 5.65, 6.05, 0.7, [[("테스트 관리자 화면  ", {"bold": True}), ("모든 화면 조회 가능 · 상단 읽기 전용 배너 · 잠금 표시된 변경 버튼", {"color": MUTED})],
                                     [("화면에서 한 번, 서버에서 두 번 차단", {"bold": True, "color": ACCENT})]], size=10.5, line=1.4)
    notes(s, """관리자 화면은 여섯 개 메뉴로 구성했습니다. 제가 백엔드를 만든 RPA 작업 화면에서는 작업마다 주기를 바꾸고, 지금 바로 실행하고, 실행 로그와 성공률을 볼 수 있습니다.
테스트 관리자로 들어오면 화면은 똑같이 다 보이지만 위에 읽기 전용 배너가 뜨고, 바꾸는 버튼에는 잠금 표시가 붙습니다. 화면에서 한 번, 서버에서 두 번 막는 구조입니다.
권한 변경에도 실수 방지 장치를 넣었습니다. 관리자가 자기 자신을 강등하거나, 비밀번호가 공개된 테스트 관리자 계정을 관리자로 올리는 건 서버에서 거절합니다.""")


def s13():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 13, "DEVOPS · CI/CD", "Git 연동 자동 배포와 CI")
    box(s, 0.6, 1.85, 2.0, 0.8, fill=INK, radius=0.15)
    text(s, 0.6, 1.88, 2.0, 0.74, [[("git push", {"font": MONO, "color": CREAM, "size": 13})], [("main", {"color": ACCENT_L, "bold": True, "size": 11})]], align="c", anchor="m", line=1.1)
    targets = [("Netlify", "스테이징 프런트 빌드·배포"), ("Render Static", "프로덕션 프런트"), ("Render Docker", "API 이미지 빌드·배포"),
               ("GitHub Actions · ci.yml", "push/PR마다 pytest 27개 + 프런트 빌드"), ("GitHub Actions · pages.yml", "docs/** 변경 시에만 Pages 배포")]
    for i, (t, d) in enumerate(targets):
        y = 1.6 + i * 0.95
        arrow(s, 2.75, y + 0.28, w=0.45, h=0.25, color=ACCENT if i < 3 else MUTED)
        card(s, 3.35, y, 3.8, 0.8, fill=WHITE if i < 3 else SOFT, line=LINE if i < 3 else None)
        text(s, 3.55, y + 0.05, 3.5, 0.7, [[(t, {"bold": True})], [(d, {"color": MUTED, "size": 10})]], size=12, anchor="m")
    text(s, 0.6, 6.4, 6.6, 0.4, "별도 Deploy Hook 없이 플랫폼 Git 연동으로 단순화", size=11, color=ACCENT, bold=True)
    box(s, 7.6, 1.6, 5.13, 2.45, fill=DARK, radius=0.04)
    text(s, 7.85, 1.75, 4.7, 2.6, [
        [("# Dockerfile (요약)", {"color": "8A857C"})],
        [("FROM ", {"color": ACCENT_L}), "python:3.11-slim"],
        [("RUN ", {"color": ACCENT_L}), "apt-get install libatomic1 libstdc++6"],
        ["  && pip install -r requirements.txt"],
        ["  && playwright install --with-deps chromium"],
        [("COPY ", {"color": ACCENT_L}), "backend ./backend · rpa ./rpa"],
        [("USER ", {"color": ACCENT_L}), "app   # non-root"],
        [("CMD ", {"color": ACCENT_L}), "uvicorn ... --port ${PORT}"],
    ], size=10.5, font=MONO, color=CREAM, line=1.3)
    bullets(s, 7.6, 4.35, 5.13, 2.1, [
        ("설정 파일", " — render.yaml · netlify.toml · docker-compose.yml"),
        (".env 하나로 관리", " — .env.example에 [Render 필수] 항목 표시"),
        ("비밀값", "은 저장소에 넣지 않고 플랫폼 환경 변수로 주입"),
    ], size=11.5, gap=6)
    notes(s, """배포는 박미금 조장님이 맡았습니다. main에 푸시하면 Netlify와 Render가 각자 알아서 빌드하고 배포합니다. 처음에는 GitHub Actions에서 배포 훅을 호출하는 방식도 만들었는데, 플랫폼 Git 연동과 기능이 겹쳐서 단순한 쪽으로 정리했습니다.
Actions는 품질 확인에 집중합니다. 푸시할 때마다 pytest 27개 케이스와 프런트 빌드를 돌리고, 문서 폴더가 바뀔 때만 프로젝트 페이지를 배포합니다.
저는 Docker 이미지에 Playwright를 넣는 부분을 같이 작업했고, 그 과정에서 겪은 문제를 다음 장에서 말씀드리겠습니다.""")


def s14():
    s = prs.slides.add_slide(BLANK)
    bg(s, DARK)
    header(s, 14, "TROUBLESHOOTING", "추측 대신, 원인을 직접 확인했습니다", mine=True, dark=True)
    cases = [
        ("01", "Render 배포 연쇄 장애",
         "open Dockerfile: no such file → libatomic.so.1 없음, exit 127",
         "서비스 설정·Dockerfile 위치 불일치 확인 → Playwright Node 드라이버 ELF 의존성(DT_NEEDED) 직접 분석",
         "Dockerfile 루트 이동, libatomic1 · libstdc++6 선설치", "필요 라이브러리를 Dockerfile 주석으로 문서화"),
        ("02", "데이터랩 정규화 왜곡",
         "요청을 나누면 키워드 점수끼리 비교 불가",
         "API가 요청마다 최댓값을 100으로 맞춘다는 점을 응답으로 확인",
         "카테고리 앵커 키워드를 매 요청에 포함, 앵커 대비 비율로 환산", "수집 모듈 docstring에 정규화 방식 기록"),
        ("03", "스키마 변경 미반영",
         "새 컬럼 orders.user_id가 기존 DB에 생기지 않음",
         "create_all은 없는 테이블만 만들고 기존 테이블은 건드리지 않음",
         "기동 시 컬럼을 확인해 추가하는 ensure_schema", "향후 Alembic 마이그레이션 도입"),
    ]
    for i, (n, t, sym, cause, fix, prevent) in enumerate(cases):
        x = 0.6 + i * 4.1
        box(s, x, 1.75, 3.9, 5.0, fill="1A1817", line="2E2B28", radius=0.03)
        text(s, x + 0.25, 1.9, 1.2, 0.6, n, size=30, color=ACCENT_L, font=DISPLAY, italic=True)
        text(s, x + 1.1, 2.0, 2.7, 0.55, t, size=15, color=CREAM, bold=True, anchor="m")
        y = 2.72
        for label, body, h in (("현상", sym, 0.78), ("원인 분석", cause, 1.05), ("해결", fix, 0.78), ("재발 방지", prevent, 0.62)):
            text(s, x + 0.25, y, 3.4, 0.25, label, size=8.5, color=ACCENT_L, bold=True, spacing=200)
            text(s, x + 0.25, y + 0.25, 3.45, h - 0.25, body, size=10.5, color="DAD5CC" if label != "해결" else CREAM,
                 bold=(label == "해결"), font=SANS, line=1.2)
            y += h + 0.08
    notes(s, """세 가지를 말씀드리겠습니다.
첫 번째는 배포입니다. Render 빌드가 Dockerfile을 못 찾다가, 그걸 고치니 이번엔 Playwright가 라이브러리가 없다며 실패했습니다. 에러에 나온 라이브러리 하나만 넣고 다시 배포하면 또 다른 게 빠질 수 있어서, Playwright 패키지를 받아 안에 있는 Node 실행 파일이 필요로 하는 라이브러리 목록을 직접 읽었습니다. 그 결과 libatomic 말고 libstdc++도 필요하다는 걸 알고 한 번에 넣었습니다. 추측으로 여러 번 배포하는 대신 원인을 직접 확인한 사례입니다.
두 번째는 앞에서 설명드린 데이터랩 정규화 문제이고, 세 번째는 DB입니다. 주문에 회원 ID 컬럼을 추가했는데 이미 테이블이 있는 운영 DB에는 컬럼이 생기지 않았습니다. 지금은 기동할 때 확인해서 추가하는 가벼운 마이그레이션으로 해결했고, 다음 단계로 Alembic을 도입할 계획입니다.

[예상 질문 대비 추가 사례]
- Vite 환경 변수 빌드 시점 고정 (이오리·박미금): Render 프런트가 localhost API 호출 → 배포된 JS 번들 문자열 확인 → 프로덕션 기본 API 주소와 CORS 기본 도메인 추가
- 읽기 전용 403이 CORS 오류로 보임 (홍기흥): 차단 미들웨어가 CORS 바깥 → 등록 순서 조정, 회귀 테스트로 고정
- 로컬 .env가 운영 DB를 가리킨 사고: 로컬·테스트는 SQLite 원칙, AGENTS.md 문서화, 노출된 DB 자격증명 교체 [확인 필요 — 교체 완료 여부]""")


def s15():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 15, "TEAMWORK · DOCUMENTATION", "협업과 문서화")
    team = [("박미금 (조장)", "PM · ARCHITECTURE · DEVOPS", "일정·범위 관리, 시스템 구성, Docker, Render/Netlify, GitHub Actions"),
            ("김모란 (발표)", "BACKEND · RPA · DATA", "FastAPI 도메인 설계, 트렌드 수집·소싱·스케줄러, 분석·가격 로직, DB 스키마·마이그레이션"),
            ("이오리", "FRONTEND · UI/UX", "React 스토어프런트, 공통 레이아웃, 디자인 시스템, 관리자 화면, Plotly"),
            ("홍기흥", "ORDER · REALTIME · AUTH · QA", "발주서 Excel/PDF, SMTP·웹훅, WebSocket, OAuth, 3단계 권한, pytest")]
    for i, (n, role, d) in enumerate(team):
        x, y = 0.6 + (i % 2) * 3.65, 1.75 + (i // 2) * 2.25
        me = i == 1
        card(s, x, y, 3.5, 2.1, fill=INK if me else WHITE, line=None if me else LINE)
        text(s, x + 0.22, y + 0.18, 3.1, 0.3, role, size=8.5, color=ACCENT_L if me else ACCENT, bold=True, spacing=150)
        text(s, x + 0.22, y + 0.5, 3.1, 0.45, n, size=17, color=CREAM if me else INK, bold=True)
        text(s, x + 0.22, y + 1.02, 3.05, 1.0, d, size=10.5, color="C9C4BA" if me else "555555", line=1.25)
    text(s, 8.15, 1.75, 4.5, 0.3, "DOCS TREE", size=10, color=ACCENT, bold=True, spacing=300)
    box(s, 8.15, 2.1, 4.58, 3.0, fill=WHITE, line=LINE, radius=0.03)
    text(s, 8.35, 2.25, 4.3, 2.8, [
        "docs/",
        "├─ 프로젝트_진행일지_1~5단계.hwpx",
        "│   기획분석 · 설계 · 구현 · 배포 · 피드백",
        "├─ 산출물/01~05_*_산출물.hwpx",
        "├─ architecture.md   설계서",
        "├─ deployment.md     배포 가이드",
        "├─ presentation.md   발표 구성안",
        "└─ index.html        GitHub Pages",
        "readme.md · AGENTS.md (개발 규칙)",
    ], size=10, font=MONO, color="333333", line=1.3)
    bullets(s, 8.15, 5.3, 4.58, 1.5, [("AGENTS.md", " — 실행 명령 · 코드 규칙 · 권한 체계 · 로컬 주의사항을 팀 공통 규칙으로"),
                                     ("역할 분담은 팀 확인 필요", "")], size=10.5, gap=4)
    notes(s, """네 명이 같은 저장소에서 일하다 보니 규칙을 문서로 맞추는 게 중요했습니다. 진행일지는 기획부터 피드백까지 다섯 단계로 나눠 쓰고, 단계마다 산출물을 남겼습니다.
설계서와 배포 가이드는 마크다운으로 저장소에 같이 두었고, 특히 AGENTS.md에는 실행 명령, 코드 규칙, 권한 구조, 로컬 환경 주의사항을 모았습니다. 예를 들어 "로컬 테스트는 SQLite로 돌린다" 같은 규칙이 여기 있어서, 누가 작업해도 같은 기준으로 움직일 수 있었습니다.""")


def s16():
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    header(s, 16, "RETROSPECTIVE · NEXT STEP", "회고와 향후 고도화")
    text(s, 0.6, 1.75, 5, 0.3, "LESSONS LEARNED", size=10, color=ACCENT, bold=True, spacing=300)
    lessons = ["무료 인프라 제약(단일 인스턴스, 휘발성 디스크)이 설계를 결정한다",
               "에러 메시지를 고치기보다 원인을 직접 확인하는 것이 배포 횟수를 줄인다",
               "테스트와 운영 환경 분리는 규칙으로 문서화해야 지켜진다"]
    for i, l in enumerate(lessons):
        y = 2.15 + i * 1.45
        text(s, 0.6, y, 0.9, 0.8, f"{i + 1:02d}", size=34, color=ACCENT, font=DISPLAY, italic=True)
        text(s, 1.5, y + 0.12, 4.4, 1.1, l, size=14, bold=True, line=1.3)
        rule(s, 0.6, y + 1.3, 5.3, color=LINE, weight=0.75)
    road = [("단기", ["Alembic 마이그레이션", "실제 공급처 어댑터 (도매꾹 Open API 등)"], WHITE, INK),
            ("중기", ["S3/R2 이미지 저장소", "Celery/Redis 작업 큐로 RPA 워커 분리"], SOFT, INK),
            ("장기", ["LLM 상품 설명·키워드 군집화", "결제(PG) 연동", "AWS 이관"], INK, CREAM)]
    text(s, 6.55, 1.75, 5, 0.3, "ROADMAP", size=10, color=ACCENT, bold=True, spacing=300)
    for i, (t, items, fill, fg) in enumerate(road):
        x = 6.55 + i * 2.1
        card(s, x, 2.15, 1.98, 4.4, fill=fill, line=LINE if fill != INK else None)
        text(s, x + 0.2, 2.3, 1.6, 0.5, t, size=20, color=ACCENT_L if fill == INK else ACCENT, font=SANS, bold=True)
        text(s, x + 0.2, 2.95, 1.62, 3.4, ["• " + it for it in items], size=12.5, color=fg, line=1.3, para_space=14)
    notes(s, """회고입니다. 가장 크게 배운 건 인프라 제약이 설계를 정한다는 점이었습니다. 무료 티어는 인스턴스가 하나이고 디스크가 재배포 때 지워지기 때문에, 스케줄러를 API 안에 두었고 이미지 저장은 아직 임시로 남아 있습니다.
그래서 다음 단계는 분명합니다. 먼저 Alembic으로 마이그레이션을 정식화하고, 이미지는 S3 같은 외부 저장소로 옮기고, RPA는 Celery와 Redis로 별도 워커로 분리하려고 합니다. 그 위에 LLM으로 상품 설명을 만들고 키워드를 묶는 기능까지 확장하는 것이 목표입니다.""")


def s17():
    s = prs.slides.add_slide(BLANK)
    bg(s, DARK)
    text(s, 0.7, 0.62, 8, 0.3, f"No.17  —  Q&A · LIVE DEMO", size=10, color="9B978E", bold=True, spacing=300)
    text(s, 0.7, 1.0, 6, 1.6, "Q&A", size=88, color=CREAM, font=DISPLAY, italic=True)
    text(s, 0.7, 2.6, 6.2, 0.5, "Thank you.  감사합니다.", size=20, color=ACCENT_L, font=DISPLAY, italic=True)
    text(s, 0.7, 3.4, 6.3, 1.6, [
        [("PRODUCTION  ", {"size": 9, "color": "9B978E", "bold": True}), "fashionpick.onrender.com"],
        [("STAGING  ", {"size": 9, "color": "9B978E", "bold": True}), "fashionpick.netlify.app"],
        [("API DOCS  ", {"size": 9, "color": "9B978E", "bold": True}), "fashionpick-api.onrender.com/docs"],
        [("PROJECT  ", {"size": 9, "color": "9B978E", "bold": True}), "fsclass-n.github.io/fashionpick"],
    ], size=13, color=CREAM, line=1.55)
    box(s, 0.7, 5.2, 6.2, 1.5, fill="1A1817", line="2E2B28", radius=0.06)
    text(s, 0.95, 5.3, 5.8, 1.35, [
        [("체험 방법", {"bold": True, "color": ACCENT_L})],
        [("일반 회원 테스트 로그인", {"bold": True}), " → 상품 구매 → 마이페이지 주문 단계"],
        [("테스트 관리자 로그인", {"bold": True}), " → 관리자 화면 전체 조회 (읽기 전용)"],
        [("Render 무료 티어라 첫 접속에 30초 이상 걸릴 수 있음", {"color": "9B978E", "size": 10})],
    ], size=11.5, color=CREAM, line=1.4)
    text(s, 7.6, 0.75, 5.1, 0.3, "EXPECTED QUESTIONS", size=10, color=ACCENT_L, bold=True, spacing=300)
    qs = [("왜 Celery 대신 API 안의 스케줄러?", "무료 티어 단일 인스턴스 · 작업별 락과 로그 · 확장 시 Celery/Redis"),
          ("크롤링은 법적으로 괜찮나요?", "robots.txt 확인 · 도메인별 2초 간격 · 허용 사이트만 · 시연은 demo 모드"),
          ("테스트 관리자 우회 가능성?", "DB에서 권한 재확인 · 미들웨어 + 변경 API 두 겹 · 읽기 전용 고정"),
          ("Render가 잠들면 스케줄러는?", "슬립 중 멈춤 · 깨어나면 주기 지난 작업부터 실행 · 근본 해결은 워커 분리"),
          ("데이터 중복·정합성은?", "트렌드는 batch 스냅샷 · 소싱은 source_url upsert · 같은 작업 동시 실행 금지")]
    for i, (q, a) in enumerate(qs):
        y = 1.15 + i * 0.8
        text(s, 7.6, y, 5.1, 0.75, [[(f"Q{i + 1}  ", {"font": DISPLAY, "italic": True, "color": ACCENT_L, "size": 13}), (q, {"bold": True})],
                                     [(a, {"color": "B5B0A6", "size": 10})]], size=12, color=CREAM, line=1.25)
    qr(s, "prod", 7.75, 5.35, "LIVE", size=0.95, dark=True)
    qr(s, "api", 9.45, 5.35, "API DOCS", size=0.95, dark=True)
    qr(s, "github", 11.15, 5.35, "GITHUB", size=0.95, dark=True)
    notes(s, """발표는 여기까지입니다. 화면의 QR로 바로 접속해 보실 수 있고, 가입 없이 일반 회원이나 테스트 관리자 버튼으로 체험하실 수 있습니다. 무료 서버라 첫 접속이 조금 느릴 수 있는 점 양해 부탁드립니다.
질문 주시면 답변드리겠습니다. 감사합니다.""")


if __name__ == "__main__":
    build_assets()
    for fn in (s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12, s13, s14, s15, s16, s17):
        fn()
    prs.core_properties.title = "fashionpick 프로젝트 발표"
    prs.core_properties.author = "김모란 (fashionpick 3조)"
    prs.save(OUT)
    print(f"saved {OUT} ({len(prs.slides)} slides)")
    os.environ.get("KEEP_TMP") or __import__("shutil").rmtree(tmp, ignore_errors=True)
