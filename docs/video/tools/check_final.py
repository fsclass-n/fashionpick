"""최종 영상 검사: 스트림 사양 · 길이 · 장면별 내레이션 음량 · 깜박임 · 주요 프레임."""
import json
import re

from common import BUILD, FINAL, HIGHLIGHT, run
from scenes import SCENES, timeline


def streams():
    info = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", FINAL]).stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next(s for s in info["streams"] if s["codec_type"] == "audio")
    size = int(info["format"]["size"]) / 1024 / 1024
    print(f"video {v['codec_name']} {v['profile']} {v['width']}x{v['height']} {v['r_frame_rate']} frames={v.get('nb_frames')}")
    print(f"audio {a['codec_name']} {a['sample_rate']}Hz ch={a['channels']} lang={a.get('tags', {}).get('language')}")
    print(f"duration {float(info['format']['duration']):.2f}s size {size:.1f}MiB (limit 95)  highlight {HIGHLIGHT.stat().st_size / 1024 / 1024:.1f}MiB (limit 10)")
    return size <= 95


def scene_volumes():
    bad = []
    for sc, t0 in timeline():
        err = run(["ffmpeg", "-v", "info", "-ss", t0 + 0.3, "-t", sc["dur"] - 0.6, "-i", FINAL, "-vn", "-af", "volumedetect", "-f", "null", "-"]).stderr
        mean = float(re.search(r"mean_volume: (-?[\d.]+)", err).group(1))
        if mean < -35:
            bad.append((sc["id"], mean))
    print("scene volume:", "all scenes > -35dB" if not bad else f"QUIET {bad}")
    return not bad


def flicker():
    """한 프레임만 튀는 번쩍임(앞뒤와 반대 방향으로 ±4 이상) 검사. 페이드·슬라이드 전환은 제외."""
    out = run(["ffmpeg", "-v", "error", "-i", FINAL, "-vf", "scale=320:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
               "-an", "-f", "null", "-"]).stdout
    y = [float(m) for m in re.findall(r"YAVG=([\d.]+)", out)]
    spikes = [i for i in range(1, len(y) - 1) if (y[i] - y[i - 1]) * (y[i] - y[i + 1]) > 0 and min(abs(y[i] - y[i - 1]), abs(y[i] - y[i + 1])) >= 4]
    print(f"frames {len(y)}, single-frame flashes: {len(spikes)}", [f"{i / 30:.2f}s" for i in spikes[:10]])
    return not spikes


def key_frames():
    d = BUILD / "keyframes"
    d.mkdir(exist_ok=True)
    for sc, t0 in timeline():
        run(["ffmpeg", "-y", "-v", "error", "-ss", t0 + sc["dur"] * 0.6, "-i", FINAL, "-frames:v", 1, "-vf", "scale=640:-2", d / f"{sc['id']}.png"])
    print("key frames ->", d)


if __name__ == "__main__":
    ok = [streams(), scene_volumes(), flicker()]
    key_frames()
    print("TOTAL scenes", len(SCENES), "PASS" if all(ok) else "CHECK FAILED")
