"""장면 클립 생성 → 이어 붙이기 → 내레이션·자막 → 2-pass 인코딩 → 하이라이트·썸네일·SRT.

python compose.py            # 전체 (클립이 있으면 재사용)
python compose.py --rebuild  # 클립 다시 만들기
"""
import bisect
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import (BUILD, CARDS_DIR, CLIPS_DIR, DEMO_DIR, FINAL, FONT, FONT_BOLD, FPS, H, HIGHLIGHT, SLIDES_DIR, SRT,
                    THUMB, TTS_DIR, W, duration, load_json, run)
from scenes import CHAPTER, SCENES, timeline

PX = W / 13.333  # 슬라이드 인치 → 픽셀
NARR_DELAY = 0.3
WORK = BUILD / "work"
WORK.mkdir(exist_ok=True)


# ---------------------------------------------------------------- 이미지 준비
def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def highlight_image(src: Path, rect, out: Path):
    im = Image.open(src).convert("RGBA").resize((W, H))
    x, y, w, h = (v * PX for v in rect)
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((x - 10, y - 10, x + w + 10, y + h + 10), radius=18, outline=(34, 211, 238, 150), width=10)
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(im).rounded_rectangle((x - 8, y - 8, x + w + 8, y + h + 8), radius=16, outline=(34, 211, 238, 255), width=4)
    im.convert("RGB").save(out)


def pill(draw, x, y, text, fill, color, size=24, bold=True, pad=(18, 9)):
    f = font(size, bold)
    bw = draw.textlength(text, font=f)
    box = (x, y, x + bw + pad[0] * 2, y + size + pad[1] * 2 + 4)
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=fill)
    draw.text((x + pad[0], y + pad[1] - 1), text, font=f, fill=color)
    return box[2]


def overlay_image(scene, out: Path):
    """구간 라벨(+노란 안내 태그). 슬라이드는 위쪽 가운데, 시연 화면은 왼쪽 아래."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    label = CHAPTER[scene["chapter"]]
    if scene["kind"] == "slide":
        f = font(22, True)
        tw = d.textlength(label, font=f) + 36
        pill(d, (W - tw) / 2, 14, label, (17, 17, 17, 215), (244, 239, 230, 255), size=22)
    else:
        x = pill(d, 26, H - 74, label, (17, 17, 17, 225), (244, 239, 230, 255), size=24)
        if scene.get("tag"):
            pill(d, x + 10, H - 74, scene["tag"], (255, 214, 64, 245), (17, 17, 17, 255), size=24)
    im.save(out)


def render_card(sid: str, out: Path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto((CARDS_DIR / f"{sid}.html").as_uri())
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(out))
        b.close()


# ---------------------------------------------------------------- 자막
def wrap(text, limit=26):
    words, lines, cur = text.split(" "), [], ""
    for w_ in words:
        if cur and len(cur) + 1 + len(w_) > limit:
            lines.append(cur)
            cur = w_
        else:
            cur = f"{cur} {w_}".strip()
    if cur:
        lines.append(cur)
    return lines


def sub_style(scene):
    """슬라이드: 본문을 가리지 않도록 맨 아래 한 줄 / 시연: 두 줄."""
    return (44, 1, 34, 10) if scene["kind"] == "slide" else (28, 2, 40, 110)  # 줄 길이, 최대 줄 수, 글자 크기, 아래 여백


def subtitle_events(scene, timing):
    """문장별 타이밍 → (시작, 끝, 텍스트) 목록 (장면 기준 초)."""
    limit, max_lines, _, _ = sub_style(scene)
    events = []
    for part in timing["parts"]:
        lines = wrap(part["text"], limit)
        chunks = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]
        total = sum(len("".join(c)) for c in chunks)
        t = part["start"] + NARR_DELAY
        for c in chunks:
            d = part["dur"] * len("".join(c)) / total
            events.append((t, t + d, "\\N".join(c)))
            t += d
    # 다음 자막 직전까지 살짝 유지해 깜박임을 줄인다
    out = []
    for i, (a, b, txt) in enumerate(events):
        nxt = events[i + 1][0] if i + 1 < len(events) else scene["dur"] - 0.2
        out.append((a, min(max(b, a + 0.8), nxt - 0.05, scene["dur"] - 0.1), txt))
    return out


def ass_time(t):
    t = max(0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def write_ass(events, path: Path, size, margin_v):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Malgun Gothic,{size},&H00FFFFFF,&H00FFFFFF,&H5A141414,&H5A141414,1,0,0,0,100,100,0,0,3,14,0,2,160,160,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Sub,,0,0,0,,{t}\n" for a, b, t in events)
    path.write_text(head + body, encoding="utf-8-sig")


# ---------------------------------------------------------------- 장면 클립
def demo_concat(sid, list_path: Path):
    frames = load_json(DEMO_DIR / "frames.json")
    a, b = load_json(DEMO_DIR / "markers.json")[sid]
    ts = [f[0] for f in frames]
    i = max(0, bisect.bisect_right(ts, a) - 1)
    lines, last = [], None
    while i < len(frames) and ts[i] < b:
        s = max(ts[i], a)
        e = min(ts[i + 1] if i + 1 < len(frames) else b, b)
        if e > s:
            path = (DEMO_DIR / "frames" / frames[i][1]).as_posix()
            lines += [f"file '{path}'", f"duration {e - s:.4f}"]
            last = path
        i += 1
    lines.append(f"file '{last}'")
    list_path.write_text("\n".join(lines), encoding="utf-8")


def build_clip(scene, timing, out: Path):
    sid, dur = scene["id"], scene["dur"]
    n = dur * FPS
    wd = WORK / sid
    wd.mkdir(exist_ok=True)
    shutil.copy(FONT, wd / "malgun.ttf")
    shutil.copy(FONT_BOLD, wd / "malgunbd.ttf")
    overlay_image(scene, wd / "overlay.png")
    _, _, size, margin = sub_style(scene)
    write_ass(subtitle_events(scene, timing), wd / "sub.ass", size, margin)

    enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", FPS, "-frames:v", n, "-an"]
    tail = f"[ov]overlay=0:0:format=auto,subtitles=sub.ass:fontsdir=.,fps={FPS},format=yuv420p,tpad=stop_mode=clone:stop_duration=2[v]"
    if scene["kind"] == "slide":
        plain = SLIDES_DIR / f"slide{scene['slide']:02d}.png"
        hl = wd / "hl.png"
        highlight_image(plain, scene["hl"], hl) if scene.get("hl") else shutil.copy(plain, hl)
        inputs = ["-loop", 1, "-t", dur + 1, "-i", plain, "-loop", 1, "-t", dur + 1, "-i", hl, "-loop", 1, "-t", dur + 1, "-i", "overlay.png"]
        flt = (f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p[a];[1:v]scale={W}:{H},fps={FPS},format=yuv420p[b];"
               f"[a][b]xfade=transition=fade:duration=0.3:offset=1.4[s];[s][2:v]overlay=0:0[ov];" + tail.replace("[ov]overlay=0:0:format=auto,", "[ov]"))
    elif scene["kind"] == "card":
        img = wd / "card.png"
        render_card(sid, img)
        inputs = ["-loop", 1, "-t", dur + 1, "-i", img, "-loop", 1, "-t", dur + 1, "-i", "overlay.png"]
        flt = f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p[s];[s][1:v]overlay=0:0[ov];" + tail.replace("[ov]overlay=0:0:format=auto,", "[ov]")
    else:
        demo_concat(sid, wd / "list.txt")
        inputs = ["-f", "concat", "-safe", 0, "-i", "list.txt", "-loop", 1, "-t", dur + 1, "-i", "overlay.png"]
        flt = f"[0:v]scale={W}:{H}:flags=lanczos,fps={FPS},format=yuv420p,setsar=1[s];[s][1:v]overlay=0:0[ov];" + tail.replace("[ov]overlay=0:0:format=auto,", "[ov]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", flt, "-map", "[v]", *enc, out.resolve()], cwd=wd)


# ---------------------------------------------------------------- 오디오 · SRT
def build_audio(out: Path, total: int):
    inputs, parts = [], []
    for k, (sc, t0) in enumerate(timeline()):
        inputs += ["-i", TTS_DIR / f"{sc['id']}.wav"]
        ms = int((t0 + NARR_DELAY) * 1000)
        parts.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{k}]")
    mix = "".join(f"[a{k}]" for k in range(len(parts))) + f"amix=inputs={len(parts)}:normalize=0:dropout_transition=0,apad,atrim=0:{total}[out]"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(parts + [mix]), "-map", "[out]", "-ar", 48000, "-ac", 2, "-c:a", "pcm_s16le", out])


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


def build_srt(timings):
    rows, k = [], 1
    for sc, t0 in timeline():
        for a, b, txt in subtitle_events(sc, timings[sc["id"]]):
            rows.append(f"{k}\n{srt_time(t0 + a)} --> {srt_time(t0 + b)}\n{txt.replace(chr(92) + 'N', chr(10))}\n")
            k += 1
    SRT.write_text("\n".join(rows), encoding="utf-8-sig")
    return k - 1


def main():
    rebuild = "--rebuild" in sys.argv
    timings = load_json(TTS_DIR / "timing.json")
    total = sum(s["dur"] for s in SCENES)
    clips = []
    for sc, _ in timeline():
        out = CLIPS_DIR / f"{sc['id']}.mp4"
        if rebuild or not out.exists():
            print("clip", sc["id"])
            build_clip(sc, timings[sc["id"]], out)
        clips.append(out)

    (WORK / "concat.txt").write_text("\n".join(f"file '{c.resolve().as_posix()}'" for c in clips), encoding="utf-8")
    master = BUILD / "master_video.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", 0, "-i", WORK / "concat.txt", "-c", "copy", master])
    audio = BUILD / "narration.wav"
    build_audio(audio, total)

    # 시작 페이드 인 / 끝 페이드 아웃 (0.6s) + 2-pass 인코딩 (≤95MB)
    vf = f"fade=t=in:st=0:d=0.6,fade=t=out:st={total - 1.2}:d=1.2,format=yuv420p"
    x264 = ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-r", FPS, "-fps_mode", "cfr", "-b:v", "1150k",
            "-maxrate", "3000k", "-bufsize", "6000k", "-x264-params", "keyint=150:min-keyint=30", "-vf", vf]
    passlog = (WORK / "x264pass").as_posix()
    run(["ffmpeg", "-y", "-i", master, *x264, "-pass", 1, "-passlogfile", passlog, "-an", "-f", "mp4", "NUL"])
    run(["ffmpeg", "-y", "-i", master, "-i", audio, *x264, "-pass", 2, "-passlogfile", passlog,
         "-af", f"afade=t=out:st={total - 1.2}:d=1.2", "-c:a", "aac", "-b:a", "160k", "-ar", 48000, "-ac", 2,
         "-metadata:s:a:0", "language=kor", "-metadata", "title=fashionpick 발표·시연 (김모란)",
         "-map", "0:v", "-map", "1:a", "-t", total, "-movflags", "+faststart", FINAL])
    n = build_srt(timings)

    starts = {sc["id"]: t for sc, t in timeline()}
    hs = starts["U06"]
    run(["ffmpeg", "-y", "-ss", hs, "-t", 60, "-i", FINAL, "-vf", "scale=1280:-2", "-c:v", "libx264", "-b:v", "1000k",
         "-maxrate", "2000k", "-bufsize", "4000k", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", HIGHLIGHT])
    shutil.copy(SLIDES_DIR / "slide01.png", THUMB)  # 썸네일 = 표지 슬라이드
    print(f"final {duration(FINAL):.2f}s {FINAL.stat().st_size / 1e6:.1f}MB, highlight {HIGHLIGHT.stat().st_size / 1e6:.1f}MB, srt {n} cues")


if __name__ == "__main__":
    main()
