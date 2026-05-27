"""
TIẾNG TRỐNG MÊ LINH - PYGAME FULL CINEMATIC VERSION
======================================================

Bản này chuyển phần hiển thị sang Pygame để đẹp hơn OpenCV:
- Menu cinematic bằng chuột.
- Cốt truyện mở đầu.
- Chọn màn kiểu card game.
- Cutscene chuyển cảnh.
- Battle 3 lane, 2 thành, lính que indie art.
- Khói, lửa, bụi, tia chém, rung màn hình.
- Màn 2: giơ 5 ngón tay gọi viện trợ.
- Màn 3: nắm tay gọi Đại Tướng Mê Linh.
- Boss Đông Hán.
- V8: sửa lỗi MediaPipe không có attribute solutions, mở camera ổn định hơn trên Windows.

Cài thư viện:
    pip install pygame opencv-python mediapipe numpy

Tuỳ chọn để tự bắt beat tốt hơn từ MP3/WAV:
    pip install librosa soundfile

Chạy:
    python game_melinh_pygame_full.py
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None

from beatmap_tools import get_level_audio_path, get_menu_audio_path, load_or_generate_beats
from skill_system_pygame import HandGestureTracker, HandState, SkillManager

# =========================
# 0. CẤU HÌNH CHUNG
# =========================

WIDTH, HEIGHT = 1280, 720
FPS = 60
ASSETS_DIR = "assets"
SAVE_PATH = "save_melinh.json"

# Âm lượng tổng. Có thể chỉnh ở đây nếu nhạc quá to/nhỏ.
MENU_VOLUME = 0.32
GAME_VOLUME = 0.46
SFX_VOLUME = 0.60

# V7: làm trận chậm hơn một chút.
# Scale này chỉ ảnh hưởng di chuyển / spawn / combat, không làm sai nhạc.
BATTLE_TIME_SCALE = 0.78

# V7: không cho mỗi nốt đúng đẻ lính ngay lập tức nữa.
# Mỗi nốt đúng vẫn tăng combo, nhưng lính thường sẽ xếp hàng ra trận theo cooldown
# để không bị tràn quân và kết thúc màn quá sớm.
ALLY_SPAWN_COOLDOWN = {1: 1.30, 2: 1.10, 3: 0.95}
ALLY_MAX_PER_LANE = {1: 4, 2: 5, 3: 6}
ALLY_MAX_TOTAL = {1: 12, 2: 16, 3: 20}
ALLY_QUEUE_MAX = {1: 5, 2: 7, 3: 9}

# Vị trí nốt nhạc cố định theo vòng lặp, không random.
# Mỗi màn sẽ đi tuần tự qua các điểm này để người chơi thấy có nhịp rõ ràng hơn.
NOTE_PATTERNS = {
    1: [(520, 250), (640, 250), (760, 250), (640, 360), (520, 475), (760, 475)],
    2: [(500, 230), (640, 230), (780, 230), (500, 360), (780, 360), (500, 500), (640, 500), (780, 500)],
    3: [(470, 210), (590, 210), (710, 210), (830, 210), (500, 350), (640, 350), (780, 350), (470, 520), (590, 520), (710, 520), (830, 520)],
}

LANE_Y = [310, 435, 560]
LANE_NAMES = ["Đường trên", "Đường giữa", "Đường dưới"]
LEFT_CASTLE_X = 118
RIGHT_CASTLE_X = 1162
LEFT_GATE_X = 215
RIGHT_GATE_X = 1065
GROUND_TOP = 250

WHITE = (245, 238, 220)
BLACK = (12, 12, 16)
GOLD = (240, 196, 82)
DARK_GOLD = (158, 102, 31)
RED = (205, 56, 48)
DARK_RED = (115, 31, 35)
GREEN = (74, 184, 106)
CYAN = (86, 201, 214)
BLUE = (66, 118, 192)
PURPLE = (147, 88, 191)
BROWN = (92, 58, 35)
DARK_BROWN = (51, 34, 24)
PAPER = (234, 215, 170)
PAPER_DARK = (155, 105, 54)
SKY_TOP = (20, 26, 45)
SKY_BOTTOM = (118, 54, 43)


# =========================
# 1. TIỆN ÍCH VẼ / FONT
# =========================

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    # Ưu tiên font Windows có tiếng Việt, fallback sang DejaVu.
    candidates = ["Segoe UI", "Arial", "Tahoma", "DejaVu Sans", "Liberation Sans"]
    for name in candidates:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)


pygame.init()
try:
    pygame.mixer.init()
    MIXER_OK = True
except Exception:
    MIXER_OK = False

FONT_XS = load_font(16)
FONT_SM = load_font(20)
FONT_MD = load_font(26)
FONT_LG = load_font(34, bold=True)
FONT_XL = load_font(52, bold=True)
FONT_TITLE = load_font(72, bold=True)


def text_surface(text: str, font: pygame.font.Font, color: Tuple[int, int, int], alpha: int = 255) -> pygame.Surface:
    surf = font.render(text, True, color)
    if alpha < 255:
        surf = surf.convert_alpha()
        surf.set_alpha(alpha)
    return surf


def draw_text(
    surf: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: Tuple[int, int, int],
    pos: Tuple[int, int],
    center: bool = False,
    alpha: int = 255,
) -> pygame.Rect:
    img = text_surface(text, font, color, alpha)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surf.blit(img, rect)
    return rect


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        test = word if not current else current + " " + word
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_panel(surface: pygame.Surface, rect: pygame.Rect, alpha: int = 210, border: Tuple[int, int, int] = GOLD) -> None:
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (22, 20, 24, alpha), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (*border, min(255, alpha + 30)), panel.get_rect(), 2, border_radius=18)
    surface.blit(panel, rect.topleft)


def draw_gradient_background(surface: pygame.Surface, top: Tuple[int, int, int] = SKY_TOP, bottom: Tuple[int, int, int] = SKY_BOTTOM) -> None:
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = lerp_color(top, bottom, t)
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))


def draw_indie_castle(surface: pygame.Surface, x: int, side: str, hp_ratio: float, level: int, shake: Tuple[int, int] = (0, 0)) -> None:
    """Vẽ tòa thành bằng shape, không cần ảnh ngoài."""
    sx, sy = shake
    base_y = 615
    wall_w = 185
    wall_h = 230
    color = (120, 82, 60) if side == "left" else (95, 76, 79)
    edge = (52, 35, 30)
    banner = RED if side == "left" else (62, 70, 116)
    direction = 1 if side == "left" else -1

    cx = x + sx
    # Bóng
    pygame.draw.ellipse(surface, (10, 10, 10, 80), (cx - 120, base_y - 10 + sy, 240, 38))

    main = pygame.Rect(cx - wall_w // 2, base_y - wall_h + sy, wall_w, wall_h)
    pygame.draw.rect(surface, color, main, border_radius=8)
    pygame.draw.rect(surface, edge, main, 4, border_radius=8)

    # Tháp hai bên
    for tx in [main.left + 28, main.right - 28]:
        tower = pygame.Rect(tx - 34, base_y - wall_h - 42 + sy, 68, wall_h + 42)
        pygame.draw.rect(surface, tuple(max(0, c - 15) for c in color), tower, border_radius=7)
        pygame.draw.rect(surface, edge, tower, 4, border_radius=7)
        # Mái
        roof = [(tx - 42, tower.top), (tx, tower.top - 52), (tx + 42, tower.top)]
        pygame.draw.polygon(surface, DARK_RED if side == "left" else (40, 45, 76), roof)
        pygame.draw.polygon(surface, edge, roof, 3)

    # Răng cưa
    block_w = 24
    for i in range(6):
        bx = main.left + 10 + i * 31
        by = main.top - 20
        pygame.draw.rect(surface, color, (bx, by, block_w, 28))
        pygame.draw.rect(surface, edge, (bx, by, block_w, 28), 2)

    # Cổng
    gate = pygame.Rect(cx - 38, base_y - 85 + sy, 76, 85)
    pygame.draw.rect(surface, (42, 30, 25), gate, border_top_left_radius=40, border_top_right_radius=40)
    pygame.draw.arc(surface, GOLD, gate.inflate(8, 8), math.pi, 2 * math.pi, 3)

    # Cờ
    pole_x = cx + direction * 50
    pole_top = main.top - 110
    pygame.draw.line(surface, DARK_BROWN, (pole_x, main.top - 18 + sy), (pole_x, pole_top + sy), 5)
    flag = [(pole_x, pole_top + sy), (pole_x + direction * 92, pole_top + 22 + sy), (pole_x, pole_top + 48 + sy)]
    pygame.draw.polygon(surface, banner, flag)
    pygame.draw.polygon(surface, GOLD if side == "left" else (180, 180, 210), flag, 2)

    # Nâng cấp hình theo level
    if level >= 2:
        for off in [-58, 58]:
            pygame.draw.circle(surface, GOLD if side == "left" else CYAN, (cx + off, main.top + 60 + sy), 10, 2)
    if level >= 3:
        pygame.draw.line(surface, GOLD, (main.left + 12, main.top + 28), (main.right - 12, main.top + 28), 3)
        pygame.draw.line(surface, GOLD, (main.left + 18, main.top + 82), (main.right - 18, main.top + 82), 2)

    # HP bar ngay trên thành
    bar_w, bar_h = 190, 16
    bx, by = cx - bar_w // 2, main.top - 48 + sy
    pygame.draw.rect(surface, (45, 22, 22), (bx, by, bar_w, bar_h), border_radius=7)
    hp_color = GREEN if hp_ratio > 0.45 else GOLD if hp_ratio > 0.22 else RED
    pygame.draw.rect(surface, hp_color, (bx, by, int(bar_w * clamp(hp_ratio, 0, 1)), bar_h), border_radius=7)
    pygame.draw.rect(surface, WHITE, (bx, by, bar_w, bar_h), 1, border_radius=7)


# =========================
# 2. PARTICLE / EFFECT
# =========================

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: Tuple[int, int, int]
    radius: float
    gravity: float = 0.0
    kind: str = "circle"

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, offset: Tuple[int, int] = (0, 0)) -> None:
        if self.life <= 0:
            return
        alpha = int(255 * clamp(self.life / self.max_life, 0, 1))
        r = max(1, int(self.radius * (0.5 + self.life / self.max_life)))
        temp = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        color = (*self.color, alpha)
        if self.kind == "smoke":
            pygame.draw.circle(temp, (*self.color, int(alpha * 0.42)), (r * 2, r * 2), r * 2)
        elif self.kind == "spark":
            pygame.draw.line(temp, color, (r, r * 2), (r * 3, r * 2), max(1, r // 2))
        else:
            pygame.draw.circle(temp, color, (r * 2, r * 2), r)
        surface.blit(temp, (self.x + offset[0] - r * 2, self.y + offset[1] - r * 2))


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def spawn_smoke(self, x: float, y: float, count: int = 8) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x + random.uniform(-18, 18),
                    y + random.uniform(-8, 8),
                    random.uniform(-22, 22),
                    random.uniform(-60, -15),
                    random.uniform(0.65, 1.4),
                    1.4,
                    random.choice([(92, 82, 78), (118, 110, 98), (70, 68, 74)]),
                    random.uniform(6, 16),
                    gravity=-5,
                    kind="smoke",
                )
            )

    def spawn_fire(self, x: float, y: float, count: int = 10) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x + random.uniform(-18, 18),
                    y + random.uniform(-5, 10),
                    random.uniform(-18, 18),
                    random.uniform(-80, -25),
                    random.uniform(0.35, 0.8),
                    0.8,
                    random.choice([(255, 96, 39), (255, 171, 48), (212, 47, 40)]),
                    random.uniform(3, 9),
                    gravity=-20,
                    kind="circle",
                )
            )

    def spawn_slash(self, x: float, y: float, direction: int, color: Tuple[int, int, int] = GOLD) -> None:
        for _ in range(8):
            self.particles.append(
                Particle(
                    x + random.uniform(-8, 8),
                    y + random.uniform(-18, 10),
                    random.uniform(40, 180) * direction,
                    random.uniform(-70, 30),
                    random.uniform(0.15, 0.35),
                    0.35,
                    color,
                    random.uniform(2, 4),
                    gravity=80,
                    kind="spark",
                )
            )

    def spawn_dust(self, x: float, y: float, count: int = 6) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x + random.uniform(-20, 20),
                    y + random.uniform(-5, 10),
                    random.uniform(-55, 55),
                    random.uniform(-40, -10),
                    random.uniform(0.3, 0.7),
                    0.7,
                    random.choice([(147, 105, 63), (116, 84, 55), (186, 146, 84)]),
                    random.uniform(3, 8),
                    gravity=120,
                    kind="smoke",
                )
            )

    def update(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface: pygame.Surface, offset: Tuple[int, int] = (0, 0)) -> None:
        for p in self.particles:
            p.draw(surface, offset)


class CameraShake:
    def __init__(self):
        self.time_left = 0.0
        self.power = 0.0

    def trigger(self, power: float = 8.0, duration: float = 0.25) -> None:
        self.time_left = max(self.time_left, duration)
        self.power = max(self.power, power)

    def update(self, dt: float) -> Tuple[int, int]:
        if self.time_left <= 0:
            self.power = 0
            return (0, 0)
        self.time_left -= dt
        p = self.power * clamp(self.time_left / max(0.001, self.time_left + dt), 0, 1)
        return (int(random.uniform(-p, p)), int(random.uniform(-p, p)))


# =========================
# 3. BUTTON / UI
# =========================

class Button:
    def __init__(self, rect: Tuple[int, int, int, int], text: str, font: pygame.font.Font = FONT_MD):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font

    def draw(self, surface: pygame.Surface, mouse_pos: Tuple[int, int], enabled: bool = True) -> None:
        hover = self.rect.collidepoint(mouse_pos) and enabled
        base = (116, 72, 42) if enabled else (70, 70, 76)
        border = GOLD if hover else (177, 122, 55) if enabled else (100, 100, 110)
        text_col = WHITE if enabled else (150, 150, 160)
        shadow = self.rect.move(0, 5)
        pygame.draw.rect(surface, (10, 10, 10, 100), shadow, border_radius=14)
        pygame.draw.rect(surface, base if not hover else (148, 91, 46), self.rect, border_radius=14)
        pygame.draw.rect(surface, border, self.rect, 3, border_radius=14)
        draw_text(surface, self.text, self.font, text_col, self.rect.center, center=True)

    def clicked(self, event: pygame.event.Event, mouse_pos: Tuple[int, int], enabled: bool = True) -> bool:
        return enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(mouse_pos)


class SceneFader:
    def __init__(self):
        self.alpha = 0
        self.target = 0
        self.speed = 800

    def fade_in(self) -> None:
        self.alpha = 255
        self.target = 0

    def fade_out(self) -> None:
        self.target = 255

    def update(self, dt: float) -> None:
        if self.alpha < self.target:
            self.alpha = min(self.target, self.alpha + self.speed * dt)
        elif self.alpha > self.target:
            self.alpha = max(self.target, self.alpha - self.speed * dt)

    def draw(self, surface: pygame.Surface) -> None:
        if self.alpha <= 1:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(self.alpha)))
        surface.blit(overlay, (0, 0))


# =========================
# 4. LEVEL CONFIG / UNIT
# =========================

@dataclass
class LevelConfig:
    level: int
    title: str
    subtitle: str
    player_castle_hp: int
    enemy_castle_hp: int
    enemy_spawn_interval: float
    enemy_hp: int
    enemy_dmg: int
    enemy_speed: float
    elite_interval: float
    elite_hp: int
    elite_dmg: int
    elite_speed: float
    boss_interval: Optional[float]
    boss_hp: int
    boss_dmg: int
    note_ttl: float
    note_radius: int
    beat_fallback_duration: float


LEVELS: Dict[int, LevelConfig] = {
    1: LevelConfig(
        1,
        "Màn 1: Mê Linh nổi trống",
        "Nhịp 1.00s/nốt. Trận chậm, dễ làm quen hơn.",
        player_castle_hp=220,
        enemy_castle_hp=300,
        enemy_spawn_interval=3.80,
        enemy_hp=3,
        enemy_dmg=1,
        enemy_speed=22,
        elite_interval=42,
        elite_hp=15,
        elite_dmg=2,
        elite_speed=20,
        boss_interval=None,
        boss_hp=0,
        boss_dmg=0,
        note_ttl=2.20,
        note_radius=54,
        beat_fallback_duration=110,
    ),
    2: LevelConfig(
        2,
        "Màn 2: Cổ Loa khói lửa",
        "Nhịp 0.75s/nốt. Mở khóa skill: giơ 5 ngón gọi viện trợ.",
        player_castle_hp=260,
        enemy_castle_hp=430,
        enemy_spawn_interval=3.00,
        enemy_hp=4,
        enemy_dmg=1,
        enemy_speed=26,
        elite_interval=32,
        elite_hp=26,
        elite_dmg=4,
        elite_speed=23,
        boss_interval=75,
        boss_hp=90,
        boss_dmg=7,
        note_ttl=2.00,
        note_radius=50,
        beat_fallback_duration=110,
    ),
    3: LevelConfig(
        3,
        "Màn 3: Luy Lâu quyết chiến",
        "Nhịp 0.55s/nốt. Boss Đông Hán xuất hiện, nhưng trận không còn kết thúc quá sớm.",
        player_castle_hp=310,
        enemy_castle_hp=650,
        enemy_spawn_interval=2.30,
        enemy_hp=5,
        enemy_dmg=2,
        enemy_speed=30,
        elite_interval=25,
        elite_hp=42,
        elite_dmg=5,
        elite_speed=27,
        boss_interval=65,
        boss_hp=150,
        boss_dmg=11,
        note_ttl=1.75,
        note_radius=47,
        beat_fallback_duration=110,
    ),
}

UNIT_STATS = {
    # V7: tốc độ thấp hơn + cooldown đánh dài hơn để trận có thời gian quan sát.
    "ally_soldier": {"name": "Lính", "hp": 5, "dmg": 1, "speed": 34, "range": 45, "size": 1.0, "cooldown": 1.28, "aoe": False},
    "general_10": {"name": "Tướng lĩnh", "hp": 14, "dmg": 2, "speed": 30, "range": 50, "size": 1.15, "cooldown": 1.18, "aoe": False},
    "general_20": {"name": "Tướng lĩnh", "hp": 26, "dmg": 4, "speed": 28, "range": 56, "size": 1.28, "cooldown": 1.12, "aoe": False},
    "general_30": {"name": "Tướng lĩnh", "hp": 42, "dmg": 6, "speed": 26, "range": 62, "size": 1.42, "cooldown": 1.06, "aoe": True},
    "general_50": {"name": "Tướng lĩnh", "hp": 76, "dmg": 9, "speed": 24, "range": 68, "size": 1.58, "cooldown": 1.00, "aoe": True},
    "great_general": {"name": "Đại Tướng Mê Linh", "hp": 165, "dmg": 16, "speed": 21, "range": 82, "size": 1.9, "cooldown": 0.95, "aoe": True},
    "reinforce": {"name": "Viện binh", "hp": 8, "dmg": 2, "speed": 36, "range": 46, "size": 1.05, "cooldown": 1.15, "aoe": False},
    "enemy": {"name": "Địch", "hp": 3, "dmg": 1, "speed": 24, "range": 42, "size": 1.0, "cooldown": 1.28, "aoe": False},
    "elite": {"name": "Tinh anh", "hp": 20, "dmg": 3, "speed": 22, "range": 50, "size": 1.35, "cooldown": 1.16, "aoe": False},
    "boss": {"name": "Boss Đông Hán", "hp": 100, "dmg": 10, "speed": 18, "range": 72, "size": 1.85, "cooldown": 1.08, "aoe": True},
}


class CastleState:
    def __init__(self, max_hp: int):
        self.max_hp = max_hp
        self.hp = max_hp

    @property
    def ratio(self) -> float:
        return clamp(self.hp / max(1, self.max_hp), 0, 1)

    def damage(self, amount: int) -> None:
        self.hp = max(0, self.hp - int(amount))


class Unit:
    def __init__(self, kind: str, faction: str, lane: int, x: float, y: float, stats_override: Optional[Dict] = None):
        base = UNIT_STATS[kind].copy()
        if stats_override:
            base.update(stats_override)
        self.kind = kind
        self.faction = faction  # ally / enemy
        self.name = base["name"]
        self.max_hp = int(base["hp"])
        self.hp = int(base["hp"])
        self.dmg = int(base["dmg"])
        self.speed = float(base["speed"])
        self.attack_range = float(base["range"])
        self.size = float(base["size"])
        self.attack_cooldown = float(base["cooldown"])
        self.aoe = bool(base.get("aoe", False))
        self.lane = lane
        self.x = float(x)
        self.y = float(y)
        self.direction = 1 if faction == "ally" else -1
        self.attack_timer = random.uniform(0, 0.2)
        self.slash_timer = 0.0
        self.slash_done = False
        self.target: Optional[Unit] = None
        self.target_castle = False
        self.walk_phase = random.random() * math.tau
        self.dead = False
        self.hit_flash = 0.0
        self.last_dust = 0.0

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.dead

    def take_damage(self, amount: int) -> None:
        self.hp -= int(amount)
        self.hit_flash = 0.12
        if self.hp <= 0:
            self.dead = True

    def distance_to(self, other: "Unit") -> float:
        return abs(self.x - other.x)

    def update(
        self,
        dt: float,
        enemies: List["Unit"],
        enemy_castle: CastleState,
        player_castle: CastleState,
        particles: ParticleSystem,
        shake: CameraShake,
    ) -> None:
        if not self.alive:
            return
        self.walk_phase += dt * 8
        self.attack_timer -= dt
        self.hit_flash = max(0, self.hit_flash - dt)

        opponents = [u for u in enemies if u.alive and u.lane == self.lane and (u.x - self.x) * self.direction > -5]
        opponents.sort(key=lambda u: abs(u.x - self.x))
        target = opponents[0] if opponents and self.distance_to(opponents[0]) <= self.attack_range else None

        # Công thành nếu đã tới cổng.
        castle_in_range = False
        if self.faction == "ally" and self.x >= RIGHT_GATE_X - self.attack_range:
            castle_in_range = True
        elif self.faction == "enemy" and self.x <= LEFT_GATE_X + self.attack_range:
            castle_in_range = True

        if target is not None:
            self.target = target
            self.target_castle = False
            self._attack(dt, target, None, particles, shake)
        elif castle_in_range:
            self.target = None
            self.target_castle = True
            castle = enemy_castle if self.faction == "ally" else player_castle
            self._attack(dt, None, castle, particles, shake)
        else:
            self.target = None
            self.target_castle = False
            self.x += self.direction * self.speed * dt
            if random.random() < 0.03:
                particles.spawn_dust(self.x, self.y + 25, 1)

        if self.slash_timer > 0:
            self.slash_timer -= dt

    def _attack(
        self,
        dt: float,
        target: Optional["Unit"],
        castle: Optional[CastleState],
        particles: ParticleSystem,
        shake: CameraShake,
    ) -> None:
        if self.slash_timer <= 0 and self.attack_timer <= 0:
            self.slash_timer = 0.28
            self.slash_done = False
            self.attack_timer = self.attack_cooldown

        # Gây sát thương ở giữa animation chém, không biến mất ngay.
        if self.slash_timer > 0 and not self.slash_done and self.slash_timer < 0.16:
            self.slash_done = True
            hit_x = self.x + self.direction * (34 * self.size)
            hit_y = self.y - 20 * self.size
            particles.spawn_slash(hit_x, hit_y, self.direction, GOLD if self.faction == "ally" else RED)
            if self.kind in ("general_50", "great_general", "boss"):
                shake.trigger(4 if self.kind != "great_general" else 8, 0.16)

            if target is not None and target.alive:
                target.take_damage(self.dmg)
                particles.spawn_dust(target.x, target.y + 18, 4)
                if self.aoe:
                    # Chém lan các mục tiêu gần đó cùng lane.
                    for u in list(getattr(target, "_group_ref", [])):
                        if u is not target and u.alive and u.lane == self.lane and abs(u.x - target.x) <= 60 * self.size:
                            u.take_damage(max(1, self.dmg // 2))
            if castle is not None:
                castle.damage(self.dmg)
                particles.spawn_smoke(RIGHT_GATE_X if self.faction == "ally" else LEFT_GATE_X, self.y - 30, 4)
                shake.trigger(3 + self.size * 2, 0.12)

    def draw(self, surface: pygame.Surface, offset: Tuple[int, int] = (0, 0)) -> None:
        sx, sy = offset
        x = int(self.x + sx)
        y = int(self.y + sy)
        s = self.size
        color = (238, 222, 155) if self.faction == "ally" else (185, 70, 68)
        outline = BLACK
        if self.kind == "great_general":
            color = (248, 215, 99)
        elif self.kind == "reinforce":
            color = (116, 217, 156)
        elif self.kind == "elite":
            color = (222, 100, 80)
        elif self.kind == "boss":
            color = (178, 92, 214)

        if self.hit_flash > 0:
            color = WHITE

        body_h = 44 * s
        head_r = int(10 * s)
        torso_top = (x, int(y - body_h))
        torso_mid = (x, int(y - body_h * 0.45))
        hip = (x, int(y - 12 * s))
        head = (x, int(y - body_h - 13 * s))

        # Tên + thanh máu
        label_y = int(head[1] - 40 * s)
        name_surf = text_surface(self.name, FONT_XS if s < 1.5 else FONT_SM, WHITE)
        name_rect = name_surf.get_rect(center=(x, label_y))
        bg = name_rect.inflate(8, 3)
        pygame.draw.rect(surface, (0, 0, 0, 120), bg, border_radius=5)
        surface.blit(name_surf, name_rect)
        hp_w = int(44 * s)
        hp_h = 5
        pygame.draw.rect(surface, (70, 20, 20), (x - hp_w // 2, label_y + 14, hp_w, hp_h), border_radius=3)
        pygame.draw.rect(surface, GREEN, (x - hp_w // 2, label_y + 14, int(hp_w * clamp(self.hp / self.max_hp, 0, 1)), hp_h), border_radius=3)

        # Bóng
        pygame.draw.ellipse(surface, (0, 0, 0, 80), (x - int(22 * s), y + 8, int(44 * s), int(12 * s)))

        # Chân có walk cycle
        step = math.sin(self.walk_phase) * 9 * s if not self.target and not self.target_castle else 0
        leg1 = (int(x - 13 * s + step), y + int(12 * s))
        leg2 = (int(x + 13 * s - step), y + int(12 * s))
        pygame.draw.line(surface, outline, hip, leg1, max(3, int(4 * s)))
        pygame.draw.line(surface, outline, hip, leg2, max(3, int(4 * s)))
        pygame.draw.line(surface, color, hip, leg1, max(2, int(2 * s)))
        pygame.draw.line(surface, color, hip, leg2, max(2, int(2 * s)))

        # Thân
        pygame.draw.line(surface, outline, torso_top, hip, max(4, int(6 * s)))
        pygame.draw.line(surface, color, torso_top, hip, max(2, int(3 * s)))

        # Tay / animation chém
        shoulder = (x, int(y - body_h * 0.75))
        back_hand = (x - self.direction * int(18 * s), int(y - body_h * 0.45))
        pygame.draw.line(surface, outline, shoulder, back_hand, max(3, int(4 * s)))
        pygame.draw.line(surface, color, shoulder, back_hand, max(2, int(2 * s)))

        if self.slash_timer > 0:
            prog = 1.0 - clamp(self.slash_timer / 0.28, 0, 1)
            angle = lerp(-1.35, 0.85, prog) * self.direction
            arm_len = 36 * s
            hand = (int(shoulder[0] + math.cos(angle) * arm_len), int(shoulder[1] + math.sin(angle) * arm_len))
            weapon_end = (int(hand[0] + self.direction * 30 * s), int(hand[1] - 12 * s))
            # slash arc
            arc_rect = pygame.Rect(x - int(52 * s), y - int(78 * s), int(104 * s), int(82 * s))
            try:
                pygame.draw.arc(surface, (255, 245, 190), arc_rect, -0.7, 0.85, max(2, int(3 * s)))
            except Exception:
                pass
        else:
            hand = (x + self.direction * int(20 * s), int(y - body_h * 0.55))
            weapon_end = (hand[0] + self.direction * int(24 * s), hand[1] - int(10 * s))

        pygame.draw.line(surface, outline, shoulder, hand, max(3, int(4 * s)))
        pygame.draw.line(surface, color, shoulder, hand, max(2, int(2 * s)))
        pygame.draw.line(surface, (224, 224, 218), hand, weapon_end, max(2, int(3 * s)))
        pygame.draw.circle(surface, color, head, head_r)
        pygame.draw.circle(surface, outline, head, head_r, max(2, int(2 * s)))

        # Khiên nhỏ cho tướng
        if self.kind.startswith("general") or self.kind == "great_general" or self.kind == "boss":
            shield_x = x - self.direction * int(18 * s)
            shield_y = int(y - body_h * 0.55)
            pygame.draw.circle(surface, DARK_GOLD if self.faction == "ally" else DARK_RED, (shield_x, shield_y), int(9 * s))
            pygame.draw.circle(surface, GOLD if self.faction == "ally" else RED, (shield_x, shield_y), int(9 * s), 2)


class RhythmNote:
    def __init__(self, spawn_time: float, expire_time: float, pos: Tuple[int, int], radius: int):
        self.spawn_time = spawn_time
        self.expire_time = expire_time
        self.x, self.y = pos
        self.radius = radius
        self.hit = False

    def alive(self, now: float) -> bool:
        return (not self.hit) and now <= self.expire_time

    def expired(self, now: float) -> bool:
        return (not self.hit) and now > self.expire_time

    def can_hit(self, pos: Tuple[int, int]) -> bool:
        dx = pos[0] - self.x
        dy = pos[1] - self.y
        return math.hypot(dx, dy) <= self.radius

    def draw(self, surface: pygame.Surface, now: float) -> None:
        ttl = max(0.001, self.expire_time - self.spawn_time)
        life = clamp((self.expire_time - now) / ttl, 0, 1)
        pulse = 1.0 + math.sin(now * 12) * 0.06
        r = int(self.radius * pulse)
        alpha = int(160 + 80 * life)
        temp = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        center = (r * 2, r * 2)
        pygame.draw.circle(temp, (255, 214, 87, 45), center, int(r * 1.55))
        pygame.draw.circle(temp, (255, 219, 94, alpha), center, r, 4)
        pygame.draw.circle(temp, (184, 69, 39, 190), center, int(r * 0.56))
        pygame.draw.circle(temp, (255, 238, 160, 220), center, int(r * 0.26))
        # vòng thu lại biểu thị thời gian
        pygame.draw.arc(temp, (255, 255, 255, 220), (r, r, r * 2, r * 2), -math.pi / 2, -math.pi / 2 + math.tau * life, 4)
        surface.blit(temp, (self.x - r * 2, self.y - r * 2))


# =========================
# 5. GAME CHÍNH
# =========================

class MelinhGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tiếng Trống Mê Linh - V8 Camera Fix")
        self.clock = pygame.time.Clock()
        self.running = True
        os.makedirs(ASSETS_DIR, exist_ok=True)

        self.state = "MENU"
        self.previous_state = "MENU"
        self.fader = SceneFader()
        self.particles = ParticleSystem()
        self.shake = CameraShake()
        self.shake_offset = (0, 0)
        self.scene_time = 0.0
        self.global_time = 0.0

        self.hand_tracker = HandGestureTracker()
        self.hand_state = HandState()
        self.skill_manager = SkillManager()
        self.use_mouse_in_battle_when_no_hand = True

        self.save = self.load_save()
        self.unlocked_level = int(self.save.get("unlocked_level", 1))
        self.current_level = 1
        self.level_config = LEVELS[1]

        self.menu_particles_timer = 0.0
        self.story_index = 0
        self.story_char = 0
        self.story_timer = 0.0
        self.cutscene_timer = 0.0
        self.cutscene_lines: List[str] = []
        self.result_victory = False

        self.buttons = {
            "start": Button((500, 415, 280, 64), "BẮT ĐẦU", FONT_LG),
            "guide": Button((500, 495, 280, 58), "HƯỚNG DẪN", FONT_MD),
            "quit": Button((500, 565, 280, 58), "THOÁT", FONT_MD),
            "back": Button((40, 630, 190, 54), "QUAY LẠI", FONT_MD),
            "skip": Button((1030, 630, 190, 54), "BỎ QUA", FONT_MD),
            "next": Button((1030, 630, 190, 54), "TIẾP", FONT_MD),
            "menu": Button((500, 570, 280, 58), "VỀ MENU", FONT_MD),
            "level_select": Button((820, 570, 280, 58), "CHỌN MÀN", FONT_MD),
            "continue": Button((180, 570, 280, 58), "TIẾP TỤC", FONT_MD),
        }

        self.story_lines = [
            "Năm 40 sau Công Nguyên, đất Giao Chỉ chìm trong bóng tối của ách đô hộ Đông Hán.",
            "Từ vùng đất Mê Linh, tiếng trống khởi nghĩa bắt đầu vang lên giữa khói lửa.",
            "Hai Bà Trưng dựng cờ, kêu gọi muôn dân đứng dậy giành lại non sông.",
            "Bạn không chỉ là người đánh trống. Bạn là nhịp tim của nghĩa quân.",
            "Mỗi nhịp trống đúng lúc sẽ triệu quân, gọi tướng, phá tan thành giặc.",
            "Hãy giữ vững ba chiến tuyến và đưa tiếng trống Mê Linh vang tới Luy Lâu!",
        ]

        # Battle variables
        self.player_castle = CastleState(160)
        self.enemy_castle = CastleState(180)
        self.allies: List[Unit] = []
        self.enemies: List[Unit] = []
        self.notes: List[RhythmNote] = []
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.last_combo_general = 0
        self.battle_start_time = 0.0
        self.song_cycle_start = 0.0
        self.song_duration = 65.0
        self.beats: List[float] = []
        self.beat_source = ""
        self.next_beat_index = 0
        self.enemy_spawn_timer = 0.0
        self.elite_spawn_timer = 0.0
        self.boss_spawn_timer = 0.0
        self.last_hit_time = 0.0
        self.last_music_path: Optional[str] = None
        self.current_music: Optional[str] = None
        self.note_pattern_index = 0
        self.pending_ally_summons = 0
        self.ally_spawn_timer = 0.0
        self.sfx = {
            "hit": self.load_sound("sfx_hit.wav"),
            "combo": self.load_sound("sfx_combo.wav"),
            "miss": self.load_sound("sfx_miss.wav"),
            "summon": self.load_sound("sfx_summon.wav"),
            "big_general": self.load_sound("sfx_big_general.wav"),
        }
        self.battle_message = ""
        self.battle_message_timer = 0.0
        self.start_menu_music()

    # ------------------------- SAVE -------------------------
    def load_save(self) -> Dict:
        if os.path.exists(SAVE_PATH):
            try:
                with open(SAVE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"unlocked_level": 1}

    def save_game(self) -> None:
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump({"unlocked_level": self.unlocked_level}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ------------------------- STATE -------------------------
    def change_state(self, new_state: str) -> None:
        self.previous_state = self.state
        self.state = new_state
        self.scene_time = 0.0
        self.fader.fade_in()
        if new_state == "STORY":
            self.story_index = 0
            self.story_char = 0
            self.story_timer = 0
        if new_state in ("MENU", "STORY", "GUIDE", "LEVEL_SELECT", "CUTSCENE", "RESULT"):
            self.start_menu_music()

    def prepare_cutscene(self, level: int) -> None:
        self.current_level = level
        self.level_config = LEVELS[level]
        if level == 1:
            self.cutscene_lines = [
                "MÊ LINH",
                "Tiếng trống đầu tiên vang lên. Nghĩa quân tập hợp trước cổng làng.",
                "Hãy giữ nhịp, giữ tuyến, phá vỡ đồn giặc đầu tiên.",
            ]
        elif level == 2:
            self.cutscene_lines = [
                "CỔ LOA",
                "Quân Đông Hán kéo đến đông hơn. Khói lửa phủ kín ba đường tiến quân.",
                "Giơ 5 ngón tay để hiệu triệu một tốp viện binh khi nguy cấp.",
            ]
        else:
            self.cutscene_lines = [
                "LUY LÂU",
                "Trận quyết chiến đã tới. Tướng Đông Hán đích thân xuất trận.",
                "Nắm tay lại để gọi Đại Tướng Mê Linh nghiền nát chiến tuyến địch.",
            ]
        self.cutscene_timer = 0.0
        self.change_state("CUTSCENE")

    # ------------------------- AUDIO / BEAT -------------------------

    def load_sound(self, filename: str) -> Optional[pygame.mixer.Sound]:
        if not MIXER_OK:
            return None
        path = os.path.join(ASSETS_DIR, filename)
        if not os.path.exists(path):
            return None
        try:
            snd = pygame.mixer.Sound(path)
            snd.set_volume(SFX_VOLUME)
            return snd
        except Exception:
            return None

    def play_sfx(self, name: str) -> None:
        snd = self.sfx.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def start_menu_music(self) -> None:
        if not MIXER_OK:
            return
        path = get_menu_audio_path(ASSETS_DIR)
        if not path:
            return
        if self.current_music == path:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(MENU_VOLUME)
            pygame.mixer.music.play(loops=-1)
            self.current_music = path
        except Exception:
            self.current_music = None

    def stop_music(self) -> None:
        if MIXER_OK:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.current_music = None

    def start_music_for_level(self, level: int) -> None:
        self.last_music_path = get_level_audio_path(ASSETS_DIR, level)
        if MIXER_OK and self.last_music_path:
            try:
                pygame.mixer.music.load(self.last_music_path)
                pygame.mixer.music.set_volume(GAME_VOLUME)
                pygame.mixer.music.play(loops=-1)
                self.current_music = self.last_music_path
            except Exception:
                self.last_music_path = None
                self.current_music = None
        self.song_cycle_start = time.time()

    def reset_battle(self, level: int) -> None:
        self.current_level = level
        self.level_config = LEVELS[level]
        cfg = self.level_config
        self.player_castle = CastleState(cfg.player_castle_hp)
        self.enemy_castle = CastleState(cfg.enemy_castle_hp)
        self.allies.clear()
        self.enemies.clear()
        self.notes.clear()
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.last_combo_general = 0
        self.enemy_spawn_timer = 0.0
        self.elite_spawn_timer = 0.0
        self.boss_spawn_timer = 0.0
        self.last_hit_time = 0.0
        self.note_pattern_index = 0
        self.pending_ally_summons = 0
        self.ally_spawn_timer = ALLY_SPAWN_COOLDOWN.get(level, 1.15)
        self.battle_start_time = time.time()
        self.battle_message = ""
        self.battle_message_timer = 0.0
        self.beats, self.song_duration, self.beat_source = load_or_generate_beats(ASSETS_DIR, level, cfg.beat_fallback_duration)
        self.next_beat_index = 0
        self.start_music_for_level(level)
        self.particles.spawn_smoke(WIDTH // 2, 610, 20)
        self.shake.trigger(7, 0.22)

    # ------------------------- MAIN LOOP -------------------------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.global_time += dt
            self.scene_time += dt
            self.handle_events()
            self.update(dt)
            self.draw()
        self.hand_tracker.release()
        pygame.quit()
        sys.exit()

    def reconnect_camera(self) -> None:
        """Nhấn C trong trận để mở lại camera nếu MediaPipe/camera bị treo."""
        try:
            self.hand_tracker.release()
        except Exception:
            pass
        self.hand_tracker = HandGestureTracker()
        self.hand_state = self.hand_tracker.last_state if hasattr(self.hand_tracker, "last_state") else HandState(message="Đã thử mở lại camera")

    def handle_events(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "PLAYING":
                        self.change_state("LEVEL_SELECT")
                    elif self.state in ("GUIDE", "STORY", "LEVEL_SELECT"):
                        self.change_state("MENU")
                    else:
                        self.running = False
                if self.state == "PLAYING":
                    # Debug khi chưa có camera.
                    if event.key == pygame.K_5 and self.current_level >= 2:
                        if self.skill_manager.reinforce.use(time.time()):
                            self.cast_reinforcement()
                    if event.key == pygame.K_f and self.current_level >= 3:
                        if self.skill_manager.great_general.use(time.time()):
                            self.cast_great_general()
                    if event.key == pygame.K_c:
                        self.reconnect_camera()
                    if event.key == pygame.K_m:
                        self.use_mouse_in_battle_when_no_hand = not self.use_mouse_in_battle_when_no_hand
                if self.state == "STORY" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.advance_story()
                if self.state == "RESULT" and event.key == pygame.K_RETURN:
                    self.change_state("LEVEL_SELECT")

            if self.state == "MENU":
                if self.buttons["start"].clicked(event, mouse_pos):
                    self.change_state("STORY")
                elif self.buttons["guide"].clicked(event, mouse_pos):
                    self.change_state("GUIDE")
                elif self.buttons["quit"].clicked(event, mouse_pos):
                    self.running = False

            elif self.state == "GUIDE":
                if self.buttons["back"].clicked(event, mouse_pos):
                    self.change_state("MENU")

            elif self.state == "STORY":
                if self.buttons["skip"].clicked(event, mouse_pos):
                    self.change_state("LEVEL_SELECT")
                elif self.buttons["next"].clicked(event, mouse_pos):
                    self.advance_story()

            elif self.state == "LEVEL_SELECT":
                if self.buttons["back"].clicked(event, mouse_pos):
                    self.change_state("MENU")
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for level in (1, 2, 3):
                        rect = self.level_card_rect(level)
                        if rect.collidepoint(mouse_pos):
                            if level <= self.unlocked_level:
                                self.prepare_cutscene(level)
                            else:
                                self.battle_message = "Hãy vượt qua màn trước để mở khóa!"
                                self.battle_message_timer = 1.4

            elif self.state == "CUTSCENE":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.reset_battle(self.current_level)
                    self.change_state("PLAYING")

            elif self.state == "RESULT":
                if self.buttons["menu"].clicked(event, mouse_pos):
                    self.change_state("MENU")
                if self.buttons["level_select"].clicked(event, mouse_pos):
                    self.change_state("LEVEL_SELECT")
                if self.result_victory and self.current_level < 3 and self.buttons["continue"].clicked(event, mouse_pos):
                    self.prepare_cutscene(self.current_level + 1)

    def advance_story(self) -> None:
        current = self.story_lines[self.story_index]
        if self.story_char < len(current):
            self.story_char = len(current)
            return
        self.story_index += 1
        self.story_char = 0
        self.story_timer = 0
        if self.story_index >= len(self.story_lines):
            self.change_state("LEVEL_SELECT")

    def update(self, dt: float) -> None:
        self.fader.update(dt)
        self.shake_offset = self.shake.update(dt)
        self.particles.update(dt)
        self.battle_message_timer = max(0, self.battle_message_timer - dt)

        if self.state in ("MENU", "LEVEL_SELECT", "CUTSCENE", "RESULT"):
            self.update_ambient_particles(dt)
        if self.state == "STORY":
            self.update_story(dt)
            self.update_ambient_particles(dt)
        if self.state == "PLAYING":
            self.update_battle(dt)

    def update_ambient_particles(self, dt: float) -> None:
        self.menu_particles_timer -= dt
        if self.menu_particles_timer <= 0:
            self.menu_particles_timer = 0.08
            if random.random() < 0.55:
                self.particles.spawn_fire(random.choice([85, 1180, 245, 1030]), random.randint(560, 690), 1)
            if random.random() < 0.45:
                self.particles.spawn_smoke(random.randint(0, WIDTH), random.randint(530, 700), 1)

    def update_story(self, dt: float) -> None:
        if self.story_index >= len(self.story_lines):
            return
        self.story_timer += dt
        if self.story_timer > 0.028:
            self.story_timer = 0
            if self.story_char < len(self.story_lines[self.story_index]):
                self.story_char += 1

    # ------------------------- BATTLE UPDATE -------------------------
    def update_battle(self, dt: float) -> None:
        now = time.time()
        cfg = self.level_config

        # Camera/hand chỉ dùng khi đang chơi.
        self.hand_state = self.hand_tracker.update(WIDTH, HEIGHT)
        if self.skill_manager.update_and_check_reinforce(self.current_level, self.hand_state, now):
            self.cast_reinforcement()
        if self.skill_manager.update_and_check_great_general(self.current_level, self.hand_state, now):
            self.cast_great_general()

        self.spawn_notes_by_beat(now)
        self.handle_note_hits(now)

        # V7: làm phần chiến trường chậm hơn mà vẫn giữ nhạc đúng thời gian thật.
        battle_dt = dt * BATTLE_TIME_SCALE
        self.process_ally_spawn_queue(battle_dt)
        self.spawn_enemies(battle_dt)

        # Gắn group ref để chém lan.
        for u in self.allies:
            u._group_ref = self.enemies
        for u in self.enemies:
            u._group_ref = self.allies

        for ally in list(self.allies):
            ally.update(battle_dt, self.enemies, self.enemy_castle, self.player_castle, self.particles, self.shake)
        for enemy in list(self.enemies):
            enemy.update(battle_dt, self.allies, self.enemy_castle, self.player_castle, self.particles, self.shake)

        # Dọn xác sau khi animation hit đã thể hiện.
        for group in (self.allies, self.enemies):
            for u in list(group):
                if not u.alive:
                    self.particles.spawn_smoke(u.x, u.y - 15, 6)
                    group.remove(u)

        if self.enemy_castle.hp <= 0:
            self.finish_battle(True)
        elif self.player_castle.hp <= 0:
            self.finish_battle(False)

    def spawn_notes_by_beat(self, now: float) -> None:
        cfg = self.level_config
        # Nếu nhạc loop, beat cũng loop.
        elapsed = now - self.song_cycle_start
        if elapsed >= self.song_duration:
            self.song_cycle_start = now
            self.next_beat_index = 0
            elapsed = 0

        # V6: nốt xuất hiện đúng theo nhịp cố định, không spawn random theo thời gian.
        # lead_time = 0 để nốt hiện đúng mốc beat. TTL dài hơn để người chơi có thời gian trỏ.
        lead_time = 0.0
        while self.next_beat_index < len(self.beats) and self.beats[self.next_beat_index] <= elapsed + lead_time:
            note_spawn_time = now
            note_expire = now + cfg.note_ttl
            pos = self.next_note_position()
            self.notes.append(RhythmNote(note_spawn_time, note_expire, pos, cfg.note_radius))
            self.next_beat_index += 1

        # Miss note -> giảm combo, không reset về 0.
        for note in list(self.notes):
            if note.expired(now):
                self.notes.remove(note)
                self.combo = max(0, self.combo - (4 if self.current_level < 3 else 6))
                self.play_sfx("miss")

    def next_note_position(self) -> Tuple[int, int]:
        """Vị trí nốt theo pattern cố định, không còn random."""
        pattern = NOTE_PATTERNS.get(self.current_level, NOTE_PATTERNS[1])
        pos = pattern[self.note_pattern_index % len(pattern)]
        self.note_pattern_index += 1
        return pos

    def get_cursor_for_battle(self) -> Optional[Tuple[int, int]]:
        if self.hand_state.has_hand and self.hand_state.pointer:
            return self.hand_state.pointer
        if self.use_mouse_in_battle_when_no_hand:
            return pygame.mouse.get_pos()
        return None

    def handle_note_hits(self, now: float) -> None:
        cursor = self.get_cursor_for_battle()
        if cursor is None:
            return
        if now - self.last_hit_time < 0.16:
            return
        for note in list(self.notes):
            if note.can_hit(cursor):
                note.hit = True
                self.notes.remove(note)
                self.last_hit_time = now
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                self.score += 10 + min(self.combo, 50)
                self.play_sfx("hit")
                self.particles.spawn_slash(note.x, note.y, random.choice([-1, 1]), GOLD)
                self.particles.spawn_fire(note.x, note.y, 8)
                self.queue_ally_soldier()
                self.check_combo_general()
                break

    def ally_count_total(self) -> int:
        return sum(1 for a in self.allies if a.alive and a.kind in ("ally_soldier", "reinforce"))

    def ally_count_lane(self, lane: int) -> int:
        return sum(1 for a in self.allies if a.alive and a.lane == lane and a.kind in ("ally_soldier", "reinforce"))

    def can_spawn_normal_ally(self) -> bool:
        return self.ally_count_total() < ALLY_MAX_TOTAL.get(self.current_level, 16)

    def queue_ally_soldier(self) -> None:
        """Một nốt đúng thêm lệnh gọi lính, nhưng không spawn ồ ạt ngay lập tức."""
        max_queue = ALLY_QUEUE_MAX.get(self.current_level, 7)
        self.pending_ally_summons = min(max_queue, self.pending_ally_summons + 1)

    def process_ally_spawn_queue(self, dt: float) -> None:
        if self.pending_ally_summons <= 0:
            return
        self.ally_spawn_timer += dt
        cooldown = ALLY_SPAWN_COOLDOWN.get(self.current_level, 1.10)
        if self.ally_spawn_timer < cooldown:
            return
        self.ally_spawn_timer = 0.0
        if self.spawn_ally_soldier():
            self.pending_ally_summons -= 1
        else:
            # Quân đã quá đông, giữ lại lệnh một chút thay vì đẻ thêm làm mất cân bằng.
            self.ally_spawn_timer = cooldown * 0.65

    def smart_lane_for_ally(self) -> int:
        # V7: ưu tiên lane nguy hiểm nhưng tránh nhồi quá nhiều quân vào một lane.
        max_lane = ALLY_MAX_PER_LANE.get(self.current_level, 5)
        best_lane = 0
        best_score = -10_000.0
        for lane in range(3):
            ally_count = self.ally_count_lane(lane)
            if ally_count >= max_lane:
                continue
            lane_enemies = [e for e in self.enemies if e.lane == lane and e.alive]
            pressure = 0.0
            if lane_enemies:
                # Địch càng gần thành ta thì điểm càng cao.
                closest = min(lane_enemies, key=lambda e: e.x)
                pressure += max(0, 900 - closest.x) / 80.0
                pressure += len(lane_enemies) * 1.8
                pressure += sum(2.5 for e in lane_enemies if e.kind in ("elite", "boss"))
            score = pressure - ally_count * 2.2 + random.random() * 0.35
            if score > best_score:
                best_score = score
                best_lane = lane
        return best_lane

    def spawn_ally_soldier(self) -> bool:
        if not self.can_spawn_normal_ally():
            return False
        lane = self.smart_lane_for_ally()
        if self.ally_count_lane(lane) >= ALLY_MAX_PER_LANE.get(self.current_level, 5):
            return False
        u = Unit("ally_soldier", "ally", lane, LEFT_GATE_X, LANE_Y[lane])
        self.allies.append(u)
        self.particles.spawn_dust(u.x, u.y + 18, 5)
        return True

    def check_combo_general(self) -> None:
        combo = self.combo
        if combo in (10, 20, 30, 50):
            self.spawn_combo_general(combo)
            self.last_combo_general = combo
        elif combo > 50 and combo % 10 == 0 and combo != self.last_combo_general:
            self.spawn_combo_general(50)
            self.last_combo_general = combo

    def spawn_combo_general(self, tier: int) -> None:
        kind = f"general_{tier}"
        lane = self.smart_lane_for_ally()
        u = Unit(kind, "ally", lane, LEFT_GATE_X - 8, LANE_Y[lane])
        self.allies.append(u)
        self.particles.spawn_smoke(u.x, u.y - 24, 16)
        self.particles.spawn_fire(u.x, u.y - 40, 8)
        self.shake.trigger(6 + tier / 12, 0.25)
        self.play_sfx("combo")
        # Không hiện thông báo triệu hồi theo yêu cầu.

    def cast_reinforcement(self) -> None:
        # V7: viện trợ vừa phải, không làm vỡ cân bằng.
        danger_lane = self.smart_lane_for_ally()
        for lane in range(3):
            if self.ally_count_lane(lane) < ALLY_MAX_PER_LANE.get(self.current_level, 5) + 1:
                x = LEFT_GATE_X - 30
                y = LANE_Y[lane] + random.uniform(-6, 6)
                self.allies.append(Unit("reinforce", "ally", lane, x, y))
        # Thêm 1 quân cho lane nguy hiểm nhất nếu còn chỗ.
        if self.ally_count_lane(danger_lane) < ALLY_MAX_PER_LANE.get(self.current_level, 5) + 2:
            self.allies.append(Unit("reinforce", "ally", danger_lane, LEFT_GATE_X - 58, LANE_Y[danger_lane]))
        self.particles.spawn_smoke(LEFT_GATE_X, 485, 24)
        self.shake.trigger(8, 0.28)
        self.play_sfx("summon")

    def cast_great_general(self) -> None:
        lane = self.smart_lane_for_ally()
        u = Unit("great_general", "ally", lane, LEFT_GATE_X - 15, LANE_Y[lane])
        self.allies.append(u)
        self.particles.spawn_fire(u.x, u.y - 80, 28)
        self.particles.spawn_smoke(u.x, u.y - 20, 32)
        self.shake.trigger(15, 0.45)
        self.play_sfx("big_general")

    def spawn_enemies(self, dt: float) -> None:
        cfg = self.level_config
        self.enemy_spawn_timer += dt
        self.elite_spawn_timer += dt
        self.boss_spawn_timer += dt

        if self.enemy_spawn_timer >= cfg.enemy_spawn_interval:
            self.enemy_spawn_timer = 0
            lane = self.smart_lane_for_enemy()
            stats = {"hp": cfg.enemy_hp, "dmg": cfg.enemy_dmg, "speed": cfg.enemy_speed}
            self.enemies.append(Unit("enemy", "enemy", lane, RIGHT_GATE_X, LANE_Y[lane], stats))

        if self.elite_spawn_timer >= cfg.elite_interval:
            self.elite_spawn_timer = 0
            lane = self.smart_lane_for_enemy()
            stats = {"hp": cfg.elite_hp, "dmg": cfg.elite_dmg, "speed": cfg.elite_speed}
            self.enemies.append(Unit("elite", "enemy", lane, RIGHT_GATE_X + 10, LANE_Y[lane], stats))
            self.particles.spawn_smoke(RIGHT_GATE_X, LANE_Y[lane], 12)
            self.shake.trigger(5, 0.16)

        if cfg.boss_interval and self.boss_spawn_timer >= cfg.boss_interval:
            self.boss_spawn_timer = 0
            lane = self.smart_lane_for_enemy(boss=True)
            if self.current_level == 3:
                # Boss Đông Hán mạnh hơn ở màn 3, có thể lặp lại.
                kind = "boss"
                hp = cfg.boss_hp + random.randint(0, 25)
                dmg = cfg.boss_dmg
                size = 1.95
            else:
                kind = "boss"
                hp = cfg.boss_hp
                dmg = cfg.boss_dmg
                size = 1.55
            self.enemies.append(Unit(kind, "enemy", lane, RIGHT_GATE_X + 20, LANE_Y[lane], {"hp": hp, "dmg": dmg, "size": size}))
            self.particles.spawn_fire(RIGHT_GATE_X, LANE_Y[lane] - 45, 22)
            self.particles.spawn_smoke(RIGHT_GATE_X, LANE_Y[lane], 22)
            self.shake.trigger(12 if self.current_level == 3 else 8, 0.35)

    def smart_lane_for_enemy(self, boss: bool = False) -> int:
        if self.current_level <= 1 and not boss:
            return random.randint(0, 2)
        # Địch ưu tiên lane đang ít quân ta để gây áp lực.
        lane_scores = []
        for lane in range(3):
            ally_count = sum(1 for a in self.allies if a.lane == lane and a.alive)
            enemy_count = sum(1 for e in self.enemies if e.lane == lane and e.alive)
            score = ally_count * 1.5 - enemy_count * 0.6 + random.random() * 1.5
            lane_scores.append((score, lane))
        lane_scores.sort(key=lambda t: t[0])
        return lane_scores[0][1]

    def finish_battle(self, victory: bool) -> None:
        self.result_victory = victory
        self.stop_music()
        if victory:
            self.unlocked_level = max(self.unlocked_level, min(3, self.current_level + 1))
            self.save_game()
            self.particles.spawn_fire(WIDTH // 2, 420, 40)
            self.shake.trigger(12, 0.45)
        else:
            self.particles.spawn_smoke(LEFT_CASTLE_X, 455, 40)
            self.shake.trigger(10, 0.35)
        self.change_state("RESULT")

    # ------------------------- DRAW STATES -------------------------
    def draw(self) -> None:
        if self.state == "MENU":
            self.draw_menu()
        elif self.state == "STORY":
            self.draw_story()
        elif self.state == "GUIDE":
            self.draw_guide()
        elif self.state == "LEVEL_SELECT":
            self.draw_level_select()
        elif self.state == "CUTSCENE":
            self.draw_cutscene()
        elif self.state == "PLAYING":
            self.draw_battle()
        elif self.state == "RESULT":
            self.draw_result()
        self.fader.draw(self.screen)
        pygame.display.flip()

    def draw_cinematic_background(self, title_mode: bool = False) -> None:
        draw_gradient_background(self.screen)
        # Mặt trời đỏ
        pygame.draw.circle(self.screen, (170, 54, 42), (1040, 145), 68)
        pygame.draw.circle(self.screen, (230, 115, 68, 80), (1040, 145), 88)
        # Núi xa
        mountains = [
            [(0, 420), (160, 250), (300, 420)],
            [(180, 430), (360, 220), (560, 430)],
            [(460, 425), (660, 245), (860, 425)],
            [(780, 430), (980, 260), (1280, 430)],
        ]
        for poly in mountains:
            pygame.draw.polygon(self.screen, (38, 45, 55), poly)
        # Nền chiến trường
        pygame.draw.rect(self.screen, (57, 43, 32), (0, 430, WIDTH, 290))
        for i in range(34):
            x = (i * 43 + int(self.global_time * 10)) % WIDTH
            pygame.draw.line(self.screen, (70, 52, 37), (x, 438), (x - 120, HEIGHT), 2)
        # Silhouette quân lính
        for i in range(28):
            x = 20 + i * 46
            h = 50 + (i % 5) * 9
            y = 600 - (i % 3) * 10
            pygame.draw.line(self.screen, (16, 16, 20), (x, y), (x, y - h), 4)
            pygame.draw.circle(self.screen, (16, 16, 20), (x, y - h - 9), 7)
            pygame.draw.line(self.screen, (16, 16, 20), (x, y - 28), (x + 20, y - 54), 3)
        self.particles.draw(self.screen)
        # Trống lớn
        if title_mode:
            cx, cy = 245, 515
            pygame.draw.ellipse(self.screen, (20, 14, 12), (cx - 100, cy + 58, 200, 30))
            pygame.draw.ellipse(self.screen, (166, 93, 45), (cx - 100, cy - 70, 200, 140))
            pygame.draw.ellipse(self.screen, (245, 202, 108), (cx - 92, cy - 62, 184, 124), 8)
            pygame.draw.circle(self.screen, DARK_RED, (cx, cy), 50)
            pygame.draw.circle(self.screen, GOLD, (cx, cy), 50, 4)
            pygame.draw.line(self.screen, GOLD, (cx - 50, cy - 90), (cx + 75, cy - 155), 7)
            pygame.draw.line(self.screen, GOLD, (cx + 10, cy - 95), (cx + 125, cy - 135), 7)

    def draw_menu(self) -> None:
        mouse = pygame.mouse.get_pos()
        self.draw_cinematic_background(title_mode=True)
        # Overlay cinematic
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 50))
        self.screen.blit(shade, (0, 0))
        draw_text(self.screen, "TIẾNG TRỐNG", FONT_TITLE, GOLD, (WIDTH // 2, 115), center=True)
        draw_text(self.screen, "MÊ LINH", FONT_TITLE, (255, 238, 188), (WIDTH // 2, 190), center=True)
        draw_text(self.screen, "Rhythm • Gesture • Lane Battle", FONT_MD, (225, 205, 160), (WIDTH // 2, 270), center=True)
        draw_text(self.screen, "Dùng chuột ở menu. Vào trận mới dùng tay/camera.", FONT_SM, WHITE, (WIDTH // 2, 315), center=True)
        self.buttons["start"].draw(self.screen, mouse)
        self.buttons["guide"].draw(self.screen, mouse)
        self.buttons["quit"].draw(self.screen, mouse)
        draw_text(self.screen, "v5 Pygame Full Cinematic", FONT_XS, (180, 165, 130), (20, HEIGHT - 30))

    def draw_story(self) -> None:
        mouse = pygame.mouse.get_pos()
        self.draw_cinematic_background(title_mode=False)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 105))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, "CỐT TRUYỆN", FONT_XL, GOLD, (WIDTH // 2, 80), center=True)
        panel = pygame.Rect(170, 170, 940, 330)
        draw_panel(self.screen, panel, alpha=225)
        if self.story_index < len(self.story_lines):
            current = self.story_lines[self.story_index][: self.story_char]
            lines = wrap_text(current, FONT_LG, panel.width - 100)
            y = panel.y + 90
            for line in lines:
                draw_text(self.screen, line, FONT_LG, WHITE, (panel.centerx, y), center=True)
                y += 50
            draw_text(
                self.screen,
                f"{self.story_index + 1}/{len(self.story_lines)}",
                FONT_SM,
                (210, 180, 120),
                (panel.centerx, panel.bottom - 35),
                center=True,
            )
        draw_text(self.screen, "Nhấn SPACE / ENTER hoặc nút TIẾP", FONT_SM, (210, 200, 180), (WIDTH // 2, 540), center=True)
        self.buttons["skip"].draw(self.screen, mouse)
        self.buttons["next"].draw(self.screen, mouse)

    def draw_guide(self) -> None:
        mouse = pygame.mouse.get_pos()
        self.draw_cinematic_background(title_mode=False)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, "HƯỚNG DẪN CHƠI", FONT_XL, GOLD, (WIDTH // 2, 70), center=True)
        rect = pygame.Rect(120, 130, 1040, 450)
        draw_panel(self.screen, rect, alpha=225)
        guide_lines = [
            "1. Ở menu: chọn bằng chuột.",
            "2. Khi vào trận: dùng ngón trỏ chạm vào vòng trống đúng nhịp để triệu lính.",
            "3. Combo 10 / 20 / 30 / 50 tự gọi Tướng lĩnh. Sau 50, mỗi 10 combo gọi lại tướng mốc 50.",
            "4. Màn 2: giơ 5 ngón tay để gọi một tốp quân viện trợ.",
            "5. Màn 3: nắm tay lại để gọi Đại Tướng Mê Linh.",
            "6. Nếu chưa có camera: dùng chuột để đánh nốt. Nhấn C để mở lại camera, M bật/tắt chuột test.",
            "7. Thêm nhạc bằng assets/level1.mp3, level2.mp3, level3.mp3.",
            "8. Muốn nốt khớp nhạc nhất: tạo assets/beatmap_level1.txt, mỗi dòng là một thời điểm giây.",
        ]
        y = rect.y + 40
        for line in guide_lines:
            draw_text(self.screen, line, FONT_MD, WHITE, (rect.x + 45, y))
            y += 42
        self.buttons["back"].draw(self.screen, mouse)

    def level_card_rect(self, level: int) -> pygame.Rect:
        w, h = 320, 380
        gap = 42
        start_x = (WIDTH - (w * 3 + gap * 2)) // 2
        return pygame.Rect(start_x + (level - 1) * (w + gap), 170, w, h)

    def draw_level_select(self) -> None:
        mouse = pygame.mouse.get_pos()
        self.draw_cinematic_background(title_mode=False)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 95))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, "CHỌN CHIẾN DỊCH", FONT_XL, GOLD, (WIDTH // 2, 80), center=True)
        for level in (1, 2, 3):
            cfg = LEVELS[level]
            rect = self.level_card_rect(level)
            enabled = level <= self.unlocked_level
            hover = rect.collidepoint(mouse) and enabled
            card = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(card, (34, 30, 32, 225) if enabled else (28, 28, 32, 190), card.get_rect(), border_radius=22)
            pygame.draw.rect(card, GOLD if hover else (150, 110, 70), card.get_rect(), 3, border_radius=22)
            # Mini artwork
            art_rect = pygame.Rect(20, 22, rect.width - 40, 130)
            pygame.draw.rect(card, lerp_color(SKY_TOP, SKY_BOTTOM, level / 4), art_rect, border_radius=14)
            pygame.draw.circle(card, (170, 54, 42), (art_rect.right - 55, art_rect.y + 42), 34)
            pygame.draw.rect(card, (70, 45, 36), (art_rect.x, art_rect.bottom - 30, art_rect.width, 30), border_bottom_left_radius=14, border_bottom_right_radius=14)
            # Castle icon
            draw_mini_castle(card, art_rect.x + 60, art_rect.bottom - 28, True)
            draw_mini_castle(card, art_rect.right - 60, art_rect.bottom - 28, False)
            # Text
            draw_text(card, cfg.title, FONT_MD, GOLD if enabled else (120, 120, 128), (rect.width // 2, 180), center=True)
            sub_lines = wrap_text(cfg.subtitle, FONT_SM, rect.width - 48)
            ty = 222
            for line in sub_lines:
                draw_text(card, line, FONT_SM, WHITE if enabled else (130, 130, 140), (rect.width // 2, ty), center=True)
                ty += 26
            diff = ["Dễ", "Trung bình", "Khó"][level - 1]
            draw_text(card, f"Độ khó: {diff}", FONT_SM, (224, 196, 120), (rect.width // 2, 310), center=True)
            if not enabled:
                lock = pygame.Surface(rect.size, pygame.SRCALPHA)
                lock.fill((0, 0, 0, 120))
                card.blit(lock, (0, 0))
                draw_text(card, "KHÓA", FONT_LG, RED, (rect.width // 2, rect.height // 2), center=True)
            else:
                draw_text(card, "Nhấn để vào trận", FONT_SM, (180, 230, 190), (rect.width // 2, 346), center=True)
            self.screen.blit(card, rect.topleft)
        if self.battle_message_timer > 0:
            draw_text(self.screen, self.battle_message, FONT_MD, RED, (WIDTH // 2, 605), center=True)
        self.buttons["back"].draw(self.screen, mouse)

    def draw_cutscene(self) -> None:
        self.draw_cinematic_background(title_mode=False)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        self.screen.blit(overlay, (0, 0))
        # Chữ lần lượt fade in
        base_y = 190
        for i, line in enumerate(self.cutscene_lines):
            delay = i * 0.9
            alpha = int(255 * clamp((self.scene_time - delay) / 0.8, 0, 1))
            font = FONT_TITLE if i == 0 else FONT_LG
            color = GOLD if i == 0 else WHITE
            y = base_y + i * 110
            for sub in wrap_text(line, font, 940):
                draw_text(self.screen, sub, font, color, (WIDTH // 2, y), center=True, alpha=alpha)
                y += font.get_height() + 6
        blink = int(160 + 95 * (0.5 + 0.5 * math.sin(self.global_time * 4)))
        draw_text(self.screen, "Click chuột để bắt đầu", FONT_MD, (235, 220, 180), (WIDTH // 2, 650), center=True, alpha=blink)

    def draw_result(self) -> None:
        mouse = pygame.mouse.get_pos()
        self.draw_cinematic_background(title_mode=False)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        title = "CHIẾN THẮNG!" if self.result_victory else "THẤT THỦ!"
        color = GOLD if self.result_victory else RED
        draw_text(self.screen, title, FONT_TITLE, color, (WIDTH // 2, 145), center=True)
        panel = pygame.Rect(390, 245, 500, 250)
        draw_panel(self.screen, panel, alpha=220, border=color)
        lines = [
            f"Màn: {self.current_level}",
            f"Điểm: {self.score}",
            f"Combo cao nhất: {self.max_combo}",
            f"Nguồn beat: {self.beat_source}",
        ]
        y = panel.y + 45
        for line in lines:
            draw_text(self.screen, line, FONT_MD, WHITE, (panel.centerx, y), center=True)
            y += 42
        if self.result_victory and self.current_level < 3:
            self.buttons["continue"].draw(self.screen, mouse)
        self.buttons["menu"].draw(self.screen, mouse)
        self.buttons["level_select"].draw(self.screen, mouse)

    # ------------------------- BATTLE DRAW -------------------------
    def draw_battle(self) -> None:
        # Vẽ battle vào surface riêng để áp dụng camera shake.
        world = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.draw_battle_background(world)
        offset = self.shake_offset

        # Thành và lane
        draw_indie_castle(world, LEFT_CASTLE_X, "left", self.player_castle.ratio, self.current_level, offset)
        draw_indie_castle(world, RIGHT_CASTLE_X, "right", self.enemy_castle.ratio, self.current_level, offset)

        # Đơn vị: vẽ theo lane/y để có chiều sâu.
        all_units = sorted(self.allies + self.enemies, key=lambda u: (u.lane, u.y, u.x))
        for u in all_units:
            u.draw(world, offset)

        # Notes trên cùng world nhưng không bị shake quá mạnh? vẫn ok.
        now = time.time()
        for note in self.notes:
            note.draw(world, now)

        self.particles.draw(world, offset)
        self.screen.blit(world, (0, 0))
        self.draw_battle_hud()
        self.draw_camera_preview()
        self.draw_cursor()

    def draw_battle_background(self, surface: pygame.Surface) -> None:
        draw_gradient_background(surface, (28, 36, 55), (111, 73, 50))
        # mây/khói xa
        for i in range(7):
            x = (i * 230 + int(self.global_time * 12)) % (WIDTH + 260) - 130
            y = 70 + (i % 3) * 38
            pygame.draw.ellipse(surface, (45, 49, 58), (x, y, 220, 45))
        # mặt đất
        pygame.draw.rect(surface, (55, 42, 31), (0, GROUND_TOP, WIDTH, HEIGHT - GROUND_TOP))
        # 3 đường song song
        for idx, y in enumerate(LANE_Y):
            road = pygame.Rect(180, y - 38, 920, 76)
            pygame.draw.rect(surface, (95, 70, 43), road, border_radius=22)
            pygame.draw.rect(surface, (142, 104, 57), road, 3, border_radius=22)
            pygame.draw.line(surface, (200, 158, 86), (road.left + 20, y), (road.right - 20, y), 2)
            draw_text(surface, LANE_NAMES[idx], FONT_XS, (190, 160, 105), (road.left + 14, road.top + 6))
        # Cờ / cọc
        for x in range(260, 1020, 150):
            pygame.draw.line(surface, DARK_BROWN, (x, 245), (x, 290), 4)
            pygame.draw.polygon(surface, RED if x % 300 == 0 else (62, 75, 112), [(x, 245), (x + 45, 258), (x, 275)])
        # Lửa cố định dưới góc
        if random.random() < 0.18:
            self.particles.spawn_fire(random.choice([75, 1200]), random.randint(610, 690), 1)

    def draw_battle_hud(self) -> None:
        # HUD top
        top_panel = pygame.Surface((WIDTH, 96), pygame.SRCALPHA)
        top_panel.fill((0, 0, 0, 125))
        self.screen.blit(top_panel, (0, 0))
        draw_text(self.screen, LEVELS[self.current_level].title, FONT_MD, GOLD, (WIDTH // 2, 18), center=True)
        draw_text(self.screen, f"Score: {self.score}", FONT_SM, WHITE, (WIDTH // 2, 55), center=True)

        self.draw_hp_bar(24, 20, 330, 18, self.player_castle.ratio, "Thành ta", self.player_castle.hp, self.player_castle.max_hp)
        self.draw_hp_bar(WIDTH - 354, 20, 330, 18, self.enemy_castle.ratio, "Thành địch", self.enemy_castle.hp, self.enemy_castle.max_hp)
        # Combo bên trái dưới thanh HP
        draw_text(self.screen, f"COMBO: {self.combo}", FONT_LG, GOLD, (24, 52))
        draw_text(self.screen, f"MAX: {self.max_combo}", FONT_SM, WHITE, (210, 64))
        draw_text(self.screen, f"Lệnh gọi lính: {self.pending_ally_summons}", FONT_XS, (215, 200, 160), (24, 84))

        # Skill HUD
        now = time.time()
        y = 612
        draw_panel(self.screen, pygame.Rect(18, y - 8, 405, 92), alpha=165, border=(130, 95, 55))
        if self.current_level >= 2:
            rem = self.skill_manager.reinforce.remaining(now)
            txt = "5 NGÓN: VIỆN TRỢ SẴN SÀNG" if rem <= 0 else f"5 NGÓN: VIỆN TRỢ {rem:.0f}s"
            draw_text(self.screen, txt, FONT_SM, GREEN if rem <= 0 else WHITE, (32, y + 4))
        else:
            draw_text(self.screen, "Màn 2 mở khóa: 5 ngón gọi viện trợ", FONT_SM, (170, 170, 170), (32, y + 4))
        if self.current_level >= 3:
            rem = self.skill_manager.great_general.remaining(now)
            txt = "NẮM TAY: ĐẠI TƯỚNG SẴN SÀNG" if rem <= 0 else f"NẮM TAY: ĐẠI TƯỚNG {rem:.0f}s"
            draw_text(self.screen, txt, FONT_SM, GOLD if rem <= 0 else WHITE, (32, y + 38))
        else:
            draw_text(self.screen, "Màn 3 mở khóa: nắm tay gọi Đại Tướng", FONT_SM, (170, 170, 170), (32, y + 38))

        draw_text(self.screen, f"Beat: {self.beat_source}", FONT_XS, (210, 200, 180), (WIDTH - 330, HEIGHT - 28))

    def draw_hp_bar(self, x: int, y: int, w: int, h: int, ratio: float, label: str, hp: int, max_hp: int) -> None:
        pygame.draw.rect(self.screen, (64, 24, 24), (x, y, w, h), border_radius=7)
        hp_col = GREEN if ratio > 0.45 else GOLD if ratio > 0.22 else RED
        pygame.draw.rect(self.screen, hp_col, (x, y, int(w * ratio), h), border_radius=7)
        pygame.draw.rect(self.screen, WHITE, (x, y, w, h), 1, border_radius=7)
        draw_text(self.screen, f"{label}: {hp}/{max_hp}", FONT_XS, WHITE, (x, y + 22))

    def draw_camera_preview(self) -> None:
        panel = pygame.Rect(WIDTH - 250, 104, 230, 150)
        pygame.draw.rect(self.screen, (0, 0, 0), panel, border_radius=12)
        pygame.draw.rect(self.screen, GOLD, panel, 2, border_radius=12)
        if self.hand_state.camera_rgb is not None:
            try:
                rgb = self.hand_state.camera_rgb
                if np is not None:
                    # frombuffer chuẩn hơn rotate surfarray.
                    h, w = rgb.shape[:2]
                    surf = pygame.image.frombuffer(rgb.tobytes(), (w, h), "RGB")
                    surf = pygame.transform.scale(surf, (panel.width - 8, panel.height - 30))
                    self.screen.blit(surf, (panel.x + 4, panel.y + 4))
            except Exception:
                pass
        draw_text(self.screen, self.hand_state.message or "Camera", FONT_XS, WHITE, (panel.centerx, panel.bottom - 14), center=True)
        if not self.hand_state.has_hand:
            draw_text(self.screen, "Nhấn C mở lại camera | M bật/tắt chuột", FONT_XS, (230, 210, 150), (panel.centerx, panel.bottom + 14), center=True)

    def draw_cursor(self) -> None:
        cursor = self.get_cursor_for_battle()
        if cursor:
            x, y = cursor
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y), 14, 2)
            pygame.draw.circle(self.screen, RED, (x, y), 5)


def draw_mini_castle(surface: pygame.Surface, x: int, base_y: int, left: bool) -> None:
    color = (120, 82, 60) if left else (85, 72, 78)
    pygame.draw.rect(surface, color, (x - 28, base_y - 50, 56, 50))
    pygame.draw.rect(surface, (35, 25, 25), (x - 28, base_y - 50, 56, 50), 2)
    pygame.draw.rect(surface, color, (x - 38, base_y - 65, 18, 65))
    pygame.draw.rect(surface, color, (x + 20, base_y - 65, 18, 65))
    pygame.draw.polygon(surface, DARK_RED if left else BLUE, [(x - 42, base_y - 65), (x - 29, base_y - 88), (x - 16, base_y - 65)])
    pygame.draw.polygon(surface, DARK_RED if left else BLUE, [(x + 16, base_y - 65), (x + 29, base_y - 88), (x + 42, base_y - 65)])


# =========================
# 6. CHẠY GAME
# =========================

if __name__ == "__main__":
    try:
        game = MelinhGame()
        game.run()
    except Exception as exc:
        # In lỗi rõ hơn để dễ gửi cho ChatGPT sửa tiếp.
        print("\nGAME BỊ LỖI:")
        print(type(exc).__name__, exc)
        print("\nGợi ý: kiểm tra đã cài pygame, opencv-python, mediapipe, numpy chưa.")
        raise
