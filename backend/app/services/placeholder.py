"""데모 상품 이미지: 카테고리별 실루엣을 스튜디오 컷 느낌으로 그린 SVG (외부 이미지 의존 없음, 벡터라 고해상도 대응)."""
from html import escape

from rpa.trend.collector import SEED_KEYWORDS

PALETTE = {"블랙": "#1f1f1f", "아이보리": "#efe8da", "그레이": "#9a9a9a", "네이비": "#23304a", "베이지": "#d8c3a5",
           "브라운": "#6b4a35", "카키": "#6b6b47", "버건디": "#6d2233", "스카이블루": "#9cc3e0"}
LIGHT = {"아이보리", "베이지", "스카이블루", "그레이"}
KEYWORD_CATEGORY = {kw: cat for cat, kws in SEED_KEYWORDS.items() for kw in kws}

# viewBox 400x500 기준 실루엣 (body: 채움, detail: 선)
SHAPES = {
    "아우터": ("M152 104 L182 96 L200 150 L218 96 L248 104 L296 128 L326 330 L296 336 L278 196 L282 420 L118 420 "
              "L122 196 L104 336 L74 330 L104 128 Z",
              "M200 150 L200 420 M182 96 L170 190 L200 150 L230 190 L218 96",
              '<circle cx="212" cy="230" r="4"/><circle cx="212" cy="280" r="4"/><circle cx="212" cy="330" r="4"/>'),
    "상의": ("M150 118 Q200 138 250 118 L300 136 L338 214 L306 230 L284 190 L284 392 L116 392 L116 190 L94 230 "
            "L62 214 L100 136 Z",
            "M168 121 Q200 152 232 121 M116 370 L284 370 M94 230 L62 214 M306 230 L338 214", ""),
    "하의": ("M132 100 L268 100 L282 420 L220 420 L200 182 L180 420 L118 420 Z",
            "M132 126 L268 126 M200 126 L200 182 M150 140 Q160 170 180 172", ""),
    "원피스": ("M170 100 L184 100 L190 140 L210 140 L216 100 L230 100 L238 172 Q250 200 306 420 L94 420 "
             "Q150 200 162 172 Z",
             "M164 198 Q200 208 236 198 M150 300 Q200 312 250 300", ""),
    "슈즈": ("M70 330 Q72 286 112 278 L160 272 Q184 300 236 310 L300 318 Q336 324 336 350 L336 360 L70 360 Z",
            "M70 360 L336 360 M112 278 Q126 300 160 300 M180 292 L196 304 M196 288 L212 300",
            '<rect x="70" y="360" width="266" height="12" rx="4" opacity=".55"/>'),
    "가방": ("M108 230 L292 230 L310 410 L90 410 Z",
            "M108 270 L292 270",
            '<path d="M150 232 Q150 140 200 140 Q250 140 250 232" fill="none" stroke="FILL" stroke-width="10"/>'
            '<rect x="186" y="262" width="28" height="18" rx="3"/>'),
    "액세서리": ("M104 310 Q108 196 200 190 Q292 196 296 310 Z M250 306 Q340 302 352 330 Q300 338 200 326 Z",
              "M200 192 L200 310 M150 206 Q162 260 160 310 M250 206 Q238 260 240 310",
              '<circle cx="200" cy="192" r="6"/>'),
}


TRANSFORMS = {"슈즈": "translate(-30 -78) scale(1.15)"}


def render(seed: str, label: str, color: str, category: str | None) -> str:
    category = category if category in SHAPES else KEYWORD_CATEGORY.get(label, "상의")
    body, detail, extra = SHAPES[category]
    fill = PALETTE.get(color, "#8a8378")
    extra = extra.replace("FILL", fill)
    transform = TRANSFORMS.get(category, "")
    light = color in LIGHT
    h = int(seed[:6], 16) if len(seed) >= 6 and all(c in "0123456789abcdef" for c in seed[:6]) else 0
    bg = ["#efede8", "#ece9e3", "#f1efeb", "#e9e6df"][h % 4] if not light else ["#dedad2", "#e2ddd3", "#d9d5cc"][h % 3]
    line = "rgba(0,0,0,.22)" if light else "rgba(255,255,255,.18)"
    accent = "rgba(0,0,0,.35)" if light else "rgba(255,255,255,.35)"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" width="800" height="1000" role="img" aria-label="{escape(label)} {escape(color)}">
<defs><radialGradient id="g" cx="50%" cy="42%" r="70%"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<linearGradient id="s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".14"/><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".18"/></linearGradient></defs>
<rect width="400" height="500" fill="{bg}"/><rect width="400" height="500" fill="url(#g)"/>
<ellipse cx="200" cy="440" rx="128" ry="9" fill="#000" opacity=".10"/>
<g transform="{transform}"><path d="{body}" fill="{fill}"/><path d="{body}" fill="url(#s)"/>
<path d="{detail}" fill="none" stroke="{line}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
<g fill="{accent}">{extra}</g></g>
</svg>"""
