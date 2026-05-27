🥁 TIẾNG TRỐNG MÊ LINH
A Vietnamese Rhythm Strategy Game powered by Computer Vision
<p align="center"> <img src="https://img.shields.io/badge/Python-3.10+-blue"> 
<img src="https://img.shields.io/badge/Pygame-2.6-green">
<img src="https://img.shields.io/badge/OpenCV-AI-red"> <img src="https://img.shields.io/badge/MediaPipe-HandTracking-orange"> </p>
📖 Giới thiệu

Tiếng Trống Mê Linh là một game rhythm chiến thuật thời gian thực lấy cảm hứng từ cuộc khởi nghĩa Hai Bà Trưng.

Người chơi không điều khiển quân đội trực tiếp bằng bàn phím, mà sử dụng:

🖐️ Cử chỉ tay qua camera
🥁 Nhịp điệu âm nhạc
⚔️ Combo chiến đấu
🎵 Beat synchronization

để triệu hồi nghĩa quân, kích hoạt kỹ năng và phá tan quân Đông Hán.

Game được xây dựng bằng:

Python
Pygame
OpenCV
MediaPipe Hand Tracking
🎮 Gameplay
🔥 Cơ chế chính

Game kết hợp giữa:

Thể loại	Vai trò
Rhythm Game	Bắt đúng nhịp xuất hiện
Strategy Defense	Giữ 3 tuyến phòng thủ
Computer Vision	Điều khiển bằng tay
Cinematic Storytelling	Cốt truyện lịch sử
🥁 Cách chơi
🎯 Mục tiêu
Giữ vững thành Mê Linh
Phá hủy thành Đông Hán
Duy trì combo cao nhất có thể
🖐️ Điều khiển bằng tay
Cử chỉ	Chức năng
☝️ Trỏ tay	Đánh nốt nhạc
🖐️ Giơ 5 ngón	Gọi viện binh
✊ Nắm tay	Triệu hồi Đại Tướng
🎯 Di chuyển tay	Điều khiển con trỏ

Hệ thống sử dụng MediaPipe Hands AI Tracking để nhận diện tay theo thời gian thực.

⚔️ Hệ thống chiến đấu
🏰 Battle 3 Lane

Game có 3 tuyến chiến đấu:

Đường trên
Đường giữa
Đường dưới

Mỗi lane đều có:

quân địch
lính nghĩa quân
elite units
boss
👑 Combo System

Khi combo tăng:

Combo	Phần thưởng
x10	Triệu hồi tướng
x20	Tướng mạnh hơn
x30	General AoE
x50	Đại quân Mê Linh
💥 Hiệu ứng chiến trường

Game có nhiều cinematic effect:

🔥 Lửa
🌫️ Khói
⚡ Tia chém
💨 Bụi chiến trường
📳 Rung màn hình

được render realtime bằng Pygame particle system.

🎵 Âm nhạc & Rhythm System
🥁 Beat-based Gameplay

Các nốt nhạc xuất hiện theo beat thực của bài nhạc:

Màn	Tốc độ
Màn 1	1.00s / note
Màn 2	0.75s / note
Màn 3	0.55s / note

Hệ thống beatmap hỗ trợ:

MP3
WAV
Auto beat detection bằng Librosa

🎼 Không khí âm nhạc

Game hướng tới cảm giác:

Hùng tráng
Bi tráng
Khí thế khởi nghĩa
Trống trận cổ đại Việt Nam

Âm nhạc đóng vai trò như “nhịp tim của nghĩa quân”.

📜 Cốt truyện
🐉 Bối cảnh

Năm 40 sau Công Nguyên.

Đất Giao Chỉ chìm trong ách đô hộ Đông Hán.
Từ vùng đất Mê Linh, Hai Bà Trưng dựng cờ khởi nghĩa.

Người chơi không phải một vị tướng.

Bạn là:

“Người giữ nhịp trống chiến trận.”

Mỗi nhịp trống vang lên sẽ:

triệu hồi quân sĩ
tiếp thêm sĩ khí
thay đổi cục diện chiến tranh
🏯 Các màn chơi
🥁 Màn 1 — Mê Linh nổi trống
Làm quen gameplay
Nghĩa quân tập hợp
Nhịp độ chậm
🔥 Màn 2 — Cổ Loa khói lửa
Địch đông hơn
Mở khóa skill viện binh
Battle bắt đầu hỗn loạn
⚔️ Màn 3 — Luy Lâu quyết chiến
Boss Đông Hán xuất hiện
Combo tốc độ cao
Triệu hồi Đại Tướng Mê Linh
🧠 AI & Computer Vision

Game sử dụng:

OpenCV
MediaPipe Hands

để:

nhận diện vị trí tay
đếm số ngón
nhận diện nắm tay
làm mượt con trỏ
tracking realtime

🛠️ Công nghệ sử dụng
Công nghệ	Vai trò
Python	Core game
Pygame	Rendering
OpenCV	Camera input
MediaPipe	Hand tracking AI
NumPy	Xử lý dữ liệu
Librosa	Beat detection
📦 Cài đặt
1️⃣ Clone project
git clone <your-repository>
cd melinh-game
2️⃣ Tạo virtual environment
python -m venv .venv
3️⃣ Activate môi trường
Windows
.\.venv\Scripts\activate
macOS/Linux
source .venv/bin/activate
4️⃣ Cài thư viện
pip install -r requirements.txt

Dependencies hiện tại:

pygame
opencv-python
mediapipe
numpy
mutagen
▶️ Chạy game
python game_melinh_pygame_full_v8.py
📷 Nếu camera không hoạt động
Thử reset camera trong game

Nhấn:

C

để reconnect webcam.

Nếu máy có nhiều webcam
$env:MELINH_CAMERA="1"
python game_melinh_pygame_full_v8.py
🎨 Điểm nổi bật

✅ Điều khiển bằng cử chỉ tay
✅ Rhythm gameplay theo beat thật
✅ Battle 3 lane realtime
✅ Combo summon system
✅ Boss fight cinematic
✅ Particle effects
✅ Vietnamese historical theme
✅ AI-powered interaction

📸 Screenshots

Thêm screenshot gameplay tại đây

Ví dụ:

![menu](images/menu.png)
![battle](images/battle.png)
![boss](images/boss.png)
🚀 Ý tưởng tương lai
Multiplayer co-op
Online leaderboard
Story campaign dài hơn
Voice acting
Dynamic soundtrack
Full animated cutscene
Steam release
❤️ Ý nghĩa dự án

“Tiếng Trống Mê Linh” không chỉ là một game.

Đây là thử nghiệm kết hợp giữa:

lịch sử Việt Nam
AI Computer Vision
âm nhạc
chiến thuật thời gian thực

thành một trải nghiệm tương tác hiện đại.

👨‍💻 Tác giả

Huy Hoàng Đình Gia
Nguyễn Phương Anh

📜 License

MIT License

⭐ Nếu bạn thích dự án

Hãy để lại ⭐ trên GitHub để ủng hộ dự án!
