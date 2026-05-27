"""
skill_system_pygame.py - V8 camera fix

Sửa lỗi thường gặp trên Windows:
- module 'mediapipe' has no attribute 'solutions'
- camera không mở được khi nhấn C
- nhận diện tay không ổn định

Game vẫn chạy bằng chuột nếu camera/mediapipe lỗi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import os
import time


@dataclass
class HandState:
    has_hand: bool = False
    pointer: Optional[Tuple[int, int]] = None
    fingers_count: int = 0
    is_open_palm: bool = False
    is_fist: bool = False
    camera_rgb: object = None
    message: str = ""


class HandGestureTracker:
    """Bọc OpenCV + MediaPipe để game chính chỉ cần gọi update()."""

    def __init__(self, camera_index: int = 0, cam_width: int = 640, cam_height: int = 360):
        self.available = False
        self.cv2 = None
        self.mp_hands = None
        self.hands = None
        self.cap = None
        self.camera_index = camera_index
        self.cam_width = cam_width
        self.cam_height = cam_height
        self._smooth_pointer: Optional[Tuple[int, int]] = None
        self.last_state = HandState(message="Camera chưa sẵn sàng")
        self.debug_info = ""

        try:
            import cv2  # type: ignore
            self.cv2 = cv2
        except Exception as exc:
            self.last_state.message = f"Thiếu OpenCV: {exc}"
            return

        try:
            self.mp_hands, self.debug_info = self._load_mediapipe_hands()
        except Exception as exc:
            self.last_state.message = f"Không dùng camera: MediaPipe lỗi: {exc}"
            return

        try:
            self.hands = self._create_hands_solution()
        except Exception as exc:
            self.last_state.message = f"Không tạo được Hands: {exc}"
            return

        self.cap, used_index = self._open_camera(camera_index, cam_width, cam_height)
        if self.cap is not None and self.cap.isOpened():
            self.available = True
            self.camera_index = used_index
            self.last_state.message = f"Camera #{used_index} sẵn sàng"
        else:
            self.last_state.message = "Không mở được camera. Đóng app Camera/Zoom rồi nhấn C."

    def _load_mediapipe_hands(self):
        """
        Một số máy gặp lỗi: module 'mediapipe' has no attribute 'solutions'.
        Vì vậy thử 2 cách import:
        1) import mediapipe as mp; mp.solutions.hands
        2) from mediapipe.python.solutions import hands
        """
        import importlib
        import mediapipe as mp  # type: ignore

        mp_path = getattr(mp, "__file__", "không rõ đường dẫn mediapipe")

        # Cách cũ, thường dùng nhất.
        try:
            solutions = getattr(mp, "solutions")
            hands_module = getattr(solutions, "hands")
            return hands_module, f"MediaPipe OK: mp.solutions.hands | {mp_path}"
        except Exception:
            pass

        # Cách fallback cho vài bản MediaPipe/Windows bị thiếu attribute solutions ở root module.
        try:
            hands_module = importlib.import_module("mediapipe.python.solutions.hands")
            return hands_module, f"MediaPipe OK: mediapipe.python.solutions.hands | {mp_path}"
        except Exception as exc:
            # Thêm gợi ý nếu bị shadow bởi file/folder local.
            local_hint = ""
            cwd_mp_py = os.path.join(os.getcwd(), "mediapipe.py")
            cwd_mp_dir = os.path.join(os.getcwd(), "mediapipe")
            if os.path.exists(cwd_mp_py) or os.path.exists(cwd_mp_dir):
                local_hint = " | Có file/thư mục mediapipe trong project, hãy đổi tên nó."
            raise RuntimeError(f"không import được Hands ({exc}). Đường dẫn mediapipe: {mp_path}{local_hint}")

    def _create_hands_solution(self):
        # model_complexity không có ở một số bản cũ nên có fallback TypeError.
        try:
            return self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.45,
                min_tracking_confidence=0.40,
            )
        except TypeError:
            return self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.45,
                min_tracking_confidence=0.40,
            )

    def _open_camera(self, camera_index: int, cam_width: int, cam_height: int):
        """Thử nhiều backend/camera để sửa lỗi Windows/VS Code không mở được webcam."""
        cv2 = self.cv2
        if cv2 is None:
            return None, camera_index

        indices = []
        env_cam = os.environ.get("MELINH_CAMERA")
        if env_cam is not None:
            try:
                indices.append(int(env_cam))
            except ValueError:
                pass
        indices.extend([camera_index, 0, 1, 2, 3])

        unique_indices = []
        for idx in indices:
            if idx not in unique_indices:
                unique_indices.append(idx)

        backends = []
        # DSHOW thường ổn hơn MSMF trên Windows; vẫn thử cả hai.
        for name in ("CAP_DSHOW", "CAP_MSMF", "CAP_ANY"):
            if hasattr(cv2, name):
                backends.append(getattr(cv2, name))
        backends.append(None)

        for idx in unique_indices:
            for backend in backends:
                cap = None
                try:
                    cap = cv2.VideoCapture(idx) if backend is None else cv2.VideoCapture(idx, backend)
                    cap.set(3, cam_width)
                    cap.set(4, cam_height)
                    if hasattr(cv2, "CAP_PROP_FPS"):
                        cap.set(cv2.CAP_PROP_FPS, 30)
                    if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if cap is not None and cap.isOpened():
                        # đọc vài frame để webcam có thời gian bật.
                        ok = False
                        for _ in range(5):
                            ok, _frame = cap.read()
                            if ok:
                                break
                            time.sleep(0.06)
                        if ok:
                            return cap, idx
                    if cap is not None:
                        cap.release()
                except Exception:
                    try:
                        if cap is not None:
                            cap.release()
                    except Exception:
                        pass
        return None, camera_index

    def update(self, screen_width: int, screen_height: int) -> HandState:
        if not self.available or self.cap is None or self.cv2 is None or self.hands is None:
            return self.last_state

        ok, frame = self.cap.read()
        if not ok:
            self.last_state = HandState(message="Không đọc được camera. Nhấn C để mở lại.")
            return self.last_state

        cv2 = self.cv2
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        try:
            rgb.flags.writeable = False
        except Exception:
            pass
        try:
            result = self.hands.process(rgb)
        except Exception as exc:
            self.last_state = HandState(camera_rgb=rgb, message=f"MediaPipe process lỗi: {exc}")
            return self.last_state
        try:
            rgb.flags.writeable = True
        except Exception:
            pass

        state = HandState(has_hand=False, camera_rgb=rgb, message=f"Đưa tay vào khung camera | Cam {self.camera_index}")
        if getattr(result, "multi_hand_landmarks", None):
            lm = result.multi_hand_landmarks[0].landmark
            index_tip = lm[8]
            raw_pointer = (int(index_tip.x * screen_width), int(index_tip.y * screen_height))
            pointer = self._smooth(raw_pointer)
            fingers = self._count_fingers(lm)
            is_fist = self._is_fist(lm)

            state.has_hand = True
            state.pointer = pointer
            state.fingers_count = fingers
            state.is_open_palm = fingers >= 5
            state.is_fist = is_fist
            state.message = f"Tay: {fingers} ngón | Cam {self.camera_index}" + (" | Nắm tay" if is_fist else "")

        self.last_state = state
        return state

    def _smooth(self, pointer: Tuple[int, int]) -> Tuple[int, int]:
        if self._smooth_pointer is None:
            self._smooth_pointer = pointer
            return pointer
        alpha = 0.48
        sx, sy = self._smooth_pointer
        nx = int(sx * (1 - alpha) + pointer[0] * alpha)
        ny = int(sy * (1 - alpha) + pointer[1] * alpha)
        self._smooth_pointer = (nx, ny)
        return self._smooth_pointer

    def _count_fingers(self, lm) -> int:
        pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]
        long_count = 0
        for tip, pip in pairs:
            if lm[tip].y < lm[pip].y - 0.012:
                long_count += 1

        # Thumb tương đối: nếu đầu ngón cái cách khớp cái đủ xa thì coi là mở.
        thumb_extended = abs(lm[4].x - lm[2].x) > 0.045 or abs(lm[4].y - lm[2].y) > 0.045
        if long_count >= 4:
            return 5
        return long_count + (1 if thumb_extended else 0)

    def _is_fist(self, lm) -> bool:
        folded = 0
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            if lm[tip].y > lm[pip].y - 0.008:
                folded += 1
        index_near_palm = abs(lm[8].x - lm[0].x) + abs(lm[8].y - lm[0].y) < 0.46
        middle_near_palm = abs(lm[12].x - lm[0].x) + abs(lm[12].y - lm[0].y) < 0.46
        return folded >= 4 and (index_near_palm or middle_near_palm)

    def release(self) -> None:
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        try:
            if self.hands is not None:
                self.hands.close()
        except Exception:
            pass


class SkillCooldown:
    def __init__(self, cooldown_seconds: float):
        self.cooldown = float(cooldown_seconds)
        self.last_used = -9999.0

    def ready(self, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        return now - self.last_used >= self.cooldown

    def use(self, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        if self.ready(now):
            self.last_used = now
            return True
        return False

    def remaining(self, now: Optional[float] = None) -> float:
        now = time.time() if now is None else now
        return max(0.0, self.cooldown - (now - self.last_used))


class SkillManager:
    """Quản lý cooldown skill theo màn."""

    def __init__(self):
        self.reinforce = SkillCooldown(22.0)
        self.great_general = SkillCooldown(45.0)
        self._open_palm_hold_start = 0.0
        self._fist_hold_start = 0.0

    def update_and_check_reinforce(self, level: int, hand_state: HandState, now: float, hold_time: float = 0.25) -> bool:
        if level < 2:
            return False
        if hand_state.has_hand and hand_state.is_open_palm:
            if self._open_palm_hold_start <= 0:
                self._open_palm_hold_start = now
            if now - self._open_palm_hold_start >= hold_time:
                self._open_palm_hold_start = now + 0.8
                return self.reinforce.use(now)
        else:
            self._open_palm_hold_start = 0.0
        return False

    def update_and_check_great_general(self, level: int, hand_state: HandState, now: float, hold_time: float = 0.25) -> bool:
        if level < 3:
            return False
        if hand_state.has_hand and hand_state.is_fist:
            if self._fist_hold_start <= 0:
                self._fist_hold_start = now
            if now - self._fist_hold_start >= hold_time:
                self._fist_hold_start = now + 0.8
                return self.great_general.use(now)
        else:
            self._fist_hold_start = 0.0
        return False
