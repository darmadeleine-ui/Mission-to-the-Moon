import pygame
import random
import sys
import math
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum, auto

# --- 1. CONFIGURATION ---
WIDTH, HEIGHT = 1000, 700
FPS = 60

# Colors
COLOR_BG = (10, 10, 35)       # Deep Night Sky
COLOR_MOON = (240, 240, 220)  # Pale Yellow
COLOR_SHIP = (200, 200, 200)  # Silver
COLOR_FIRE = (255, 140, 0)    # Orange for thrusters
COLOR_TEXT = (255, 255, 255)

# Power Up Colors
COLOR_PU_SLOW = (100, 200, 255) # Cyan
COLOR_PU_FIX = (50, 255, 100)   # Green
COLOR_PU_GHOST = (200, 100, 255)# Purple
COLOR_PU_RAPID = (255, 50, 50)  # Red

# Gameplay Config
PLAYER_SPEED = 9 
BASE_SCROLL_SPEED = 5
BASE_CLOUD_FREQ = 160 
POWERUP_FREQUENCY = 600 # 10 seconds
TARGET_NUMBER = 50

# --- 2. MODELS & ENUMS ---

class GameState(Enum):
    PLAYING = auto()
    TRANSITION_TO_LANDING = auto()
    LANDING_SCENE = auto()
    GAME_OVER = auto()

class Operation(Enum):
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "x"
    DIVIDE = ":"

class PowerUpType(Enum):
    SLOW_MOTION = "SLOW"
    ROUND_NUM = "FIX" 
    GHOST = "GHOST"
    INVERT_CONTROLS = "CONFUSION" 
    RAPID_FIRE = "RAPID"

@dataclass
class Star:
    x: float
    y: float
    size: float
    speed: float

class PowerUp:
    def __init__(self, x: int, y: int, p_type: PowerUpType):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.type = p_type
        self.angle = 0
        self.hue = 0 
        
        if p_type == PowerUpType.SLOW_MOTION: self.color = COLOR_PU_SLOW
        elif p_type == PowerUpType.ROUND_NUM: self.color = COLOR_PU_FIX
        elif p_type == PowerUpType.GHOST: self.color = COLOR_PU_GHOST
        elif p_type == PowerUpType.RAPID_FIRE: self.color = COLOR_PU_RAPID
        else: self.color = (255, 255, 255) 

    def move(self, speed: float):
        self.rect.x -= speed
        self.angle += 5
        self.hue = (self.hue + 5) % 360 

    def draw(self, surface: pygame.Surface):
        center = self.rect.center
        draw_color = self.color
        if self.type == PowerUpType.INVERT_CONTROLS:
            c = pygame.Color(0,0,0)
            c.hsva = (self.hue, 100, 100, 100)
            draw_color = c

        points = []
        for i in range(10):
            radius = 20 if i % 2 == 0 else 10
            angle_rad = math.radians(self.angle + i * 36)
            px = center[0] + radius * math.cos(angle_rad)
            py = center[1] + radius * math.sin(angle_rad)
            points.append((px, py))
        
        pygame.draw.polygon(surface, draw_color, points)
        pygame.draw.polygon(surface, (255, 255, 255), points, 2) 

class Cloud:
    def __init__(self, x: int, y: int, width: int, height: int, op: Operation, val: int):
        self.rect = pygame.Rect(x, y, width, height)
        self.op = op
        self.val = val
        
        # MOVEMENT LOGIC
        self.original_y = float(y) # Remember starting lane
        self.float_offset = random.uniform(0, 2 * math.pi) # Random start point in sine wave
        self.float_speed = random.uniform(0.02, 0.05) # How fast it bobs
        self.amplitude = 40 # How far up/down it goes (pixels)

        self.circles = []
        for _ in range(8):
            cx = random.randint(x, x + width)
            cy = random.randint(y, y + height)
            r = random.randint(30, 50)
            self.circles.append((cx - x, cy - y, r))

    def move(self, scroll_speed: float):
        # 1. Horizontal Scroll
        self.rect.x -= scroll_speed
        
        # 2. Vertical Sine Wave (Bobbing)
        # Using pygame.time.get_ticks() ensures smooth animation
        current_time = pygame.time.get_ticks()
        
        # Calculate vertical offset
        wave = math.sin(current_time * 0.002 + self.float_offset) * self.amplitude
        
        # Apply to rect
        self.rect.y = int(self.original_y + wave)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, is_ghost_active: bool):
        base_color = (230, 230, 250) if not is_ghost_active else (100, 100, 120)
        
        # Draw circles relative to the current rect position
        for cx, cy, r in self.circles:
            pygame.draw.circle(surface, base_color, (self.rect.x + cx, self.rect.y + cy), r)
        
        text = f"{self.op.value} {self.val}"
        shadow = font.render(text, True, (50, 50, 80))
        surface.blit(shadow, (self.rect.centerx - shadow.get_width()//2 + 2, self.rect.centery - shadow.get_height()//2 + 2))
        
        render = font.render(text, True, (50, 100, 150) if not is_ghost_active else (80, 80, 80))
        surface.blit(render, (self.rect.centerx - render.get_width()//2, self.rect.centery - render.get_height()//2))

class Player:
    def __init__(self):
        self.rect = pygame.Rect(100, HEIGHT // 2, 100, 60)
        self.score: int = 0 
        self.figure_x = 0 

    def calculate(self, op: Operation, val: int) -> bool:
        """ Returns True if decimal penalty occurred """
        res = float(self.score)
        if op == Operation.ADD: res += val
        elif op == Operation.SUBTRACT: res -= val
        elif op == Operation.MULTIPLY: res *= val
        elif op == Operation.DIVIDE:
            if val == 0: return False
            res = res / val
        
        if res < 0: res = 0
        
        is_decimal_penalty = (res % 1 != 0)
        self.score = round(res)
        return is_decimal_penalty

    def draw_spaceship(self, surface: pygame.Surface, font: pygame.font.Font, x_offset=0, y_offset=0, scale=1.0, is_ghost=False):
        w, h = self.rect.width * scale, self.rect.height * scale
        
        if x_offset == 0 and y_offset == 0:
            lx, ly = self.rect.x, self.rect.y
        else:
            lx, ly = x_offset, y_offset

        cx, cy = lx + w/2, ly + h/2

        ship_color = COLOR_SHIP if not is_ghost else (100, 100, 130)
        if is_ghost:
             pygame.draw.circle(surface, (200, 100, 255), (cx, cy), w, 2)

        if random.random() > 0.2:
            flame_len = random.randint(20, 50) * scale
            flame_points = [
                (lx + 10 * scale, cy - 10 * scale),
                (lx - flame_len, cy),
                (lx + 10 * scale, cy + 10 * scale)
            ]
            pygame.draw.polygon(surface, COLOR_FIRE, flame_points)

        points = [
            (lx + w, cy), (lx, ly), 
            (lx + 20 * scale, cy), (lx, ly + h)
        ]
        pygame.draw.polygon(surface, ship_color, points)
        pygame.draw.polygon(surface, (100, 100, 100), points, int(3*scale))

        if scale < 2.0:
            score_surf = font.render(str(self.score), True, (0, 0, 0))
            surface.blit(score_surf, (cx - score_surf.get_width()//2 - 10, cy - score_surf.get_height()//2))

# --- 3. THE GAME ENGINE ---

class SpaceMathGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Cosmic Calculator: Mission to Moon")
        self.clock = pygame.time.Clock()
        
        self.font_ui = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_cloud = pygame.font.SysFont("Verdana", 45, bold=True) 
        self.font_big = pygame.font.SysFont("Arial", 60, bold=True)
        
        self.reset_game()

    def reset_game(self):
        self.state = GameState.PLAYING
        self.player = Player()
        self.clouds: List[Cloud] = []
        self.powerups: List[PowerUp] = []
        self.stars = [Star(random.randint(0, WIDTH), random.randint(0, HEIGHT), 
                           random.randint(1, 3), random.uniform(0.5, 2)) for _ in range(120)]
        self.target = TARGET_NUMBER
        
        self.spawn_cloud_wall(x_offset=200) 
        self.timer_spawn_cloud = 0
        
        self.timer_spawn_powerup = 0
        self.current_difficulty_speed = BASE_SCROLL_SPEED
        self.msg = ""
        self.msg_timer = 0
        
        self.timer_slow_motion = 0
        self.timer_ghost_mode = 0
        self.timer_inverted = 0
        self.timer_rapid_fire = 0
        
        self.lander_y = -100 
        
    def spawn_cloud_wall(self, x_offset=0):
        wall_x = WIDTH + 100 + x_offset
        lane_height = HEIGHT // 3
        ops = [Operation.ADD, Operation.SUBTRACT, Operation.MULTIPLY]
        if self.player.score > 10: ops.append(Operation.DIVIDE)
        
        for i in range(3):
            op = random.choice(ops)
            val = random.randint(1, 9)
            if op == Operation.MULTIPLY: val = random.randint(2, 4)
            y_pos = i * lane_height + (lane_height // 2) - 60
            self.clouds.append(Cloud(wall_x, y_pos, 180, 120, op, val))

    def spawn_powerup(self):
        roll = random.random()
        
        # Dynamic Probabilities based on speed
        if self.current_difficulty_speed > BASE_SCROLL_SPEED * 1.5:
            if roll < 0.50: p_type = PowerUpType.ROUND_NUM
            elif roll < 0.70: p_type = PowerUpType.SLOW_MOTION
            elif roll < 0.85: p_type = PowerUpType.GHOST
            else: p_type = PowerUpType.INVERT_CONTROLS
        else:
            if roll < 0.25: p_type = PowerUpType.SLOW_MOTION
            elif roll < 0.50: p_type = PowerUpType.ROUND_NUM
            elif roll < 0.70: p_type = PowerUpType.GHOST
            elif roll < 0.90: p_type = PowerUpType.INVERT_CONTROLS
            else: p_type = PowerUpType.RAPID_FIRE

        y = random.randint(50, HEIGHT - 50)
        self.powerups.append(PowerUp(WIDTH + 50, y, p_type))

    def update_background(self):
        for star in self.stars:
            star.x -= star.speed
            if star.x < 0:
                star.x = WIDTH
                star.y = random.randint(0, HEIGHT)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(star.x), int(star.y)), int(star.size))

    def draw_hud(self):
        if self.state == GameState.PLAYING:
            mx, my = WIDTH - 80, 80
            pygame.draw.circle(self.screen, COLOR_MOON, (mx, my), 50)
            pygame.draw.circle(self.screen, (200, 200, 180), (mx-15, my-10), 10)
            t_surf = self.font_ui.render(str(self.target), True, (50, 50, 50))
            self.screen.blit(t_surf, (mx - t_surf.get_width()//2, my - t_surf.get_height()//2))

        y_hud = 20
        status_texts = []
        if self.timer_slow_motion > 0: status_texts.append(("SLOW MOTION", COLOR_PU_SLOW))
        if self.timer_ghost_mode > 0: status_texts.append(("GHOST MODE", COLOR_PU_GHOST))
        if self.timer_inverted > 0: status_texts.append(("CONTROLS FLIPPED!", (255, 100, 255)))
        if self.timer_rapid_fire > 0: status_texts.append(("RAPID FIRE!!!", COLOR_PU_RAPID))
        
        for text, color in status_texts:
            surf = self.font_ui.render(text, True, color)
            self.screen.blit(surf, (20, y_hud))
            y_hud += 30

        if self.current_difficulty_speed > BASE_SCROLL_SPEED and self.timer_rapid_fire == 0:
            spd_text = self.font_ui.render("DECIMAL PENALTY! SPEED UP!", True, (255, 50, 50))
            self.screen.blit(spd_text, (20, y_hud))

    def animate_landing_scene(self):
        moon_rect = pygame.Rect(0, HEIGHT - 200, WIDTH, 200)
        pygame.draw.rect(self.screen, COLOR_MOON, moon_rect)
        pygame.draw.ellipse(self.screen, (200, 200, 180), (100, HEIGHT-150, 150, 40))
        
        target_y = HEIGHT - 200 - 80 
        if self.lander_y < target_y:
            self.lander_y += 3
            self.player.draw_spaceship(self.screen, self.font_ui, 
                                     x_offset=200, y_offset=self.lander_y, scale=2.5)
            if self.lander_y > target_y - 100:
                pygame.draw.circle(self.screen, (200, 200, 200), (250, HEIGHT-200), random.randint(10, 30))
        else:
            self.lander_y = target_y
            self.player.draw_spaceship(self.screen, self.font_ui, 
                                     x_offset=200, y_offset=self.lander_y, scale=2.5)
            self.animate_stick_figure()

    def animate_stick_figure(self):
        start_x = 350 
        ground_y = HEIGHT - 200
        flag_pos_x = 600
        
        if self.player.figure_x < (flag_pos_x - start_x): self.player.figure_x += 2 
        
        current_x = start_x + self.player.figure_x
        current_y = ground_y - 40 
        
        fig_color = (255, 255, 255) 
        
        pygame.draw.circle(self.screen, (0,0,0), (int(current_x), int(current_y - 20)), 10)
        pygame.draw.circle(self.screen, fig_color, (int(current_x), int(current_y - 20)), 8)
        pygame.draw.line(self.screen, fig_color, (current_x, current_y - 10), (current_x, current_y + 20), 4)
        
        if self.player.figure_x < (flag_pos_x - start_x): offset = math.sin(self.player.figure_x * 0.2) * 10
        else: offset = 0
        
        pygame.draw.line(self.screen, fig_color, (current_x, current_y + 20), (current_x - 10 + offset, current_y + 50), 4)
        pygame.draw.line(self.screen, fig_color, (current_x, current_y + 20), (current_x + 10 - offset, current_y + 50), 4)
        pygame.draw.line(self.screen, fig_color, (current_x, current_y), (current_x + 15, current_y + 10), 4)
        
        if self.player.figure_x >= (flag_pos_x - start_x):
            pygame.draw.line(self.screen, (50, 50, 50), (current_x + 20, current_y + 50), (current_x + 20, current_y - 60), 4)
            flag_width = 220 
            flag_rect = pygame.Rect(current_x + 22, current_y - 60, flag_width, 50)
            pygame.draw.rect(self.screen, (0, 200, 0), flag_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), flag_rect, 2)
            
            win_txt = self.font_ui.render("YOU WON!", True, (255, 255, 255))
            self.screen.blit(win_txt, (flag_rect.centerx - win_txt.get_width()//2, flag_rect.centery - win_txt.get_height()//2))
            
            big_win = self.font_big.render("MISSION ACCOMPLISHED", True, (255, 215, 0))
            self.screen.blit(big_win, (WIDTH//2 - big_win.get_width()//2, 100))
            
            sub = self.font_ui.render("Press SPACE to Play Again", True, (200, 200, 200))
            self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 180))

    def run(self):
        while True:
            # 1. Process Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if self.state in [GameState.LANDING_SCENE, GameState.GAME_OVER]:
                            self.reset_game()

            # 2. Get Keys (Called every frame, ensuring immediate response)
            keys = pygame.key.get_pressed()

            self.screen.fill(COLOR_BG)
            
            if self.state == GameState.PLAYING:
                self.update_background()
                
                # --- MOVEMENT ---
                if self.timer_inverted > 0:
                    if keys[pygame.K_UP] and self.player.rect.bottom < HEIGHT:
                        self.player.rect.y += PLAYER_SPEED
                    if keys[pygame.K_DOWN] and self.player.rect.top > 0:
                        self.player.rect.y -= PLAYER_SPEED
                else:
                    if keys[pygame.K_UP] and self.player.rect.top > 0:
                        self.player.rect.y -= PLAYER_SPEED
                    if keys[pygame.K_DOWN] and self.player.rect.bottom < HEIGHT:
                        self.player.rect.y += PLAYER_SPEED
                
                # --- CALCULATE SPEEDS ---
                effective_speed = self.current_difficulty_speed
                spawn_freq = BASE_CLOUD_FREQ

                if self.timer_slow_motion > 0:
                    effective_speed *= 0.5
                    self.timer_slow_motion -= 1
                
                if self.timer_rapid_fire > 0:
                    effective_speed = 12 
                    spawn_freq = 40      
                    self.timer_rapid_fire -= 1

                if self.timer_ghost_mode > 0: self.timer_ghost_mode -= 1
                if self.timer_inverted > 0: self.timer_inverted -= 1

                # --- SPAWNERS ---
                self.timer_spawn_cloud += 1
                if self.timer_spawn_cloud > spawn_freq:
                    self.spawn_cloud_wall()
                    self.timer_spawn_cloud = 0

                self.timer_spawn_powerup += 1
                if self.timer_spawn_powerup > POWERUP_FREQUENCY:
                    self.spawn_powerup()
                    self.timer_spawn_powerup = 0
                
                # --- COLLISIONS ---
                for pu in self.powerups[:]:
                    pu.move(effective_speed)
                    pu.draw(self.screen)
                    if self.player.rect.colliderect(pu.rect):
                        if pu.type == PowerUpType.SLOW_MOTION:
                            self.timer_slow_motion = 600
                        elif pu.type == PowerUpType.GHOST:
                            self.timer_ghost_mode = 300
                        elif pu.type == PowerUpType.ROUND_NUM:
                            self.current_difficulty_speed = BASE_SCROLL_SPEED
                        elif pu.type == PowerUpType.INVERT_CONTROLS:
                            self.timer_inverted = 300 
                        elif pu.type == PowerUpType.RAPID_FIRE:
                            self.timer_rapid_fire = 300 
                        self.powerups.remove(pu)
                    elif pu.rect.right < 0:
                        self.powerups.remove(pu)

                for cloud in self.clouds[:]:
                    cloud.move(effective_speed)
                    cloud.draw(self.screen, self.font_cloud, self.timer_ghost_mode > 0)
                    
                    if self.player.rect.colliderect(cloud.rect):
                        if self.timer_ghost_mode > 0:
                            pass 
                        else:
                            penalty = self.player.calculate(cloud.op, cloud.val)
                            if penalty and self.timer_rapid_fire == 0:
                                self.current_difficulty_speed *= 1.2
                                if self.current_difficulty_speed > 18: self.current_difficulty_speed = 18
                            
                            self.clouds.remove(cloud)
                            if self.player.score == self.target:
                                self.state = GameState.TRANSITION_TO_LANDING
                    
                    if cloud.rect.right < 0:
                        self.clouds.remove(cloud)

                self.player.draw_spaceship(self.screen, self.font_ui, is_ghost=self.timer_ghost_mode > 0)
                self.draw_hud()

            elif self.state == GameState.TRANSITION_TO_LANDING:
                self.update_background()
                self.player.rect.x += 10
                self.player.draw_spaceship(self.screen, self.font_ui)
                if self.player.rect.left > WIDTH:
                    self.state = GameState.LANDING_SCENE
                    
            elif self.state == GameState.LANDING_SCENE:
                for star in self.stars:
                     pygame.draw.circle(self.screen, (255, 255, 255), (int(star.x), int(star.y)), int(star.size))
                self.animate_landing_scene()

            elif self.state == GameState.GAME_OVER:
                self.update_background()
                for c in self.clouds: c.draw(self.screen, self.font_cloud, False)
                self.player.draw_spaceship(self.screen, self.font_ui)
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.screen.blit(overlay, (0,0))
                txt = self.font_big.render("GAME OVER", True, (255, 50, 50))
                self.screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 50))

            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = SpaceMathGame()
    game.run()