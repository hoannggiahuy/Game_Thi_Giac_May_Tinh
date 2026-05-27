"""
beatmap_tools.py - bản V6

Bản này chỉnh theo yêu cầu:
- Nốt nhạc KHÔNG tự xuất hiện ngẫu nhiên theo thời gian nữa.
- Nhịp mặc định cố định theo từng màn:
    Màn 1: 1.00 giây / nốt
    Màn 2: 0.75 giây / nốt
    Màn 3: 0.55 giây / nốt
- Nhạc vẫn được đọc từ assets/level1.mp3, level2.mp3, level3.mp3.
- Nếu muốn tự chỉnh beat thủ công chính xác hơn, vẫn có thể tạo beatmap_levelN.txt.
"""

from __future__ import annotations

import os
import wave
from typing import List, Optional, Tuple


LEVEL_INTERVALS = {
    1: 1.00,
    2: 0.75,
    3: 0.55,
}


def read_txt_beatmap(path: str) -> List[float]:
    """Đọc beatmap thủ công. Mỗi dòng là thời điểm giây."""
    beats: List[float] = []
    if not os.path.exists(path):
        return beats

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            raw = raw.replace(",", ".")
            try:
                value = float(raw)
            except ValueError:
                continue
            if value >= 0:
                beats.append(value)

    return sorted(set(round(x, 3) for x in beats))


def audio_duration(audio_path: Optional[str]) -> float:
    """Lấy thời lượng nhạc. MP3 cần mutagen hoặc librosa; nếu thiếu thì dùng 90 giây fallback."""
    if not audio_path or not os.path.exists(audio_path):
        return 110.0

    ext = os.path.splitext(audio_path)[1].lower()

    if ext == ".wav":
        try:
            with wave.open(audio_path, "rb") as wf:
                return wf.getnframes() / float(wf.getframerate())
        except Exception:
            return 110.0

    # Mutagen nhẹ hơn librosa và đọc mp3 tốt nếu máy có cài.
    try:
        from mutagen.mp3 import MP3  # type: ignore
        return float(MP3(audio_path).info.length)
    except Exception:
        pass

    try:
        import librosa  # type: ignore
        return float(librosa.get_duration(path=audio_path))
    except Exception:
        return 110.0


def generate_fixed_interval_beats(duration: float, level: int) -> List[float]:
    """Tạo nốt cách đều theo cấp độ màn."""
    interval = LEVEL_INTERVALS.get(level, 0.75)
    beats: List[float] = []

    # Chừa 1.25 giây đầu để nhạc vào, người chơi chuẩn bị.
    t = 1.25
    while t < duration:
        beats.append(round(t, 3))
        t += interval

    return beats


def get_level_audio_path(assets_dir: str, level: int) -> Optional[str]:
    for ext in ("mp3", "wav", "ogg"):
        path = os.path.join(assets_dir, f"level{level}.{ext}")
        if os.path.exists(path):
            return path
    return None


def get_menu_audio_path(assets_dir: str) -> Optional[str]:
    for ext in ("mp3", "wav", "ogg"):
        path = os.path.join(assets_dir, f"menu_theme.{ext}")
        if os.path.exists(path):
            return path
    return None


def load_or_generate_beats(assets_dir: str, level: int, fallback_duration: float = 110.0) -> Tuple[List[float], float, str]:
    """
    Ưu tiên:
    1) Nếu có beatmap_levelN.txt thì dùng beatmap đó.
    2) Nếu không có, sinh nốt theo khoảng cách cố định từng màn.
    """
    os.makedirs(assets_dir, exist_ok=True)

    audio_path = get_level_audio_path(assets_dir, level)
    duration = audio_duration(audio_path) if audio_path else fallback_duration

    txt_path = os.path.join(assets_dir, f"beatmap_level{level}.txt")
    txt_beats = read_txt_beatmap(txt_path)
    if txt_beats:
        return txt_beats, max(duration, max(txt_beats) + 2.0), "beatmap txt"

    interval = LEVEL_INTERVALS.get(level, 0.75)
    beats = generate_fixed_interval_beats(duration, level)
    return beats, duration, f"nhịp cố định {interval:.2f}s"
