"""장면별 내레이션 합성 (여성 신경망 음성 ko-KR-SunHiNeural).

사람처럼 들리게
- 문장마다 따로 합성하고 문장 사이에 0.35초 숨 쉬는 쉼을 넣는다
- 기본보다 5% 느리게, 톤은 1Hz 낮게 → 장면 시간을 넘으면 속도를 단계적으로 올린다
- 목소리 보정: 80Hz 이하 제거, 부드러운 압축, 3kHz 명료도 보강, -16 LUFS

출력: build/tts/<장면ID>.wav (48kHz 스테레오) + build/tts/timing.json (문장별 시작·길이)
"""
import asyncio
import os
import sys

import edge_tts

from common import TTS_DIR, duration, load_json, run, save_json
from scenes import SCENES, VOICE

PAUSE = 0.35
RATES = ["-4%", "-2%", "+0%", "+3%"]  # 자연스러운 범위 안에서만 조정
VOICE_FILTER = ("highpass=f=80,"
                "acompressor=threshold=-20dB:ratio=2.2:attack=8:release=120:makeup=1.5,"
                "equalizer=f=3000:t=q:w=1.2:g=2.5,"
                "equalizer=f=200:t=q:w=1.0:g=-1.5,"
                "loudnorm=I=-16:TP=-1.5:LRA=9")


async def synth(text: str, out, rate: str):
    await edge_tts.Communicate(text, VOICE, rate=rate, pitch="-1Hz").save(str(out))


def build_scene(scene: dict, force=False) -> dict:
    sid, budget = scene["id"], (999 if os.getenv("TTS_MEASURE") else scene["dur"] - 0.9)
    wav = TTS_DIR / f"{sid}.wav"
    timing = load_json(TTS_DIR / "timing.json", {})
    if wav.exists() and sid in timing and not force:
        return timing[sid]
    for rate in RATES:
        parts, cursor = [], 0.0
        for i, (sub, spoken) in enumerate(scene["lines"]):
            mp3 = TTS_DIR / f"{sid}_{i}.mp3"
            asyncio.run(synth(spoken or sub, mp3, rate))
            d = duration(mp3)
            parts.append({"text": sub, "start": round(cursor, 3), "dur": round(d, 3), "file": mp3.name})
            cursor += d + PAUSE
        total = cursor - PAUSE
        if total <= budget:
            break
    else:
        print(f"!! {sid}: {total:.1f}s > budget {budget:.1f}s even at fastest rate", file=sys.stderr)

    # 문장 + 쉼을 이어 붙이고 보정
    inputs, labels = [], []
    for i, p in enumerate(parts):
        inputs += ["-i", TTS_DIR / p["file"]]
        labels.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,apad=pad_dur={PAUSE if i < len(parts) - 1 else 0}[a{i}]")
    concat = "".join(f"[a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[c]"
    flt = ";".join(labels + [concat, f"[c]{VOICE_FILTER},aresample=48000,aformat=channel_layouts=stereo[out]"])
    run(["ffmpeg", "-y", *inputs, "-filter_complex", flt, "-map", "[out]", "-ar", 48000, "-ac", 2, wav])
    real = duration(wav)
    scale = real / total if total else 1.0  # loudnorm 등으로 생기는 미세한 길이 차이 보정
    for p in parts:
        p["start"], p["dur"] = round(p["start"] * scale, 3), round(p["dur"] * scale, 3)
    info = {"rate": rate, "length": round(real, 3), "budget": budget, "parts": parts}
    timing[sid] = info
    save_json(TTS_DIR / "timing.json", timing)
    return info


if __name__ == "__main__":
    only = set(sys.argv[1:]) - {"--force"}
    force = "--force" in sys.argv
    for sc in SCENES:
        if only and sc["id"] not in only:
            continue
        info = build_scene(sc, force=force or bool(only))
        flag = "" if info["length"] <= info["budget"] else "  <-- OVER"
        print(f"{sc['id']}  {info['length']:5.1f}s / {sc['dur']:3d}s  rate {info['rate']}{flag}")
