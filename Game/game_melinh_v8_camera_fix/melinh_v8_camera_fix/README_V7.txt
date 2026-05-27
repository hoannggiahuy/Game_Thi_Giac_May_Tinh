TIẾNG TRỐNG MÊ LINH - V7 BALANCED + GESTURE FIX

Chạy game:
    pip install -r requirements.txt
    python game_melinh_pygame_full_v7.py

Nếu camera không nhận:
    - Vào trận rồi nhấn phím C để mở lại camera.
    - Nhấn M để bật/tắt chuột test trong battle.
    - Nếu máy có nhiều camera, thử chạy:
        PowerShell:
        $env:MELINH_CAMERA="1"
        python game_melinh_pygame_full_v7.py

Thay đổi V7:
    - Sửa tracker camera: thử nhiều camera/backend trên Windows, hạ ngưỡng nhận diện, làm mượt con trỏ tay.
    - Nhịp nốt chậm hơn: màn 1 = 1.00s, màn 2 = 0.75s, màn 3 = 0.55s.
    - Trận chậm hơn bằng BATTLE_TIME_SCALE.
    - Lính ta không spawn ồ ạt ngay mỗi nốt nữa: nốt đúng tạo lệnh gọi lính, lính xuất trận theo cooldown.
    - Có giới hạn quân thường mỗi lane và toàn bản đồ để tránh mất cân bằng.
    - Thành nhiều máu hơn, địch spawn chậm hơn, tốc độ quân chậm hơn để game không kết thúc quá sớm.
