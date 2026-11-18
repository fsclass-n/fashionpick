"""scenes.py 와 실제 합성 길이로 '영상 대본 및 연출 가이드' 문서를 만든다."""
from common import TTS_DIR, VIDEO, load_json
from scenes import CHAPTER, PRESENTER, SCENES, VOICE, timeline

SCREEN = {
    "U01": "메인 `/` — 유틸리티 바 → 룩북 히어로 → 실시간 트렌드 줄 강조",
    "U02": "메인 스크롤 — NEW ARRIVALS → LOOKBOOK → TREND PICKS 첫 카드",
    "U03": "GNB `TREND` 클릭 → `/trends` 검색 지수 차트 → 급상승 행 강조",
    "U04": "상단 `로그인` → 테스트 계정 버튼 강조 → `일반 회원 테스트 로그인`",
    "U05": "카테고리 바 `아우터` → 정렬 `트렌드순` → 첫 상품 카드 강조",
    "U06": "상품 상세 — 색상 3번 전환(이미지 변경) → 사이즈 → 수량 + → 총 상품금액",
    "U07": "`바로 구매하기` → 연락처·배송지 입력 → `주문하기` → 주문 완료 모달",
    "U08": "`주문 내역 보기` → `/mypage` 주문 진행 단계 강조",
    "U09": "주소 `/admin` 직접 이동(주소 표시 오버레이) → 메인으로 돌아옴 → 헤더 강조(ADMIN 없음)",
    "A01": "`로그아웃` → `로그인` → `테스트 관리자 로그인` → 헤더 `ADMIN` 강조 → 클릭",
    "A02": "`/admin` 읽기 전용 배너 강조 → 최근 주문 첫 행(방금 주문) 강조",
    "A03": "`상품 소싱` — 도매가·판매가·마진율 강조 → 잠긴 `원클릭 등록`",
    "A04": "`주문·발주` → `발주서` 탭 → 첫 발주서 → `미리보기` 모달 → 잠긴 발송 버튼",
    "A05": "`RPA 작업` — 작업 카드 → 잠긴 `지금 실행` → 실행 로그 표",
    "A06": "`회원 권한` — 비활성 권한 토글 → `테스트 관리자 · 읽기 전용` 배지",
    "C01": "권한 비교 카드 (일반 회원 · 테스트 관리자 · 실제 관리자)",
    "A07": "`fashionpick-api.onrender.com/docs` — auth · shop → admin API 묶음 강조",
}


def mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def main():
    timing = load_json(TTS_DIR / "timing.json", {})
    rows = []
    for sc, t0 in timeline():
        screen = f"슬라이드 {sc['slide']}" if sc["kind"] == "slide" else SCREEN.get(sc["id"], "")
        text = " ".join(sub for sub, _ in sc["lines"])
        length = timing.get(sc["id"], {}).get("length", 0)
        rows.append(f"| {mmss(t0)}–{mmss(t0 + sc['dur'])} | {sc['id']} | {CHAPTER[sc['chapter']]} | {screen} | {text} | "
                    f"{sc.get('tag', '')} | {length:.1f}s / {sc['dur']}s |")
    doc = f"""# fashionpick 10분 발표·시연 영상 — 대본 및 연출 가이드

> 자동 생성 문서입니다 (`docs/video/tools/gen_guide.py`). 대본 수정은 `docs/video/tools/scenes.py` 에서 합니다.

- 발표자: **{PRESENTER}** (백엔드 · RPA 파이프라인 · 데이터 분석) — 내레이션은 여성 신경망 합성 음성 `{VOICE}` (속도 −4%, 문장 사이 0.35초 쉼, −16 LUFS)
- 구성: PPT 1~15장(+10장 전환) → 운영 사이트 **일반 회원** 시연 → **테스트 관리자** 시연 → 권한 비교 → 운영 API 문서 → PPT 16·17장 클로징
- 시연 대상: 실제 운영 서비스 `https://fashionpick.onrender.com` (일반 회원 테스트 계정으로 주문 1건 생성, 테스트 관리자는 읽기 전용이라 데이터 변경 없음)
- 연출: 노란 원형 커서·클릭 링, 시안 테두리 강조(0.3초 페이드), 구간 라벨(슬라이드 위쪽 가운데·시연 왼쪽 아래), 노란 안내 태그, 하단 자막

| 시간 | 장면 | 구간 | 화면 · 동작 | 대본 | 안내 태그 | 음성 / 장면 |
|---|---|---|---|---|---|---|
""" + "\n".join(rows) + """

## 다시 만들기

```bash
cd docs/video/tools
python tts.py                 # 내레이션 (장면별 wav + timing.json)
powershell -File export_slides.ps1   # 슬라이드 PNG
python record_demo.py         # 운영 사이트 시연 녹화 (일반 회원 구간에서 주문 1건 생성)
python record_demo.py --admin-only   # 관리자 구간만 다시 녹화
python compose.py --rebuild   # 클립 → 이어 붙이기 → 음성·자막 → 2-pass 인코딩 → 하이라이트·썸네일·SRT
python check_final.py         # 사양 · 장면별 음량 · 깜박임 · 주요 프레임
python gen_guide.py           # 이 문서
```

## 실제 사람 목소리로 바꾸려면

장면별로 녹음해 `docs/video/build/tts/<장면ID>.wav` (48kHz 스테레오, 장면 시간보다 0.9초 이상 짧게)로 덮어쓰고 `compose.py` 만 다시 실행합니다.
"""
    (VIDEO / "영상_대본_및_연출가이드.md").write_text(doc, encoding="utf-8")
    print("written", len(rows), "scenes")


if __name__ == "__main__":
    main()
