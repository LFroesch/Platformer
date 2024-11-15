from settings import * 
from sprites import *
from groups import AllSprites
import os
import pygame._sdl2 as sdl2
import pygame.display
from support import *
from random import randint
import pytmx
import sys

class Game:
    def __init__(self):
        print("Starting platform game!")
        os.environ['SDL_VIDEO_DISPLAY'] = '1'
        os.environ['SDL_VIDEO_WINDOW_POS'] = '1920,0'	

        pygame.init()
        self.font = pygame.font.Font(None, 36)

        # Let's see what we're working with

        self.display_surface = pygame.display.set_mode((1600, 900))
        pygame.display.set_caption('Platformer')

        self.clock = pygame.time.Clock()
        self.game_state = 'menu'
        self.running = True
        self.current_level = 1
        self.level_loaded = False

        # groups 
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.collectible_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()

        self.load_assets()

    def create_bee(self):
        Bee(frames = self.bee_frames,
            pos = ((self.level_width + WINDOW_WIDTH),(randint(0, self.level_height))),
            groups = (self.all_sprites, self.enemy_sprites),
            speed = randint(100, 300))

    def create_bullet(self, pos, direction):
        x = pos[0] + direction * 34 if direction == 1 else pos[0] + direction * 34 - self.bullet_surf.get_width()
        Bullet(self.bullet_surf, (x, pos[1]), direction, (self.all_sprites, self.bullet_sprites), self.level_width)
        Fire(self.fire_surf, pos, self.all_sprites, self.player)

    def load_assets(self):
        #graphics
        self.player_frames = import_folder('images', 'player')
        self.bullet_surf = import_image('images', 'gun', 'bullet')
        self.fire_surf = import_image('images', 'gun', 'fire')
        self.bee_frames = import_folder('images', 'enemies', 'bee')
        self.worm_frames = import_folder('images', 'enemies', 'worm')
        self.coin_frames = import_folder('images', 'collectibles', 'coin')

        # audio
        self.audio = audio_importer('audio')
        # self.audio['music'].play()

    def setup (self, level_num):

        self.level_num = level_num
        print(f"Attempting to load level: {self.level_num}")
        tmx_map = load_pygame(join('data', 'maps', f'world{self.level_num}.tmx'))
        self.level_width = tmx_map.width * TILE_SIZE
        self.level_height = tmx_map.height * TILE_SIZE

        portal_x = 18 * TILE_SIZE
        top_y = 2 * TILE_SIZE
        bottom_y = 38 * TILE_SIZE
        portal_surf = pygame.Surface((64, 64))
        portal_surf.fill('blue')
        self.top_portal = Portal((portal_x, top_y), portal_surf, [self.all_sprites], 'top')
        self.bottom_portal = Portal((portal_x, bottom_y), portal_surf, [self.all_sprites], 'bottom')

        for x, y, image in tmx_map.get_layer_by_name('Main').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites, self.collision_sprites))

        for x, y, image in tmx_map.get_layer_by_name('Decoration').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites))

        for obj in tmx_map.get_layer_by_name('Entities'):
            
            if obj.name == 'Player':
                self.player = Player(
                    (obj.x, obj.y),
                    self.all_sprites,
                    self.collision_sprites,
                    self.collectible_sprites,
                    self.player_frames,
                    self.create_bullet,
                    self.top_portal,
                    self.bottom_portal
                    )
            
            if obj.name == 'Cherry':  # Or whatever you named your objects in Tiled
                cherry_image = tmx_map.get_tile_image_by_gid(obj.gid)
                Cherry((obj.x, obj.y), cherry_image, [self.all_sprites, self.collectible_sprites])
                self.player.total_cherries += 1
            
            if obj.name == 'Worm':
                Worm(self.worm_frames, pygame.FRect(obj.x, obj.y, obj.width, obj.height), (self.all_sprites, self.enemy_sprites))
            
            if obj.name == 'Coin':
                Coin(self.coin_frames, pygame.FRect(obj.x, obj.y, obj.width, obj.height), (self.all_sprites, self.collectible_sprites))
                self.player.total_coins += 1
        
    def collision(self):
        # bullets -> enemies
        for bullet in self.bullet_sprites:
            sprite_collision = pygame.sprite.spritecollide(bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)
            if sprite_collision:
                bullet.kill()
                for sprite in sprite_collision:
                    sprite.destroy()
                    self.player.kills += 1
                    self.player.points += 250

        # enemies -> player
        collision_sprites = pygame.sprite.spritecollide(self.player, self.enemy_sprites, False, pygame.sprite.collide_mask)
        for enemy in collision_sprites:
            if isinstance(enemy, Bee):
                self.player.take_damage(20)
                enemy.destroy()
            else:
                self.player.take_damage(25)

    def display_score_area(self):
        # Calculate the total area covered by the score texts
        x, y = 10, 10  # Starting position for texts w/ Padding
        width = 230    # Estimated width of the text area
        height = 190   # Estimated height to cover all 5 lines (adjust as needed)

        # Create a semi-transparent surface
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((128, 128, 128, 128))  # Gray color with 50% transparency

        # Render it on the display surface
        self.display_surface.blit(overlay, (x, y))

    def display_coins(self):
        if self.player.coins == self.player.total_coins:
            color = (76, 153, 0)  # Green
        else:
            color = (0, 0, 0)    # Black
        coins_text = self.font.render(f'Coins: {self.player.coins} / {self.player.total_coins}', True, color)
        coins_rect = coins_text.get_rect(topleft = (20, 20))
        self.display_surface.blit(coins_text, coins_rect)
        self.display_cherries(coins_rect)

    def display_cherries(self, coins_rect):
        if self.player.cherries == self.player.total_cherries:
            color = (76, 153, 0)  # Green
        else:
            color = (0, 0, 0)    # Black
        cherries_text = self.font.render(f'Cherries: {self.player.cherries} / {self.player.total_cherries}', True, color)
        cherries_rect = cherries_text.get_rect(topleft = (20, coins_rect.bottom + 10))
        self.display_surface.blit(cherries_text, cherries_rect)
        self.display_kills(cherries_rect)

    def display_kills(self, cherries_rect):
        kill_text = self.font.render(f'Kills: {self.player.kills}', True, (0,0,0))
        kill_rect = kill_text.get_rect(topleft = (20, cherries_rect.bottom + 10))
        self.display_surface.blit(kill_text, kill_rect)
        self.display_score_total(kill_rect)
    
    def display_score_total(self, kill_rect):
        score_total_text = self.font.render(f'Score: {self.player.points}', True, (0, 0, 0))
        score_total_rect = score_total_text.get_rect(topleft = (20, kill_rect.bottom + 10))
        self.display_surface.blit(score_total_text, score_total_rect)
        self.display_health(score_total_rect)
    
    def display_health(self, score_total_rect): # Swap to a health bar at some point
        if self.player.health < 50:
            color = (255, 0, 0)  # Red
        elif self.player.health == 100:
            color = (76, 153, 0)  # Green
        else:
            color = (0, 0, 0)    # Black
        health_text = self.font.render(f'Health: {self.player.health}', True, color)
        health_rect = health_text.get_rect(topleft = (20, score_total_rect.bottom + 10))
        self.display_surface.blit(health_text, health_rect)

    # Main Game Loop
    def run(self):

        while self.running:
            #print(f"Current game state: {self.game_state}")
            dt = self.clock.tick(FRAMERATE) / 1000 

            # Handle all events in one place
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        if self.game_state == 'playing':
                            self.game_state = 'paused'
                        elif self.game_state == 'paused':
                            self.game_state = 'playing'
                    elif event.key == pygame.K_RETURN and self.game_state == 'menu':
                        self.game_state = 'playing'
                    elif event.key == pygame.K_COMMA and self.game_state == 'playing':
                        self.current_level += 1
                        self.level_loaded = False
            
            keys = pygame.key.get_pressed()
            if keys[pygame.K_c] and keys[pygame.K_LCTRL]:
                self.running = False

            # State machine
            if self.game_state == 'menu':
                self.run_menu()
            elif self.game_state == 'playing':
                self.run_game(dt, self.current_level)
            elif self.game_state == 'paused':
                self.run_pause_menu()
            elif self.game_state == 'settings':
                self.run_settings_menu()

            pygame.display.update()

        pygame.quit()

    def run_menu(self):
        # Clear the screen
        self.display_surface.fill(BG_COLOR)

        # Get screen dimensions
        screen_width = self.display_surface.get_width()
        screen_height = self.display_surface.get_height()

        # Create button dimensions
        button_width = 200
        button_height = 50
        button_spacing = 20  # Space between buttons

        # Create buttons (x, y, width, height)
        start_button = pygame.Rect(
            (screen_width - button_width) // 2,
            (screen_height - button_height * 2 - button_spacing) // 2,
            button_width,
            button_height
        )

        quit_button = pygame.Rect(
            (screen_width - button_width) // 2,
            (screen_height + button_spacing) // 2,
            button_width,
            button_height
        )

        # Handle mouse events
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()[0]  # Left click

        # Draw and handle Start button
        if start_button.collidepoint(mouse_pos):
            pygame.draw.rect(self.display_surface, (100, 100, 100), start_button)  # Lighter when hovered
            if mouse_clicked:
                self.game_state = 'playing'
                self.level_loaded = False
        else:
            pygame.draw.rect(self.display_surface, (70, 70, 70), start_button)  # Darker when not hovered

        # Draw and handle Quit button
        if quit_button.collidepoint(mouse_pos):
            pygame.draw.rect(self.display_surface, (100, 100, 100), quit_button)
            if mouse_clicked:
                self.running = False
        else:
            pygame.draw.rect(self.display_surface, (70, 70, 70), quit_button)

        # After drawing the Start button, add:
        start_text = self.font.render("Start Game", True, (255, 255, 255))  # White text
        start_text_rect = start_text.get_rect(center=start_button.center)
        self.display_surface.blit(start_text, start_text_rect)
        
        # After drawing the Quit button, add:
        quit_text = self.font.render("Quit", True, (255, 255, 255))  # White text
        quit_text_rect = quit_text.get_rect(center=quit_button.center)
        self.display_surface.blit(quit_text, quit_text_rect)

    def run_pause_menu(self):
        overlay = pygame.Surface(self.display_surface.get_size())
        overlay.fill(BG_COLOR)
        overlay.set_alpha(128)
        self.display_surface.blit(overlay, (0, 0))

        resume_text = self.font.render("Press P to Resume", True, (0, 0, 0))
        text_rect = resume_text.get_rect(center=(self.display_surface.get_width() // 2,
                                                self.display_surface.get_height() // 2))
        self.display_surface.blit(resume_text, text_rect)
    
    def run_settings_menu(self):
        # Draw settings menu with:
        # - Variables
        # - Settings
        # - Exit to Main Menu
        pass

    def load_level(self, level_num):
        # Clear existing level data
        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.collectible_sprites.empty()
        self.bullet_sprites.empty()
        self.enemy_sprites.empty()
        # other things?

        self.setup(level_num) # add level_num param

        # static level game timers
        self.bee_timer = Timer(2000, func = self.create_bee, autostart = True, repeat = True)

    def run_game(self, dt, level_num):

        if not self.level_loaded:
            self.load_level(level_num)
            self.level_loaded = True
            print

        self.bee_timer.update()
        self.all_sprites.update(dt)
        self.collision()

        if self.check_level_complete():
            self.current_level += 1
            self.level_loaded = False
        if hasattr(self, 'player') and self.player.health <= 0:
            self.game_state = 'game_over'
        # Draw
        self.display_surface.fill(BG_COLOR)
        if self.player:  # Safety check
            self.all_sprites.draw(self.player.rect.center)
        self.display_score_area()
        self.display_coins()
        '''# collision red square debug
        for sprite in self.collision_sprites:
            offset_rect = sprite.rect.copy()
            platform_rect_debug = sprite.rect.copy()
            offset_rect.topleft += self.all_sprites.offset
            platform_rect_debug.height = 16
            platform_rect_debug.topleft += self.all_sprites.offset
            pygame.draw.rect(self.display_surface, (0,0,0), platform_rect_debug, 1)
            pygame.draw.rect(self.display_surface, (255,0,0), offset_rect, 1)'''

    def run_game_over(self):
        # add TBD
        pass

    def check_level_complete(self):
        if hasattr(self, 'player'):
            if (hasattr(self.player, 'cherries') and 
                hasattr(self.player, 'total_cherries') and 
                hasattr(self.player, 'coins') and 
                hasattr(self.player, 'total_coins')):
                return (self.player.cherries == self.player.total_cherries and 
                        self.player.coins == self.player.total_coins)
        return False

if __name__ == '__main__':
    game = Game()
    game.run() 