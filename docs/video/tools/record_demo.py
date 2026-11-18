"""운영 사이트(fashionpick.onrender.com) 시연 자동 녹화.

- CDP 스크린캐스트(JPEG 92%)로 프레임과 타임스탬프를 저장해 고화질로 녹화한다 (Playwright 기본 녹화보다 선명)
- 장면마다 [시작, 끝] 시각을 markers.json 에 남기고, 장면 시간(scenes.py dur)이 될 때까지 기다린다
- 사이트 안 이동은 클릭(React Router)으로만 한다 → 전체 새로고침 흰 화면 없음
- 외부 페이지(API 문서)는 장면 시작 전에 열고 로딩이 끝난 뒤 장면을 시작한다
- 커서(노란 원)·클릭 링·테두리 강조는 페이지 위에 덧씌운 요소로 그린다 (화면 전체를 덮는 막 없음)
- 운영 DB 영향: 일반 회원 테스트 계정으로 주문 1건이 생성된다. 테스트 관리자는 읽기 전용이라 아무것도 바꾸지 않는다.
"""
import base64
import json
import math
import sys
import time
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from common import DEMO_DIR, save_json
from scenes import SCENES

BASE = "https://fashionpick.onrender.com"
API = "https://fashionpick-api.onrender.com"
DUR = {s["id"]: s["dur"] for s in SCENES}
FRAMES = DEMO_DIR / "frames"
ADMIN_ONLY = "--admin-only" in sys.argv  # 일반 회원 구간(운영 주문 생성)은 유지하고 관리자 구간만 다시 녹화
RUN = time.strftime("%H%M%S")

OVERLAY_JS = r"""
(() => {
  if (window.__fpOverlay) return; window.__fpOverlay = true;
  const css = `
  #__cur{position:fixed;left:0;top:0;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;
    background:rgba(255,212,0,.32);border:2px solid rgba(240,180,0,.95);pointer-events:none;z-index:2147483647;
    box-shadow:0 0 0 1px rgba(255,255,255,.6)}
  .__ring{position:fixed;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;border:3px solid rgba(240,180,0,.95);
    pointer-events:none;z-index:2147483647;animation:__ring .55s ease-out forwards}
  @keyframes __ring{from{transform:scale(.6);opacity:1}to{transform:scale(2.3);opacity:0}}
  .__hl{position:fixed;border:3px solid #22d3ee;border-radius:12px;box-shadow:0 0 16px rgba(34,211,238,.45);
    pointer-events:none;z-index:2147483646;opacity:0;transition:opacity .3s ease}
  .__addr{position:fixed;left:50%;top:14px;transform:translateX(-50%);z-index:2147483647;pointer-events:none;
    background:#fff;border:1px solid #d6d6d6;border-radius:999px;padding:8px 22px;font:600 17px "Malgun Gothic",sans-serif;
    color:#111;box-shadow:0 8px 24px rgba(0,0,0,.15);opacity:0;transition:opacity .3s}
  .__addr b{color:#b4532a}
  main{min-height:100vh}
  ::-webkit-scrollbar{width:0;height:0}
  html{scrollbar-width:none}`;
  function init() {
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    const cur = document.createElement('div'); cur.id = '__cur'; document.body.appendChild(cur);
    const pos = window.__curPos || [960, 540];
    cur.style.transform = `translate(${pos[0]}px,${pos[1]}px)`;
    document.addEventListener('mousemove', e => { window.__curPos = [e.clientX, e.clientY];
      cur.style.transform = `translate(${e.clientX}px,${e.clientY}px)`; }, true);
    document.addEventListener('mousedown', e => { const r = document.createElement('div'); r.className = '__ring';
      r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'; document.body.appendChild(r);
      setTimeout(() => r.remove(), 600); }, true);
  }
  window.__hl = (el, ms = 1800, pad = 6) => {
    if (!el) return; const r = el.getBoundingClientRect(); const d = document.createElement('div'); d.className = '__hl';
    Object.assign(d.style, {left: (r.left - pad) + 'px', top: (r.top - pad) + 'px', width: (r.width + pad * 2) + 'px', height: (r.height + pad * 2) + 'px'});
    document.body.appendChild(d); requestAnimationFrame(() => requestAnimationFrame(() => d.style.opacity = 1));
    setTimeout(() => { d.style.opacity = 0; setTimeout(() => d.remove(), 350); }, ms);
  };
  window.__addr = (path, ms = 2600) => {
    const d = document.createElement('div'); d.className = '__addr';
    d.innerHTML = 'fashionpick.onrender.com<b>' + path + '</b>'; document.body.appendChild(d);
    requestAnimationFrame(() => requestAnimationFrame(() => d.style.opacity = 1));
    setTimeout(() => { d.style.opacity = 0; setTimeout(() => d.remove(), 350); }, ms);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
"""


class Recorder:
    def __init__(self, context, page):
        FRAMES.mkdir(parents=True, exist_ok=True)
        if not ADMIN_ONLY:
            for f in FRAMES.glob("*.jpg"):
                f.unlink()
        self.page, self.context, self.frames, self.n = page, context, [], 0
        self.cdp = None
        self.pos = [960, 540]

    def start(self):
        self.cdp = self.context.new_cdp_session(self.page)
        self.cdp.on("Page.screencastFrame", self._frame)
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1})

    def stop(self):
        if self.cdp:
            try:
                self.cdp.send("Page.stopScreencast")
                self.cdp.detach()
            except Exception:  # noqa: BLE001
                pass
            self.cdp = None

    def _frame(self, params):
        name = f"{RUN}_{self.n:06d}.jpg"
        (FRAMES / name).write_bytes(base64.b64decode(params["data"]))
        self.frames.append([params["metadata"]["timestamp"], name])
        self.n += 1
        try:
            self.cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:  # noqa: BLE001
            pass


def main():
    markers = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--hide-scrollbars", "--force-color-profile=srgb"])

        # 0) 콜드 스타트 해소 (녹화하지 않는 별도 페이지)
        warm = browser.new_page()
        warm.goto(f"{API}/health", timeout=180000)
        for path in ("/api/shop/home", "/api/trends/public-top", "/api/auth/providers", "/api/trends/latest", "/api/trends/categories"):
            warm.goto(API + path, timeout=120000)
        warm.goto(BASE, timeout=120000)
        warm.wait_for_timeout(3000)
        warm.close()

        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1, locale="ko-KR",
                                  color_scheme="light", timezone_id="Asia/Seoul")
        ctx.add_init_script(OVERLAY_JS)
        page = ctx.new_page()
        rec = Recorder(ctx, page)

        def pause(ms):
            page.wait_for_timeout(ms)

        def move(x, y, dur=0.7):
            sx, sy = rec.pos
            steps = max(8, int(dur * 30))
            for i in range(1, steps + 1):
                t = i / steps
                e = 0.5 - math.cos(math.pi * t) / 2
                page.mouse.move(sx + (x - sx) * e, sy + (y - sy) * e)
                page.wait_for_timeout(dur * 1000 / steps)
            rec.pos = [x, y]

        def center(loc):
            loc.scroll_into_view_if_needed()
            b = loc.bounding_box()
            return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

        def move_to(loc, dur=0.7, dx=0, dy=0):
            x, y = center(loc)
            move(x + dx, y + dy, dur)

        def click(loc, dur=0.7, wait=600):
            move_to(loc, dur)
            pause(450)
            page.mouse.down()
            pause(90)
            page.mouse.up()
            pause(wait)

        def hl(loc, ms=1800):
            loc.evaluate("(el, ms) => window.__hl(el, ms)", ms)

        def rest_beside(loc):
            """말하는 동안 커서를 영역 오른쪽 아래 여백에 둔다."""
            b = loc.bounding_box()
            move(min(1880, b["x"] + b["width"] + 40), min(1040, b["y"] + b["height"] + 30), 0.6)

        def scroll(dy, ms=1100):
            page.evaluate("dy => window.scrollBy({top: dy, behavior: 'smooth'})", dy)
            pause(ms)

        def scroll_top(ms=1000):
            page.evaluate("() => window.scrollTo({top: 0, behavior: 'smooth'})")
            pause(ms)

        @contextmanager
        def scene(sid):
            start = time.time()
            print(f"[{sid}] start")
            yield
            used = time.time() - start
            remain = DUR[sid] - used
            if remain < 0:
                print(f"  !! {sid} over by {-remain:.1f}s")
            else:
                pause(int(remain * 1000))
            markers[sid] = [start, start + DUR[sid]]

        # 같은 컨텍스트에서 차트 번들(Plotly)·API 문서를 미리 받아 둔다 (녹화 전, 캐시 확보)
        page.goto(f"{BASE}/trends", wait_until="networkidle", timeout=120000)
        page.wait_for_selector("text=Search index trend", timeout=60000)
        page.wait_for_timeout(2500)
        page.goto(f"{API}/docs", wait_until="networkidle", timeout=120000)
        page.wait_for_selector(".opblock-tag", timeout=60000)

        if not ADMIN_ONLY:
            # ---------------------------------------------------------------- 일반 회원
            page.goto(BASE, wait_until="networkidle", timeout=120000)
            page.wait_for_selector("text=NEW ARRIVALS", timeout=60000)
            pause(2500)
            page.mouse.move(960, 540)
            rec.start()
            pause(600)

            with scene("U01"):
                pause(700)
                topbar = page.get_by_text("트렌드 키워드 기반 큐레이션", exact=False).first
                move_to(topbar, 0.8)
                hl(topbar, 2600)
                pause(2900)
                hero = page.locator("section[aria-roledescription=carousel] h1").first
                move_to(hero, 0.8, dx=260)
                hl(hero, 2800)
                pause(3200)
                strip = page.get_by_text("실시간 트렌드", exact=True).first.locator("xpath=ancestor::section[1]")
                move_to(strip, 0.8, dx=420)
                hl(strip, 3000)

            with scene("U02"):
                scroll(780, 1500)
                new = page.get_by_role("heading", name="NEW ARRIVALS")
                hl(new.locator("xpath=ancestor::section[1]"), 2600)
                pause(3000)
                scroll(1250, 1700)
                pause(1200)
                scroll(1100, 1700)
                picks = page.get_by_role("heading", name="TREND PICKS").locator("xpath=ancestor::section[1]")
                card = picks.locator("a[href^='/products/']").first
                move_to(card, 0.8)
                hl(card, 2600)

            with scene("U03"):
                scroll_top(1300)
                click(page.locator("header nav a[href='/trends']").first)
                page.wait_for_selector("text=Search index trend", timeout=30000)
                pause(1800)
                scroll(560, 1400)
                chart = page.get_by_text("Search index trend", exact=True).locator("xpath=ancestor::section[1]")
                hl(chart, 2600)
                rest_beside(chart)
                pause(2400)
                scroll(640, 1400)
                surge = page.locator("table tr.bg-accent\\/5").first
                if surge.count():
                    move_to(surge, 0.8, dx=-200)
                    hl(surge, 2600)

            with scene("U04"):
                scroll_top(1000)
                click(page.locator("a[href='/login']").first)
                page.wait_for_selector("text=일반 회원 테스트 로그인", timeout=30000)
                pause(900)
                btns = page.get_by_text("일반 회원 테스트 로그인").locator("xpath=ancestor::div[contains(@class,'grid')][1]")
                hl(btns, 2600)
                pause(2600)
                click(page.get_by_text("일반 회원 테스트 로그인").first, wait=300)
                page.wait_for_url(BASE + "/", timeout=30000)
                page.wait_for_selector("text=NEW ARRIVALS", timeout=30000)
                pause(1200)

            with scene("U05"):
                click(page.locator("nav[aria-label='카테고리'] a", has_text="아우터").first)
                page.wait_for_selector("a[href^='/products/']", timeout=30000)
                pause(1200)
                click(page.get_by_role("radio", name="트렌드순"))
                pause(1500)
                first = page.locator("a[href^='/products/']").first
                hl(first, 3000)
                rest_beside(first)

            with scene("U06"):
                click(page.locator("a[href^='/products/']").first, wait=300)
                page.wait_for_selector("text=바로 구매하기", timeout=30000)
                pause(1600)
                swatches = page.locator("button[aria-pressed][title]")
                for i in (1, 2, 0):
                    if swatches.count() > i:
                        click(swatches.nth(i), 0.6, wait=1300)
                sizes = page.locator("button.min-w-14")
                if sizes.count():
                    click(sizes.nth(min(1, sizes.count() - 1)), 0.6, wait=900)
                click(page.get_by_label("수량 증가"), 0.6, wait=900)
                total = page.get_by_text("총 상품금액").first
                hl(total, 2400)
                rest_beside(total)

            with scene("U07"):
                click(page.get_by_role("button", name="바로 구매하기"))
                page.wait_for_selector("#co-phone", timeout=15000)
                pause(900)
                click(page.locator("#co-phone"), 0.6, wait=200)
                page.locator("#co-phone").press_sequentially("010-1234-5678", delay=70)
                pause(400)
                click(page.locator("#co-addr"), 0.6, wait=200)
                page.locator("#co-addr").press_sequentially("서울특별시 성동구 성수이로 100", delay=60)
                pause(600)
                submit = page.get_by_role("button", name="주문하기")
                hl(submit, 1600)
                pause(1700)
                click(submit, 0.5, wait=300)
                page.wait_for_selector("text=주문이 완료되었습니다", timeout=30000)
                pause(800)
                modal = page.get_by_role("dialog")
                hl(modal, 3000)
                rest_beside(modal)

            with scene("U08"):
                click(page.get_by_role("link", name="주문 내역 보기"))
                page.wait_for_selector("article ol", timeout=30000)
                pause(1500)
                steps = page.locator("article ol").first
                move_to(steps, 0.8, dy=40)
                hl(steps, 3200)
                pause(3600)
                art = page.locator("article").first
                hl(art, 2600)
                rest_beside(art)

            with scene("U09"):
                pause(800)
                page.evaluate("() => window.__addr('/admin', 3000)")
                pause(1400)
                page.evaluate("() => { history.pushState({}, '', '/admin'); dispatchEvent(new PopStateEvent('popstate')); }")
                pause(2600)
                hdr = page.locator("header").first
                hl(hdr, 3200)
                move(1500, 160, 0.8)

        else:
            page.goto(BASE, wait_until="networkidle", timeout=120000)
            page.wait_for_selector("text=NEW ARRIVALS", timeout=60000)
            pause(2500)
            page.mouse.move(960, 540)
            rec.start()
            pause(600)

        # ---------------------------------------------------------------- 테스트 관리자
        with scene("A01"):
            logout = page.get_by_role("button", name="로그아웃").first
            if logout.count():
                click(logout, wait=900)
            else:
                pause(2600)
            click(page.locator("a[href='/login']").first)
            page.wait_for_selector("text=테스트 관리자 로그인", timeout=30000)
            pause(700)
            click(page.get_by_text("테스트 관리자 로그인").first, wait=300)
            page.wait_for_url(BASE + "/", timeout=30000)
            pause(1200)
            admin_btn = page.locator("header a[href='/admin']").first
            move_to(admin_btn, 0.8)
            hl(admin_btn, 2200)
            pause(2300)
            click(admin_btn, 0.3, wait=300)
            page.wait_for_selector("text=ADMIN CONSOLE", timeout=30000)

        with scene("A02"):
            pause(900)
            banner = page.locator("[role=status]").first
            move_to(banner, 0.8, dx=300)
            hl(banner, 3200)
            pause(3600)
            scroll(760, 1500)
            recent = page.get_by_text("Recent orders", exact=True).locator("xpath=ancestor::section[1]")
            row = recent.locator("tbody tr").first
            move_to(row, 0.8, dx=-300)
            hl(row, 3200)
            rest_beside(row)

        with scene("A03"):
            scroll_top(900)
            click(page.locator("nav[aria-label='관리자 메뉴'] a", has_text="상품 소싱"))
            page.wait_for_selector("article", timeout=30000)
            pause(1800)
            card = page.locator("main article").first
            info = card.locator("div.grid").first
            move_to(info, 0.8)
            hl(info, 2600)
            pause(2900)
            reg = card.get_by_role("button", name="원클릭 등록")
            move_to(reg, 0.7)
            hl(reg, 2600)

        with scene("A04"):
            click(page.locator("nav[aria-label='관리자 메뉴'] a", has_text="주문·발주"))
            page.wait_for_selector("text=Order", timeout=30000)
            pause(900)
            click(page.get_by_role("button", name="발주서", exact=True))
            page.wait_for_selector("main article", timeout=30000)
            pause(1300)
            po = page.locator("main article").first
            hl(po, 2600)
            pause(2600)
            click(po.get_by_role("button", name="미리보기"), wait=300)
            page.get_by_role("dialog").get_by_text("발주번호").first.wait_for(timeout=30000)
            pause(3800)
            page.keyboard.press("Escape")
            pause(900)
            locked = page.locator("main article button:disabled").filter(has_text="발송").first
            if not locked.count():
                locked = page.locator("main article button:disabled").first
            move_to(locked, 0.7)
            hl(locked, 2600)

        with scene("A05"):
            scroll_top(800)
            click(page.locator("nav[aria-label='관리자 메뉴'] a", has_text="RPA 작업"))
            page.wait_for_selector("text=trend_collect", timeout=30000)
            pause(1500)
            job = page.locator("main article").first
            hl(job, 2600)
            pause(2700)
            run_btn = job.get_by_role("button", name="지금 실행")
            move_to(run_btn, 0.7)
            hl(run_btn, 2200)
            pause(2300)
            scroll(720, 1500)
            logs = page.locator("main table").first
            hl(logs, 2600)
            rest_beside(logs)

        with scene("A06"):
            scroll_top(800)
            click(page.locator("nav[aria-label='관리자 메뉴'] a", has_text="회원 권한"))
            page.wait_for_selector("main table", timeout=30000)
            pause(1500)
            toggle = page.locator("main table td div.inline-flex").first
            move_to(toggle, 0.8)
            hl(toggle, 2600)
            pause(2800)
            badge = page.get_by_text("테스트 관리자 · 읽기 전용", exact=True).first
            if badge.count():
                move_to(badge, 0.7)
                hl(badge, 2600)

        # ---------------------------------------------------------------- 운영 API 문서 (장면 전에 로딩)
        rec.stop()
        page.goto(f"{API}/docs", wait_until="networkidle", timeout=120000)
        page.wait_for_selector(".opblock-tag", timeout=60000)
        pause(2000)
        page.mouse.move(*rec.pos)
        rec.start()
        pause(500)
        with scene("A07"):
            pause(800)
            tags = page.locator(".opblock-tag")
            for name in ("auth", "shop"):
                t = tags.filter(has_text=name).first
                move_to(t, 0.8, dx=-300)
                hl(t.locator("xpath=ancestor::div[contains(@class,'opblock-tag-section')][1]"), 2600)
                pause(2900)
            scroll(1300, 1600)
            t = tags.filter(has_text="admin").first
            if t.count():
                move_to(t, 0.8, dx=-300)
                hl(t.locator("xpath=ancestor::div[contains(@class,'opblock-tag-section')][1]"), 2600)
        pause(800)
        rec.stop()
        ctx.close()
        browser.close()

    if ADMIN_ONLY:
        old_frames = json.loads((DEMO_DIR / "frames.json").read_text(encoding="utf-8"))
        old_markers = json.loads((DEMO_DIR / "markers.json").read_text(encoding="utf-8"))
        rec.frames = sorted(old_frames + rec.frames)
        markers = {**old_markers, **markers}
    save_json(DEMO_DIR / "frames.json", rec.frames)
    save_json(DEMO_DIR / "markers.json", markers)
    print(f"frames {len(rec.frames)}, scenes {len(markers)}")


if __name__ == "__main__":
    main()
