"""영상 제작 도구 공통 설정: 경로, ffmpeg 위치, 실행 헬퍼."""
import glob
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIDEO = ROOT / "docs" / "video"
BUILD = VIDEO / "build"
TTS_DIR = BUILD / "tts"
SLIDES_DIR = BUILD / "slides"
DEMO_DIR = BUILD / "demo"
CLIPS_DIR = BUILD / "clips"
CARDS_DIR = VIDEO / "tools" / "cards"
PPTX = ROOT / "docs" / "fashionpick_발표자료.pptx"
FINAL = VIDEO / "3조_final.mp4"
HIGHLIGHT = VIDEO / "3조_highlight.mp4"
SRT = VIDEO / "3조_final.srt"
THUMB = VIDEO / "video-thumbnail.png"
W, H, FPS = 1920, 1080, 30
FONT = "C:/Windows/Fonts/malgun.ttf"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"

for d in (BUILD, TTS_DIR, SLIDES_DIR, DEMO_DIR, CLIPS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _find(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    hits = glob.glob(os.path.expandvars(rf"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\{name}.exe"))
    if not hits:
        raise SystemExit(f"{name} 를 찾을 수 없습니다. (winget install Gyan.FFmpeg)")
    return hits[0]


FFMPEG, FFPROBE = _find("ffmpeg"), _find("ffprobe")


def run(args: list, cwd=None, quiet=True) -> subprocess.CompletedProcess:
    cmd = [FFMPEG if args[0] == "ffmpeg" else FFPROBE if args[0] == "ffprobe" else args[0], *map(str, args[1:])]
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(map(str, cmd))[:400]}\n{res.stderr[-2000:]}")
    return res


def duration(path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path]).stdout
    return float(json.loads(out)["format"]["duration"])


def load_json(path, default=None):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
