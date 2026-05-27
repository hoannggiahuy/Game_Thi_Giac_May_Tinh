TIẾNG TRỐNG MÊ LINH - V8 CAMERA FIX

Lỗi bạn gặp trong ảnh:
    Không dùng camera: module 'mediapipe' has no attribute 'solutions'

Bản V8 đã sửa bằng cách import MediaPipe Hands theo 2 kiểu:
1) mp.solutions.hands
2) mediapipe.python.solutions.hands

Cách cài lại thư viện sạch:
    cd D:\ThiGiacMayTinh\Game\melinh_v8_camera_fix
    .\.venv\Scripts\python.exe -m pip uninstall -y mediapipe opencv-python numpy
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Test camera trước:
    .\.venv\Scripts\python.exe camera_test.py

Chạy game:
    .\.venv\Scripts\python.exe game_melinh_pygame_full_v8.py

Nếu camera vẫn đen hoặc không mở:
    Đóng Camera/Zoom/Zalo/Teams/OBS rồi nhấn C trong game.

Nếu máy có nhiều webcam:
    $env:MELINH_CAMERA="1"
    .\.venv\Scripts\python.exe camera_test.py
