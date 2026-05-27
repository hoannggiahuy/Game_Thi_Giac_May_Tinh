from skill_system_pygame import HandGestureTracker
import time
import sys

try:
    import pygame
except Exception:
    print("Chưa cài pygame. Chạy: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt")
    raise

WIDTH, HEIGHT = 800, 450
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mê Linh Camera Test V8 - ESC thoát, C mở lại")
font = pygame.font.SysFont("Arial", 22)
small = pygame.font.SysFont("Arial", 16)
tracker = HandGestureTracker(cam_width=640, cam_height=360)
clock = pygame.time.Clock()
running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            running = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_c:
            tracker.release()
            tracker = HandGestureTracker(cam_width=640, cam_height=360)
    state = tracker.update(WIDTH, HEIGHT)
    screen.fill((20, 20, 28))
    if state.camera_rgb is not None:
        try:
            h, w = state.camera_rgb.shape[:2]
            surf = pygame.image.frombuffer(state.camera_rgb.tobytes(), (w, h), "RGB")
            surf = pygame.transform.scale(surf, (WIDTH, HEIGHT))
            screen.blit(surf, (0, 0))
        except Exception as exc:
            txt = font.render(f"Lỗi vẽ camera: {exc}", True, (255, 80, 80))
            screen.blit(txt, (12, 48))
    if state.pointer:
        pygame.draw.circle(screen, (255, 0, 0), state.pointer, 12)
    pygame.draw.rect(screen, (0, 0, 0), (0, 0, WIDTH, 72))
    msg = state.message or "Đưa tay vào camera"
    img = font.render(msg, True, (255, 255, 255))
    screen.blit(img, (12, 10))
    info = small.render("ESC thoát | C mở lại camera | Nếu vẫn lỗi, gửi dòng thông báo này cho ChatGPT", True, (220, 220, 180))
    screen.blit(info, (12, 44))
    pygame.display.flip()
    clock.tick(30)
tracker.release()
pygame.quit()
