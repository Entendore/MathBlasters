"""
MATH BLASTERS - A Math Space Shooter Game
Built with Pygame

Controls:
  ← → / A D    - Move spaceship
  Mouse move    - Move spaceship
  Number keys   - Type answer
  Enter         - Fire laser
  Backspace     - Delete last digit
  P / ESC       - Pause
"""

import pygame
import sys
import math
import random
import json
import os

# ============================================================
# INIT
# ============================================================
pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception:
    pass  # No audio hardware available

# Screen
WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Math Blasters")

# Clock
clock = pygame.time.Clock()
FPS = 60

# ============================================================
# COLORS
# ============================================================
BLACK       = (0, 0, 0)
WHITE       = (255, 255, 255)
CYAN        = (0, 204, 255)
GOLD        = (255, 215, 0)
RED         = (255, 68, 68)
GREEN       = (0, 255, 136)
DARK_BG     = (10, 10, 46)
BLUE_SHIP   = (68, 136, 255)
NEBULA1     = (100, 50, 150)
NEBULA2     = (150, 50, 50)

# ============================================================
# FONTS
# ============================================================
FONT_SMALL  = pygame.font.SysFont("monospace", 14, bold=True)
FONT_MED    = pygame.font.SysFont("monospace", 18, bold=True)
FONT_LARGE  = pygame.font.SysFont("monospace", 28, bold=True)
FONT_TITLE  = pygame.font.SysFont("monospace", 52, bold=True)
FONT_HUGE   = pygame.font.SysFont("monospace", 64, bold=True)
FONT_INPUT  = pygame.font.SysFont("monospace", 22, bold=True)
FONT_PROBLEM = pygame.font.SysFont("monospace", 16, bold=True)

# ============================================================
# SOUND ENGINE
# ============================================================
def generate_tone(frequency, duration_ms=150, volume=0.15, wave="square"):
    """Generate a tone as a pygame Sound object"""
    if not pygame.mixer.get_init():
        return None
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = bytearray(n_samples * 2)
    for i in range(n_samples):
        t = i / sample_rate
        env = max(0, 1 - i / n_samples)
        if wave == "square":
            val = 1 if math.sin(2 * math.pi * frequency * t) >= 0 else -1
        elif wave == "sawtooth":
            val = 2 * (frequency * t % 1) - 1
        elif wave == "sine":
            val = math.sin(2 * math.pi * frequency * t)
        else:
            val = math.sin(2 * math.pi * frequency * t)
        sample = int(val * volume * env * 32767)
        sample = max(-32768, min(32767, sample))
        buf[i*2]     = sample & 0xFF
        buf[i*2 + 1] = (sample >> 8) & 0xFF
    sound = pygame.mixer.Sound(buffer=bytes(buf))
    return sound

def generate_noise(duration_ms=300, volume=0.1):
    """Generate noise burst"""
    if not pygame.mixer.get_init():
        return None
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = bytearray(n_samples * 2)
    rng = random.Random(42)
    for i in range(n_samples):
        env = max(0, (1 - i / n_samples) ** 3)
        sample = int((rng.random() * 2 - 1) * volume * env * 32767)
        sample = max(-32768, min(32767, sample))
        buf[i*2]     = sample & 0xFF
        buf[i*2 + 1] = (sample >> 8) & 0xFF
    sound = pygame.mixer.Sound(buffer=bytes(buf))
    return sound

SFX_ENABLED = True
try:
    SFX_SHOOT    = generate_tone(800, 120, 0.08, "square")
    SFX_EXPLODE  = generate_noise(350, 0.15)
    SFX_WRONG    = generate_tone(200, 250, 0.1, "sawtooth")
    SFX_LOSE_LIFE = generate_tone(300, 200, 0.1, "square")
    SFX_LEVEL_UP = generate_tone(784, 200, 0.1, "square")
except Exception:
    SFX_ENABLED = False

def play_sfx(sound):
    if SFX_ENABLED and sound is not None:
        try:
            sound.play()
        except Exception:
            pass

# ============================================================
# STAR FIELD
# ============================================================
class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.size = random.uniform(0.5, 3.0)
        self.speed = random.uniform(0.1, 0.6)
        self.base_brightness = random.uniform(0.5, 1.0)

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, surface, time_ms):
        b = self.base_brightness + math.sin(time_ms * 0.002 * self.speed + self.x) * 0.3
        b = max(0, min(1, b))
        color = (int(255*b), int(255*b), int(255*b))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), max(1, int(self.size)))

# ============================================================
# PARTICLE
# ============================================================
class Particle:
    def __init__(self, x, y, color, speed_range=(1, 5), life_range=(0.3, 0.8)):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*speed_range)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(*life_range)
        self.max_life = self.life
        self.color = color
        self.size = random.uniform(1, 4)

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.05  # gravity
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        alpha = self.life / self.max_life
        r = max(1, int(self.size * alpha))
        color = tuple(int(c * alpha) for c in self.color[:3])
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), r)
        # glow
        glow_r = r * 3
        glow_surf = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
        glow_color = (*self.color[:3], int(40 * alpha))
        pygame.draw.circle(glow_surf, glow_color, (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (int(self.x) - glow_r, int(self.y) - glow_r))

# ============================================================
# THRUST PARTICLE
# ============================================================
class ThrustParticle:
    def __init__(self, x, y):
        self.x = x + random.uniform(-5, 5)
        self.y = y + 15
        self.life = 0.3
        self.max_life = 0.3
        self.size = random.uniform(3, 7)

    def update(self, dt):
        self.y += 2
        self.size *= 0.97
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        alpha = self.life / self.max_life
        r = max(1, int(self.size))
        glow_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        glow_color = (int(100*alpha), int(200*alpha), int(255*alpha), int(150*alpha))
        pygame.draw.circle(glow_surf, glow_color, (r, r), r)
        surface.blit(glow_surf, (int(self.x) - r, int(self.y) - r))

# ============================================================
# LASER
# ============================================================
class Laser:
    def __init__(self, x, y, target_asteroid=None):
        self.x = x
        self.y = y
        self.speed = 12
        self.width = 3
        self.target_asteroid = target_asteroid
        self.alive = True
        self.hit = False

    def update(self, dt):
        self.y -= self.speed
        return self.y > -20

    def draw(self, surface):
        # Main beam
        for i in range(30):
            alpha = 1 - i / 30
            r = max(0, int(0 + 0 * alpha))
            g = max(0, int(255 * alpha))
            b = max(0, int(255 * alpha))
            pygame.draw.line(surface, (r, g, b),
                             (int(self.x), int(self.y - i)),
                             (int(self.x), int(self.y - i - 1)), self.width)
        # Glow
        for i in range(20):
            alpha = 0.3 * (1 - i / 20)
            r = int(0 * alpha)
            g = int(255 * alpha)
            b = int(255 * alpha)
            pygame.draw.line(surface, (r, g, b),
                             (int(self.x), int(self.y - i)),
                             (int(self.x), int(self.y - i - 1)), self.width * 4)

# ============================================================
# ASTEROID
# ============================================================
ASTEROID_PALETTES = [
    ((139, 115, 85), (210, 105, 30)),
    ((105, 105, 105), (169, 169, 169)),
    ((139, 105, 20), (218, 165, 32)),
    ((95, 75, 59), (205, 133, 63)),
    ((85, 34, 34), (184, 134, 11)),
    ((127, 255, 0), (154, 205, 50)),
]

class Asteroid:
    def __init__(self, level, difficulty, operation):
        self.size = random.randint(28, 48) + level * 2
        self.x = random.randint(self.size, WIDTH - self.size)
        self.y = -self.size
        self.vx = random.uniform(-1, 1) * (1 + level * 0.3)
        self.vy = random.uniform(0.5, 1.0) + level * 0.15
        self.rotation = random.uniform(0, 2 * math.pi)
        self.rotation_speed = random.uniform(-0.03, 0.03)
        self.flash = 0

        # Generate shape
        n_verts = random.randint(8, 12)
        self.vertices = []
        for i in range(n_verts):
            angle = (i / n_verts) * 2 * math.pi
            r = self.size * random.uniform(0.7, 1.0)
            self.vertices.append((math.cos(angle) * r, math.sin(angle) * r))

        # Color
        palette = random.choice(ASTEROID_PALETTES)
        self.color = palette[0]
        self.glow_color = palette[1]

        # Math problem
        self.problem, self.answer = generate_math_problem(operation, difficulty, level)

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy
        self.rotation += self.rotation_speed
        if self.flash > 0:
            self.flash -= dt * 5

        # Bounce off walls
        if self.x < self.size or self.x > WIDTH - self.size:
            self.vx *= -1
            self.x = max(self.size, min(WIDTH - self.size, self.x))

    def draw(self, surface):
        # Glow
        glow_r = int(self.size * 1.5)
        glow_surf = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
        glow_color = (*self.glow_color, 30)
        pygame.draw.circle(glow_surf, glow_color, (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (int(self.x) - glow_r, int(self.y) - glow_r))

        # Body
        rot_verts = []
        for vx, vy in self.vertices:
            rx = vx * math.cos(self.rotation) - vy * math.sin(self.rotation)
            ry = vx * math.sin(self.rotation) + vy * math.cos(self.rotation)
            rot_verts.append((int(self.x + rx), int(self.y + ry)))

        if len(rot_verts) >= 3:
            pygame.draw.polygon(surface, self.color, rot_verts)
            pygame.draw.polygon(surface, self.glow_color, rot_verts, 2)

        # Craters
        pygame.draw.circle(surface, (0, 0, 0, 50),
                           (int(self.x + self.size * 0.2), int(self.y + self.size * 0.1)),
                           max(1, int(self.size * 0.15)))
        pygame.draw.circle(surface, (0, 0, 0, 50),
                           (int(self.x - self.size * 0.3), int(self.y - self.size * 0.2)),
                           max(1, int(self.size * 0.1)))

        # Flash
        if self.flash > 0:
            flash_surf = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            flash_alpha = int(min(1, self.flash) * 127)
            pygame.draw.circle(flash_surf, (255, 255, 255, flash_alpha),
                               (self.size, self.size), self.size)
            surface.blit(flash_surf, (int(self.x) - self.size, int(self.y) - self.size))

        # Math label
        label = f"{self.problem} = ?"
        text_surf = FONT_PROBLEM.render(label, True, GOLD)
        tw, th = text_surf.get_size()
        pad = 8
        bx = int(self.x) - tw // 2 - pad
        by = int(self.y) - self.size - 32
        bg_rect = pygame.Rect(bx, by, tw + pad*2, th + pad)
        pygame.draw.rect(surface, (0, 0, 0, 180), bg_rect, border_radius=6)
        pygame.draw.rect(surface, self.glow_color, bg_rect, 1, border_radius=6)
        surface.blit(text_surf, (bx + pad, by + pad // 2))

# ============================================================
# MATH PROBLEM GENERATOR
# ============================================================
def generate_math_problem(operation, difficulty, level):
    level_bonus = level // 3
    ops = ["addition", "subtraction", "multiplication", "division"]
    op = random.choice(ops) if operation == "mixed" else operation

    if op == "addition":
        max_n = {"easy": 10+level_bonus*3, "medium": 25+level_bonus*5, "hard": 50+level_bonus*8}[difficulty]
        a = random.randint(1, max_n)
        b = random.randint(1, max_n)
        return f"{a} + {b}", a + b

    elif op == "subtraction":
        max_n = {"easy": 15+level_bonus*3, "medium": 30+level_bonus*5, "hard": 60+level_bonus*8}[difficulty]
        a = random.randint(1, max_n)
        b = random.randint(1, a)
        return f"{a} - {b}", a - b

    elif op == "multiplication":
        max_n = {"easy": 5+level_bonus, "medium": 9+level_bonus, "hard": 12+level_bonus}[difficulty]
        a = random.randint(1, min(max_n, 15))
        b = random.randint(1, min(max_n, 15))
        return f"{a} x {b}", a * b

    elif op == "division":
        max_n = {"easy": 5+level_bonus, "medium": 10+level_bonus, "hard": 12+level_bonus}[difficulty]
        b = random.randint(1, min(max_n, 15))
        answer = random.randint(1, min(max_n, 12))
        a = b * answer
        return f"{a} / {b}", answer

    return "1 + 1", 2

# ============================================================
# DRAW SPACESHIP
# ============================================================
def draw_ship(surface, x, y):
    # Shield glow
    glow_r = 35
    glow_surf = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (0, 150, 255, 30), (glow_r, glow_r), glow_r)
    surface.blit(glow_surf, (int(x) - glow_r, int(y) - glow_r))

    # Ship body
    points = [
        (x, y - 22),
        (x - 14, y + 12),
        (x - 8, y + 8),
        (x - 6, y + 18),
        (x, y + 14),
        (x + 6, y + 18),
        (x + 8, y + 8),
        (x + 14, y + 12),
    ]
    pygame.draw.polygon(surface, BLUE_SHIP, points)
    pygame.draw.polygon(surface, (102, 170, 255), points, 1)

    # Cockpit
    pygame.draw.ellipse(surface, (170, 238, 255), (int(x)-5, int(y)-13, 10, 16))
    pygame.draw.ellipse(surface, (68, 136, 204), (int(x)-5, int(y)-13, 10, 16), 1)

    # Wing accents
    pygame.draw.line(surface, (102, 204, 255), (int(x)-4, int(y)+4), (int(x)-12, int(y)+11), 1)
    pygame.draw.line(surface, (102, 204, 255), (int(x)+4, int(y)+4), (int(x)+12, int(y)+11), 1)

# ============================================================
# DRAW HEARTS
# ============================================================
def draw_heart(surface, cx, cy, filled=True):
    color = RED if filled else (255, 255, 255, 38)
    if filled:
        pygame.draw.circle(surface, color, (int(cx) - 4, int(cy) - 2), 5)
        pygame.draw.circle(surface, color, (int(cx) + 4, int(cy) - 2), 5)
        pygame.draw.polygon(surface, color, [
            (int(cx) - 9, int(cy)),
            (int(cx), int(cy) + 10),
            (int(cx) + 9, int(cy)),
        ])
    else:
        pygame.draw.circle(surface, (60, 60, 60), (int(cx) - 4, int(cy) - 2), 5)
        pygame.draw.circle(surface, (60, 60, 60), (int(cx) + 4, int(cy) - 2), 5)
        pygame.draw.polygon(surface, (60, 60, 60), [
            (int(cx) - 9, int(cy)),
            (int(cx), int(cy) + 10),
            (int(cx) + 9, int(cy)),
        ])

# ============================================================
# DRAW BACKGROUND
# ============================================================
def draw_background(surface, stars, time_ms):
    # Gradient background
    for y_pos in range(HEIGHT):
        t = y_pos / HEIGHT
        r = int(10 + 16 * t)
        g = int(10 + 16 * t)
        b = int(46 + (61 - 46) * (1 - abs(t - 0.5) * 2))
        pygame.draw.line(surface, (r, g, b), (0, y_pos), (WIDTH, y_pos))

    # Nebula
    neb_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(neb_surf, (*NEBULA1, 20), (WIDTH//3, HEIGHT//3), WIDTH//2)
    pygame.draw.circle(neb_surf, (*NEBULA2, 15), (int(WIDTH*0.7), int(HEIGHT*0.6)), WIDTH//3)
    surface.blit(neb_surf, (0, 0))

    # Stars
    for star in stars:
        star.draw(surface, time_ms)

# ============================================================
# HIGH SCORE
# ============================================================
HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mathblasters_highscore.json")

def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return json.load(f).get("highscore", 0)
    except Exception:
        return 0

def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump({"highscore": score}, f)
    except Exception:
        pass

# ============================================================
# BUTTON CLASS
# ============================================================
class Button:
    def __init__(self, x, y, w, h, text, color=CYAN, text_color=WHITE):
        self.rect = pygame.Rect(x - w//2, y - h//2, w, h)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.hovered = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        color = tuple(min(255, c + 30) for c in self.color) if self.hovered else self.color
        # Shadow/glow
        glow_surf = pygame.Surface((self.rect.w + 20, self.rect.h + 20), pygame.SRCALPHA)
        glow_color = (*self.color, 40)
        pygame.draw.rect(glow_surf, glow_color, (0, 0, self.rect.w + 20, self.rect.h + 20), border_radius=16)
        surface.blit(glow_surf, (self.rect.x - 10, self.rect.y - 10))

        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, tuple(min(255, c + 60) for c in self.color), self.rect, 2, border_radius=12)

        text_surf = FONT_MED.render(self.text, True, self.text_color)
        tx = self.rect.centerx - text_surf.get_width() // 2
        ty = self.rect.centery - text_surf.get_height() // 2
        surface.blit(text_surf, (tx, ty))

    def clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

# ============================================================
# MAIN GAME CLASS
# ============================================================
class MathBlastersGame:
    def __init__(self):
        self.highscore = load_highscore()
        self.state = "menu"  # menu, playing, paused, game_over
        self.difficulty = "medium"
        self.operation = "mixed"
        self.sound_on = True

        self.reset_game()
        self.stars = [Star() for _ in range(150)]
        self.time_ms = 0

        # Menu buttons
        bw, bh = 130, 42
        gap = 145
        self.diff_buttons = {
            "easy":   Button(WIDTH//2 - gap, 310, bw, bh, "Easy",   GREEN),
            "medium": Button(WIDTH//2, 310, bw, bh, "Medium", GOLD),
            "hard":   Button(WIDTH//2 + gap, 310, bw, bh, "Hard",   RED),
        }
        op_labels = {"addition": " + ", "subtraction": " - ", "multiplication": " x ", "division": " / ", "mixed": " * "}
        gap2 = 85
        self.op_buttons = {
            key: Button(WIDTH//2 - 2*gap2 + i*gap2, 410, 70, bh, label, CYAN)
            for i, (key, label) in enumerate(op_labels.items())
        }
        self.start_button = Button(WIDTH//2, 530, 260, 55, "START MISSION", CYAN)
        self.sound_button = Button(WIDTH//2 + 120, 490, 100, 36, "Sound ON", GREEN if self.sound_on else (100,100,100))
        self.resume_button = Button(WIDTH//2, HEIGHT//2 + 60, 200, 50, "RESUME", CYAN)
        self.play_again_button = Button(WIDTH//2, HEIGHT//2 + 100, 260, 50, "PLAY AGAIN", CYAN)

    def reset_game(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.ship_x = WIDTH // 2
        self.ship_y = HEIGHT - 80
        self.ship_target_x = WIDTH // 2
        self.asteroids = []
        self.lasers = []
        self.particles = []
        self.thrusts = []
        self.input_text = ""
        self.correct_answers = 0
        self.wrong_answers = 0
        self.combo = 0
        self.max_combo = 0
        self.spawn_timer = 0
        self.spawn_interval = {"easy": 3000, "medium": 2200, "hard": 1500}[self.difficulty]
        self.asteroids_destroyed = 0
        self.asteroids_for_next_level = 5
        self.screen_shake = 0
        self.combo_display = ""
        self.combo_display_timer = 0

    def start_game(self):
        self.reset_game()
        self.state = "playing"

    def fire_laser(self):
        if not self.input_text:
            return
        try:
            answer = int(self.input_text)
        except ValueError:
            self.input_text = ""
            return

        matching = None
        for a in self.asteroids:
            if a.answer == answer:
                matching = a
                break

        self.lasers.append(Laser(self.ship_x, self.ship_y - 20, matching))
        play_sfx(SFX_SHOOT)
        self.input_text = ""

    def spawn_asteroid(self):
        a = Asteroid(self.level, self.difficulty, self.operation)
        self.asteroids.append(a)

    def handle_game_over(self):
        self.state = "game_over"
        if self.score > self.highscore:
            self.highscore = self.score
            save_highscore(self.score)

    # ---- UPDATE ----
    def update(self, dt):
        self.time_ms += dt * 1000

        # Stars always update
        for star in self.stars:
            star.update()

        if self.combo_display_timer > 0:
            self.combo_display_timer -= dt

        if self.state != "playing":
            return

        # Screen shake decay
        if self.screen_shake > 0:
            self.screen_shake *= 0.9
            if self.screen_shake < 0.1:
                self.screen_shake = 0

        # Ship movement (smooth)
        self.ship_x += (self.ship_target_x - self.ship_x) * 0.15
        self.ship_x = max(30, min(WIDTH - 30, self.ship_x))

        # Thrust
        if abs(self.ship_x - self.ship_target_x) > 2 or random.random() < 0.3:
            self.thrusts.append(ThrustParticle(self.ship_x, self.ship_y))

        # Update thrusts
        self.thrusts = [t for t in self.thrusts if t.update(dt)]

        # Spawn asteroids
        self.spawn_timer += dt * 1000
        interval = self.spawn_interval / (1 + self.level * 0.1)
        max_asteroids = 6 + self.level
        if self.spawn_timer >= interval and len(self.asteroids) < max_asteroids:
            self.spawn_asteroid()
            self.spawn_timer = 0

        # Update asteroids
        for a in self.asteroids[:]:
            a.update(dt)
            if a.y > HEIGHT + a.size:
                self.asteroids.remove(a)
                self.lives -= 1
                self.combo = 0
                self.screen_shake = 10
                play_sfx(SFX_LOSE_LIFE)
                if self.lives <= 0:
                    self.handle_game_over()
                    return

        # Update lasers
        for laser in self.lasers[:]:
            alive = laser.update(dt)
            if not alive:
                # Laser went off screen
                if laser.target_asteroid and laser.target_asteroid in self.asteroids:
                    # Wrong answer
                    self.wrong_answers += 1
                    self.combo = 0
                    self.lives -= 1
                    self.screen_shake = 5
                    play_sfx(SFX_WRONG)
                    if self.lives <= 0:
                        self.handle_game_over()
                        return
                self.lasers.remove(laser)
                continue

            # Check hit
            if laser.target_asteroid and laser.target_asteroid in self.asteroids:
                target = laser.target_asteroid
                dist = math.sqrt((laser.x - target.x)**2 + (laser.y - target.y)**2)
                if dist < target.size + 15:
                    # HIT!
                    for _ in range(25):
                        self.particles.append(Particle(target.x, target.y, target.glow_color))
                    for _ in range(10):
                        self.particles.append(Particle(target.x, target.y, GOLD))

                    self.combo += 1
                    multiplier = min(self.combo, 10)
                    points = (10 + self.level * 5) * multiplier
                    self.score += points
                    self.correct_answers += 1
                    self.asteroids_destroyed += 1
                    if self.combo > self.max_combo:
                        self.max_combo = self.combo
                    self.combo_display = f"+{points}"
                    self.combo_display_timer = 1.0

                    self.asteroids.remove(target)
                    self.screen_shake = 3
                    play_sfx(SFX_EXPLODE)

                    if laser in self.lasers:
                        self.lasers.remove(laser)

                    # Level up
                    if self.asteroids_destroyed >= self.asteroids_for_next_level:
                        self.level += 1
                        self.asteroids_destroyed = 0
                        self.asteroids_for_next_level = 5 + self.level * 2
                        play_sfx(SFX_LEVEL_UP)
                    continue

        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]

    # ---- DRAW ----
    def draw(self, surface):
        # Screen shake offset
        shake_x = random.uniform(-self.screen_shake, self.screen_shake) if self.screen_shake > 0 else 0
        shake_y = random.uniform(-self.screen_shake, self.screen_shake) if self.screen_shake > 0 else 0

        # Create buffer for shake
        buf = pygame.Surface((WIDTH, HEIGHT))
        draw_background(buf, self.stars, self.time_ms)

        if self.state in ("playing", "paused", "game_over"):
            # Thrusts
            for t in self.thrusts:
                t.draw(buf)

            # Asteroids
            for a in self.asteroids:
                a.draw(buf)

            # Lasers
            for l in self.lasers:
                l.draw(buf)

            # Particles
            for p in self.particles:
                p.draw(buf)

            # Ship
            if self.state == "playing":
                draw_ship(buf, self.ship_x, self.ship_y)

            # HUD
            self.draw_hud(buf)

            # Combo display
            if self.combo_display_timer > 0:
                alpha = min(1, self.combo_display_timer)
                color = (int(255*alpha), int(215*alpha), 0)
                txt = FONT_LARGE.render(self.combo_display, True, color)
                buf.blit(txt, (int(self.ship_x) - txt.get_width()//2, int(self.ship_y) - 50))

        # Blit with shake
        surface.fill(BLACK)
        surface.blit(buf, (int(shake_x), int(shake_y)))

        # Overlays (no shake)
        if self.state == "menu":
            self.draw_menu(surface)
        elif self.state == "paused":
            self.draw_pause(surface)
        elif self.state == "game_over":
            self.draw_game_over(surface)

    def draw_hud(self, surface):
        # Top bar
        hud_surf = pygame.Surface((WIDTH, 50), pygame.SRCALPHA)
        hud_surf.fill((0, 0, 30, 160))
        surface.blit(hud_surf, (0, 0))

        # Score
        score_txt = FONT_MED.render(f"Score: {self.score}", True, GOLD)
        surface.blit(score_txt, (15, 15))

        # Level
        level_txt = FONT_MED.render(f"LEVEL {self.level}", True, CYAN)
        surface.blit(level_txt, (WIDTH//2 - level_txt.get_width()//2, 15))

        # Lives
        for i in range(3):
            draw_heart(surface, WIDTH - 20 - i * 28, 25, i < self.lives)

        # Combo
        if self.combo > 1:
            pulse = 0.7 + 0.3 * math.sin(self.time_ms * 0.005)
            c = int(255 * pulse)
            combo_txt = FONT_SMALL.render(f"COMBO x{self.combo}", True, (c, int(200*pulse), 0))
            surface.blit(combo_txt, (15, 42))

        # Input display
        input_str = self.input_text if self.input_text else "TYPE ANSWER..."
        input_color = GREEN if self.input_text else (80, 80, 80)
        input_txt = FONT_INPUT.render(input_str, True, input_color)
        ix = WIDTH//2 - input_txt.get_width()//2
        iy = HEIGHT - 45

        # Input box
        box_rect = pygame.Rect(ix - 12, iy - 6, input_txt.get_width() + 24, 34)
        box_color = (*GREEN, 60) if self.input_text else (255, 255, 255, 20)
        box_surf = pygame.Surface((box_rect.w, box_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(box_surf, box_color, (0, 0, box_rect.w, box_rect.h), border_radius=8)
        border_c = GREEN if self.input_text else (100, 100, 100)
        pygame.draw.rect(box_surf, border_c, (0, 0, box_rect.w, box_rect.h), 1, border_radius=8)
        surface.blit(box_surf, box_rect)

        surface.blit(input_txt, (ix, iy))

        # Cursor blink
        if self.input_text and int(self.time_ms / 500) % 2 == 0:
            cursor_x = ix + input_txt.get_width() + 4
            pygame.draw.line(surface, GREEN, (cursor_x, iy), (cursor_x, iy + 22), 2)

        # Controls hint
        hint = FONT_SMALL.render("Arrow/Mouse: Move | Type Answer | Enter: Fire | P: Pause", True, (60, 60, 60))
        surface.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 12))

    def draw_menu(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, 120))
        surface.blit(overlay, (0, 0))

        # Title
        title1 = FONT_HUGE.render("MATH", True, CYAN)
        title2 = FONT_HUGE.render("BLASTERS", True, GOLD)
        # Glow effect
        glow1 = FONT_HUGE.render("MATH", True, (0, 80, 130))
        glow2 = FONT_HUGE.render("BLASTERS", True, (130, 100, 0))
        surface.blit(glow1, (WIDTH//2 - title1.get_width()//2 + 3, 103))
        surface.blit(glow2, (WIDTH//2 - title2.get_width()//2 + 3, 173))
        surface.blit(title1, (WIDTH//2 - title1.get_width()//2, 100))
        surface.blit(title2, (WIDTH//2 - title2.get_width()//2, 170))

        subtitle = FONT_SMALL.render("Blast the asteroids with your math skills!", True, (100, 200, 255))
        surface.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 240))

        # Difficulty label
        diff_label = FONT_SMALL.render("DIFFICULTY", True, CYAN)
        surface.blit(diff_label, (WIDTH//2 - diff_label.get_width()//2, 275))
        mouse_pos = pygame.mouse.get_pos()
        for key, btn in self.diff_buttons.items():
            btn.color = GREEN if key == "easy" else (GOLD if key == "medium" else RED)
            btn.update(mouse_pos)
            btn.draw(surface)

        # Operation label
        op_label = FONT_SMALL.render("OPERATIONS", True, CYAN)
        surface.blit(op_label, (WIDTH//2 - op_label.get_width()//2, 375))
        op_names = {"addition": "+ Add", "subtraction": "- Sub", "multiplication": "x Mul", "division": "/ Div", "mixed": "* Mix"}
        for key, btn in self.op_buttons.items():
            btn.text = op_names[key]
            btn.color = CYAN if self.operation == key else (80, 80, 80)
            btn.update(mouse_pos)
            btn.draw(surface)

        # Sound button
        self.sound_button.text = "Sound ON" if self.sound_on else "Sound OFF"
        self.sound_button.color = GREEN if self.sound_on else (80, 80, 80)
        self.sound_button.update(mouse_pos)
        self.sound_button.draw(surface)

        # High score
        if self.highscore > 0:
            hs = FONT_MED.render(f"HIGH SCORE: {self.highscore}", True, GOLD)
            surface.blit(hs, (WIDTH//2 - hs.get_width()//2, 490))

        # Start button
        self.start_button.update(mouse_pos)
        self.start_button.draw(surface)

        # Controls
        controls = FONT_SMALL.render("Arrow keys or mouse to move | Type answer | Enter to fire", True, (50, 50, 50))
        surface.blit(controls, (WIDTH//2 - controls.get_width()//2, HEIGHT - 30))

    def draw_pause(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        title = FONT_TITLE.render("PAUSED", True, CYAN)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 50))

        hint = FONT_SMALL.render("Press P or ESC to resume", True, (150, 150, 150))
        surface.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 10))

        mouse_pos = pygame.mouse.get_pos()
        self.resume_button.update(mouse_pos)
        self.resume_button.draw(surface)

    def draw_game_over(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        title = FONT_TITLE.render("GAME OVER", True, RED)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))

        if self.score >= self.highscore and self.score > 0:
            hs = FONT_MED.render("NEW HIGH SCORE!", True, GOLD)
            surface.blit(hs, (WIDTH//2 - hs.get_width()//2, HEIGHT//2 - 70))

        # Stats card
        card_w, card_h = 340, 140
        card_rect = pygame.Rect(WIDTH//2 - card_w//2, HEIGHT//2 - 45, card_w, card_h)
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill((0, 0, 0, 140))
        pygame.draw.rect(card_surf, CYAN, (0, 0, card_w, card_h), 1, border_radius=12)
        surface.blit(card_surf, card_rect)

        stats = [
            (f"{self.score}", GOLD, "Score"),
            (f"{self.level}", CYAN, "Level"),
            (f"{self.correct_answers}", GREEN, "Correct"),
            (f"{self.wrong_answers}", RED, "Wrong"),
        ]
        cols = 4
        col_w = card_w // cols
        for i, (val, color, label) in enumerate(stats):
            cx = card_rect.x + col_w * i + col_w // 2
            # Value
            vtxt = FONT_LARGE.render(val, True, color)
            surface.blit(vtxt, (cx - vtxt.get_width()//2, card_rect.y + 20))
            # Label
            ltxt = FONT_SMALL.render(label, True, (120, 120, 120))
            surface.blit(ltxt, (cx - ltxt.get_width()//2, card_rect.y + 55))

        # Accuracy
        total = self.correct_answers + self.wrong_answers
        accuracy = math.round((self.correct_answers / total) * 100) if total > 0 else 0
        acc_txt = FONT_SMALL.render(f"Accuracy: {accuracy}%", True, (100, 100, 100))
        surface.blit(acc_txt, (WIDTH//2 - acc_txt.get_width()//2, card_rect.y + card_h + 10))

        mouse_pos = pygame.mouse.get_pos()
        self.play_again_button.update(mouse_pos)
        self.play_again_button.draw(surface)

        hint = FONT_SMALL.render("Press Enter to continue", True, (50, 50, 50))
        surface.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 160))

    # ---- EVENT HANDLING ----
    def handle_event(self, event):
        mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.QUIT:
            return False

        if self.state == "menu":
            if event.type == pygame.MOUSEBUTTONDOWN:
                for key, btn in self.diff_buttons.items():
                    if btn.clicked(mouse_pos):
                        self.difficulty = key
                for key, btn in self.op_buttons.items():
                    if btn.clicked(mouse_pos):
                        self.operation = key
                if self.start_button.clicked(mouse_pos):
                    self.start_game()
                if self.sound_button.clicked(mouse_pos):
                    self.sound_on = not self.sound_on

            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.start_game()

        elif self.state == "playing":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    pass  # handled in continuous movement
                elif event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.state = "paused"
                elif event.key == pygame.K_RETURN:
                    self.fire_laser()
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                elif event.key == pygame.K_MINUS:
                    if len(self.input_text) < 6:
                        self.input_text += "-"
                elif event.unicode.isdigit() and len(self.input_text) < 6:
                    self.input_text += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN:
                self.ship_target_x = mouse_pos[0]
            if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                self.ship_target_x = mouse_pos[0]

        elif self.state == "paused":
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_ESCAPE):
                self.state = "playing"
            if event.type == pygame.MOUSEBUTTONDOWN and self.resume_button.clicked(mouse_pos):
                self.state = "playing"

        elif self.state == "game_over":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.state = "menu"
            if event.type == pygame.MOUSEBUTTONDOWN and self.play_again_button.clicked(mouse_pos):
                self.state = "menu"

        return True

    def handle_continuous_input(self):
        """Handle held keys for smooth movement"""
        if self.state != "playing":
            return
        keys = pygame.key.get_pressed()
        speed = 6
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.ship_target_x -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.ship_target_x += speed
        self.ship_target_x = max(30, min(WIDTH - 30, self.ship_target_x))


# ============================================================
# MAIN LOOP
# ============================================================
def main():
    game = MathBlastersGame()
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)  # cap delta time

        for event in pygame.event.get():
            if not game.handle_event(event):
                running = False

        game.handle_continuous_input()
        game.update(dt)
        game.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
