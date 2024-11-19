from settings import * 
from sprites import *
from groups import AllSprites
from popuptext import *
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
        try:
            self.font = pygame.font.Font('data/fonts/PressStart2P-Regular.ttf', 16)
            self.large_font = pygame.font.Font('data/fonts/PressStart2P-Regular.ttf', 32)
        except:
            print("Pixel font not found, using fallback monospace")
            self.font = pygame.font.SysFont('courier', 16)
            self.large_font = pygame.font.SysFont('courier', 32)
        
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Platformer')

        # BG
        self.background = pygame.image.load('data/graphics/bg2.png').convert()
        self.background = pygame.transform.scale(self.background, (WINDOW_WIDTH, WINDOW_HEIGHT))

        self.SPAWN_MARGIN = 10 * TILE_SIZE
        self.PLAYABLE_HEIGHT = 40 * TILE_SIZE
        self.PLAYABLE_WIDTH = 50 * TILE_SIZE

        # game states and clock
        self.clock = pygame.time.Clock()
        self.game_state = 'menu'
        self.running = True
        self.current_level = 1
        self.total_levels = 6
        self.level_loaded = False
        self.show_inventory = False
        self.popup_system = PopupText(self.display_surface, self.font)
        self.shop = None
        self.show_shop = False
        self.shop_interaction_cooldown = Timer(500)
        self.level_start_coins = 0
        self.death_total = 0
        self.level_start_points = 0 

        # transition values
        self.transition_timer = 0
        self.transition_duration = 3000
        self.fade_alpha = 0
        self.fade_direction = 1

        # groups 
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.collectible_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()
        self.trader_sprites = pygame.sprite.Group()

        self.load_assets()

    def create_bee(self):
        spawn_x = self.SPAWN_MARGIN + self.PLAYABLE_WIDTH
        random_tile_position = randint(0, self.PLAYABLE_HEIGHT // 64)

        spawn_y = (random_tile_position * 64) + self.SPAWN_MARGIN
        Bee(frames = self.bee_frames,
            pos = (spawn_x, spawn_y),
            groups = (self.all_sprites, self.enemy_sprites),
            speed = randint(100, 300))

    def create_bullet(self, pos, direction):
        x = pos[0] + direction * 34 if direction == 1 else pos[0] + direction * 34 - self.bullet_surf.get_width()
        Bullet(self.bullet_surf, (x, pos[1]), direction, (self.all_sprites, self.bullet_sprites), self.level_width)
        Fire(self.fire_surf, pos, self.all_sprites, self.player)

    def load_assets(self):
        self.v_icon = import_image('data', 'graphics', 'V')
        self.diamond_frames = import_folder('images', 'collectibles', 'diamond')
        self.health_potion_icon = import_image('images', 'collectibles','health_potion', '09')
        self.health_potion_frames = import_folder('images', 'collectibles', 'health_potion')
        self.player_frames = import_folder('images', 'player')
        self.bullet_surf = import_image('images', 'gun', 'bullet')
        self.fire_surf = import_image('images', 'gun', 'fire')
        self.bee_frames = import_folder('images', 'enemies', 'bee')
        self.worm_frames = import_folder('images', 'enemies', 'worm')
        self.coin_frames = import_folder('images', 'collectibles', 'coin')
        self.trader_frames = import_folder('images', 'friendly', 'trader')
        scaled_frames = []
        for frame in self.trader_frames:
            scaled = pygame.transform.scale_by(frame, 1.5)
            scaled_frames.append(scaled)
        self.trader_frames = scaled_frames

        self.ui_assets = {
            # Static UI frames
            'inventory': import_image('images', 'ui', 'inventory'),
            'score_panel': import_image('images', 'ui', 'score_backdrop'),
            'status_scroll': import_image('images', 'ui', 'banner'),
            'shop_ui': import_image('images', 'ui', 'shop_inv1'),
            'dialogue': import_image('images', 'ui', 'dialogue'),
        }

        # Scale UI elements to desired sizes
        self.ui_assets['inventory'] = pygame.transform.scale(
            self.ui_assets['inventory'],
            (100, 300)
        )
        self.ui_assets['score_panel'] = pygame.transform.scale(
            self.ui_assets['score_panel'],
            (290, 200)
        )
        self.ui_assets['status_scroll'] = pygame.transform.scale(
            self.ui_assets['status_scroll'],
            (400, 80)
        )
        self.ui_assets['shop_ui'] = pygame.transform.scale(
            self.ui_assets['shop_ui'],
            (800, 800)
        )
        self.ui_assets['dialogue'] = pygame.transform.scale(
            self.ui_assets['dialogue'],
            (300, 150)
        )
        self.popup_system.add_popup_image('status_scroll', self.ui_assets['status_scroll'])
        self.popup_system.add_popup_image('shop_ui', self.ui_assets['shop_ui'])
        self.popup_system.add_popup_image('dialogue', self.ui_assets['dialogue'])

        # audio
        self.audio = audio_importer('audio')
        # self.audio['music'].play()

    def handle_shop_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE] and self.show_shop:
            self.show_shop = False
            return
        if keys[pygame.K_e] and not self.shop_interaction_cooldown.active:
            trader_colliding = pygame.sprite.spritecollide(self.player, self.trader_sprites, False, pygame.sprite.collide_mask)
            if trader_colliding and not self.show_shop:
                self.show_shop = True
                self.shop_interaction_cooldown.activate()
        if self.show_shop:
            trader_colliding = pygame.sprite.spritecollide(self.player, self.trader_sprites, False, pygame.sprite.collide_mask)
            if not trader_colliding:
                self.show_shop = False

    def setup (self, level_num):
        self.level_num = level_num
        tmx_map = load_pygame(join('data', 'maps', f'world{self.level_num}.tmx'))
        self.level_width = tmx_map.width * TILE_SIZE
        self.level_height = tmx_map.height * TILE_SIZE
        
        # Portal Surfaces
        portal_surf = pygame.Surface((64, 64))
        portal_surf.fill('blue')
        portal2_surf = pygame.Surface((64, 64))
        portal2_surf.fill('red')

        # Portal Spawning
        if self.current_level == 1:
            portal_x = (18 + 10) * TILE_SIZE
            top_y = (2 + 10) * TILE_SIZE
            bottom_y = (38 + 10) * TILE_SIZE
            self.top_portal = Portal((portal_x, top_y), portal_surf, [self.all_sprites], 'top')
            self.bottom_portal = Portal((portal_x, bottom_y), portal_surf, [self.all_sprites], 'bottom')
            self.top_portal_two = None
            self.bottom_portal_two = None

        elif self.current_level ==2:
            top_x = (35 + 10) * TILE_SIZE
            top_y = (6 + 10) * TILE_SIZE
            bottom_x = (5 + 10) * TILE_SIZE
            bottom_y = (35 + 10) * TILE_SIZE
            self.top_portal = Portal((top_x, top_y), portal_surf, [self.all_sprites], 'top')
            self.bottom_portal = Portal((bottom_x, bottom_y), portal_surf, [self.all_sprites], 'bottom')
            self.top_portal_two = None
            self.bottom_portal_two = None

        elif self.current_level == 3:
            top_x = (46) * TILE_SIZE
            top_y = (31) * TILE_SIZE
            bottom_x = (11) * TILE_SIZE
            bottom_y = (48) * TILE_SIZE
            self.top_portal = Portal((top_x, top_y), portal_surf, [self.all_sprites], 'top')
            self.bottom_portal = Portal((bottom_x, bottom_y), portal_surf, [self.all_sprites], 'bottom')
            top_x2 = (58) * TILE_SIZE
            top_y2 = (43) * TILE_SIZE
            bottom_x2 = (25) * TILE_SIZE
            bottom_y2 = (32) * TILE_SIZE
            self.top_portal_two = Portal((top_x2, top_y2), portal2_surf, [self.all_sprites], 'top')
            self.bottom_portal_two = Portal((bottom_x2, bottom_y2), portal2_surf, [self.all_sprites], 'bottom')
        
        elif self.current_level == 5:
            level5_portal_surf = portal_surf.copy()
            level5_portal_surf.set_alpha(64)
            top_x = (56) * TILE_SIZE
            top_y = (18) * TILE_SIZE
            bottom_x = (16) * TILE_SIZE
            bottom_y = (44) * TILE_SIZE
            self.top_portal = Portal((top_x, top_y), level5_portal_surf, [self.all_sprites], 'top')
            self.bottom_portal = Portal((bottom_x, bottom_y), level5_portal_surf, [self.all_sprites], 'bottom')
            self.top_portal_two = None
            self.bottom_portal_two = None
            
        else:
            self.top_portal = None
            self.bottom_portal = None
            self.top_portal_two = None
            self.bottom_portal_two = None

        for x, y, image in tmx_map.get_layer_by_name('Main').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites, self.collision_sprites))

        for x, y, image in tmx_map.get_layer_by_name('Decoration').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites))
        
        try:
            for x, y, image in tmx_map.get_layer_by_name('Decoration FG').tiles():
                Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites))
        except ValueError:
            pass

        previous_points = 0
        previous_kills = 0
        if hasattr(self, 'player'):
            previous_points = self.player.points
            previous_kills = self.player.kills
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
                    self.bottom_portal,
                    self.top_portal_two,
                    self.bottom_portal_two,
                    self.display_surface
                    )
                # Restore previous stats
                self.player.points = previous_points
                self.player.kills = previous_kills

            if obj.name == 'Cherry':  # Or whatever you named your objects in Tiled
                cherry_image = tmx_map.get_tile_image_by_gid(obj.gid)
                Cherry((obj.x, obj.y), cherry_image, [self.all_sprites, self.collectible_sprites])
                self.player.total_cherries += 1
            
            if obj.name == 'Worm':
                Worm(self.worm_frames, pygame.FRect(obj.x, obj.y, obj.width, obj.height), (self.all_sprites, self.enemy_sprites))
            
            if obj.name == 'Coin':
                Coin(self.coin_frames, pygame.FRect(obj.x, obj.y - 2, obj.width, obj.height), (self.all_sprites, self.collectible_sprites))
                self.player.total_coins += 1
            
            if obj.name == 'Health_Potion':
                Health_Potion(self.health_potion_frames, pygame.FRect(obj.x, obj.y - 12, obj.width, obj.height), (self.all_sprites, self.collectible_sprites))
                self.player.total_health_pots += 1
            
            if obj.name == 'Diamond':
                Diamond(self.diamond_frames, pygame.FRect(obj.x, obj.y, obj.width, obj.height), (self.all_sprites, self.collectible_sprites))
                self.player.total_diamonds += 1

            if obj.name == 'Trader':
                Trader(self.trader_frames, (obj.x - 44, obj.y - 95), (self.all_sprites, self.trader_sprites))
            
        self.shop = Shop(self)

        
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
            if not enemy.is_dying:
                if isinstance(enemy, Bee):
                    self.player.take_damage(20)
                    self.popup_system.add_message("Ouch a bee!\n-20 HP", image_type='status_scroll')
                    enemy.destroy()
                else:
                    self.player.take_damage(25)
                    self.popup_system.add_message("AH a worm!\n-25 HP")
                if hasattr(self, 'player') and self.player.health <= 40:
                    self.popup_system.add_message("Low health!\nDrink a potion!", 4000)

        # trader and player
        trader_sprites = pygame.sprite.spritecollide(self.player, self.trader_sprites, False, pygame.sprite.collide_mask)
        for trader in trader_sprites:
            if not self.dialogue_timer.active:
                self.popup_system.add_message("'ello travla!", duration=3000, image_type='dialogue')
                self.dialogue_timer.activate()
                break

    def display_score_area(self):
        x, y = 10, 10

        self.display_surface.blit(self.ui_assets['score_panel'], (x, y))
        score_x = x + 35
        score_y = y + 15

        self.display_coins(score_x, score_y)


    def display_coins(self, x, y):
        if self.player.coins == self.player.total_coins:
            color = (76, 153, 0)  # Green
        else:
            color = (0, 0, 0)    # Black
        coins_text = self.font.render(f'Coins: {self.player.coins} / {self.player.total_coins}', True, color)
        coins_rect = coins_text.get_rect(topleft = (x, y))
        self.display_surface.blit(coins_text, coins_rect)
        self.display_diamonds(coins_rect)

    def display_diamonds(self, coins_rect):
        if self.player.diamonds == self.player.total_diamonds:
            color = (76, 153, 0)  # Green
        else:
            color = (0, 0, 0)    # Black
        diamonds_text = self.font.render(f'Diamonds: {self.player.diamonds} / {self.player.total_diamonds}', True, color)
        diamonds_rect = diamonds_text.get_rect(topleft = (20, coins_rect.bottom + 10))
        self.display_surface.blit(diamonds_text, diamonds_rect)
        self.display_kills(diamonds_rect)

    def display_kills(self, diamonds_rect):
        kill_text = self.font.render(f'Kills: {self.player.kills}', True, (0,0,0))
        kill_rect = kill_text.get_rect(topleft = (20, diamonds_rect.bottom + 10))
        self.display_surface.blit(kill_text, kill_rect)
        self.display_score_total(kill_rect)
    
    def display_score_total(self, kill_rect):
        score_total_text = self.font.render(f'Score: {self.player.points}', True, (0, 0, 0))
        score_total_rect = score_total_text.get_rect(topleft = (20, kill_rect.bottom + 10))
        self.display_surface.blit(score_total_text, score_total_rect)
        self.display_health(score_total_rect)
    
    def display_health(self, score_total_rect):
        if self.player.health < 50:
            color = (255, 0, 0)  # Red
        elif self.player.health == 100:
            color = (76, 153, 0)  # Green
        else:
            color = (0, 0, 0)    # Black
        health_text = self.font.render(f'Health: {self.player.health}', True, color)
        health_rect = health_text.get_rect(topleft = (30, score_total_rect.bottom + 10))
        self.display_surface.blit(health_text, health_rect)
        self.display_health_potions()
        self.display_level(health_rect)

    def display_level(self, health_rect):
        color = (0, 0, 0)    # Black
        level_text = self.font.render(f'Level: {self.current_level} / {self.total_levels}', True, color)
        level_rect = level_text.get_rect(topleft = (30, health_rect.bottom + 10))
        self.display_surface.blit(level_text, level_rect)
        self.display_total_coins(level_rect)
    
    def display_total_coins(self, level_rect):
        color = (0, 0, 0)    # Black
        total_coins_text = self.font.render(f'Total Coins: {self.level_start_coins + self.player.coins}', True, color)
        total_coins_rect = total_coins_text.get_rect(topleft = (30, level_rect.bottom + 10))
        self.display_surface.blit(total_coins_text, total_coins_rect)

    def display_health_potions(self):
        inventory_x = 20
        inventory_y = 300
        
        self.display_surface.blit(self.ui_assets['inventory'], (inventory_x, inventory_y))
        
        potion_x = inventory_x + 25
        potion_y = inventory_y + 30
        self.display_surface.blit(self.health_potion_icon, (potion_x, potion_y))
        
        count_x = potion_x + 40
        count_y = potion_y + 10
        potion_count_text = self.font.render(str(self.player.health_pots), True, BG_WHITE)
        potion_count_text2 = self.font.render(str(self.player.health_pots), True, '#000000')
        self.display_surface.blit(potion_count_text2, (count_x + 1, count_y + 1))
        self.display_surface.blit(potion_count_text, (count_x, count_y))
        
        v_x = potion_x + 75
        v_y = potion_y + 10
        self.display_surface.blit(self.v_icon, (v_x, v_y))

    def run(self):
        
        while self.running:
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
                    elif event.key == pygame.K_RETURN:
                        if self.game_state == 'menu':
                            self.game_state = 'playing'
                    elif event.key == pygame.K_COMMA and self.game_state == 'playing':
                        self.current_level += 1
                        self.start_level_transition()
                    elif event.key == pygame.K_1 and self.game_state == 'playing':
                        self.current_level = 1
                        self.start_level_transition()
                    elif event.key == pygame.K_2 and self.game_state == 'playing':
                        self.current_level = 2
                        self.start_level_transition()
                    elif event.key == pygame.K_3 and self.game_state == 'playing':
                        self.current_level = 3
                        self.start_level_transition()
                    elif event.key == pygame.K_4 and self.game_state == 'playing':
                        self.current_level = 4
                        self.start_level_transition()
                    elif event.key == pygame.K_5 and self.game_state == 'playing':
                        self.current_level = 5
                        self.start_level_transition()
            
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
            elif self.game_state == 'level_transition':
                self.run_level_transition(dt)
            elif self.game_state == 'game_over':
                self.run_game_over()

            pygame.display.update()

        pygame.quit()

    def reset_game(self):
        """Reset the game state to start a new game"""
        self.current_level = 1
        self.level_loaded = False
        self.game_state = 'playing'
        self.death_total = 0
        self.level_start_coins = 0
        self.level_start_points = 0

    def run_menu(self):
        self.display_surface.fill(BG_COLOR)
        self.display_surface.blit(self.background, (0, 0))

        screen_width = self.display_surface.get_width()
        screen_height = self.display_surface.get_height()

        button_width = 200
        button_height = 50
        button_spacing = 20  # Space between buttons

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

        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()[0]  # Left click

        if start_button.collidepoint(mouse_pos):
            pygame.draw.rect(self.display_surface, (100, 100, 100), start_button)  # Lighter when hovered
            if mouse_clicked:
                self.game_state = 'playing'
                self.level_loaded = False
        else:
            pygame.draw.rect(self.display_surface, (70, 70, 70), start_button)  # Darker when not hovered

        if quit_button.collidepoint(mouse_pos):
            pygame.draw.rect(self.display_surface, (100, 100, 100), quit_button)
            if mouse_clicked:
                self.running = False
        else:
            pygame.draw.rect(self.display_surface, (70, 70, 70), quit_button)

        start_text = self.font.render("Start Game", True, (255, 255, 255))  # White text
        start_text_rect = start_text.get_rect(center=start_button.center)
        self.display_surface.blit(start_text, start_text_rect)
        
        quit_text = self.font.render("Quit", True, (255, 255, 255))  # White text
        quit_text_rect = quit_text.get_rect(center=quit_button.center)
        self.display_surface.blit(quit_text, quit_text_rect)

    def run_pause_menu(self):
        center_x = self.display_surface.get_width() // 2
        center_y = self.display_surface.get_height() // 2 - 60  # Your text offset

        overlay = pygame.Surface((300, 60))
        overlay.fill(BG_WHITE)
        overlay.set_alpha(64)

        overlay2 = pygame.Surface ((302, 62))
        overlay2.fill('#000000')
        overlay2.set_alpha(64)

        overlay_x = center_x - 150
        overlay_y = center_y - 30
        self.display_surface.blit(overlay2, (overlay_x -1 , overlay_y-1))
        self.display_surface.blit(overlay, (overlay_x, overlay_y))

        resume_text = self.font.render("Press P to Resume", True, (0, 0, 0))
        text_rect = resume_text.get_rect(center=(center_x, center_y))
        self.display_surface.blit(resume_text, text_rect)
    
    def run_settings_menu(self):
        # Draw settings menu with:
        # - Variables
        # - Settings
        # - Exit to Main Menu
        pass

    def load_level(self, level_num):
        if hasattr(self, 'player'):
            self.level_start_points += self.player.points
            self.level_start_coins += self.player.coins
        if hasattr(self, 'top_portal') and self.top_portal is not None:
            self.top_portal.kill()
        if hasattr(self, 'bottom_portal') and self.bottom_portal is not None:
            self.bottom_portal.kill()
        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.collectible_sprites.empty()
        self.bullet_sprites.empty()
        self.enemy_sprites.empty()

        self.setup(level_num)

        self.bee_timer = Timer(1000, func = self.create_bee, autostart = True, repeat = True)
        self.dialogue_timer = Timer(3000)

    def run_game(self, dt, level_num):
        if level_num > self.total_levels:
            self.game_state = 'game_over'
            return
        if not self.level_loaded:
            self.load_level(level_num)
            self.level_loaded = True

        self.bee_timer.update()
        self.dialogue_timer.update()
        self.shop_interaction_cooldown.update()
        self.all_sprites.update(dt)
        self.collision()
        self.handle_shop_input()

        if self.check_level_complete():
            self.current_level += 1
            self.start_level_transition()
            return
        
        if hasattr(self, 'player') and self.player.health <= 0:
            self.death_total += 1
            self.game_state = 'game_over'
            self.player.coins = 0
            self.player.health_pots = 0
        
        
        self.display_surface.fill(BG_COLOR)
        # self.display_surface.blit(self.background, (0, 0))
        if self.player:
            self.all_sprites.draw(self.player.rect.center)
        self.popup_system.update()
        self.popup_system.draw()
        if self.show_shop:
            shop_pos = (WINDOW_WIDTH // 2 - 400, WINDOW_HEIGHT // 2 - 400)
            self.display_surface.blit(self.ui_assets['shop_ui'], shop_pos)
            
            # Draw shop items
            if self.shop:
                item_start_x = shop_pos[0] + 50
                item_start_y = shop_pos[1] + 50
                for idx, item in enumerate(self.shop.items):
                    # Draw item icon
                    icon_pos = (item_start_x, item_start_y + idx * 64)
                    self.display_surface.blit(item['icon'], icon_pos)
                    
                    # Draw item name and price
                    name_text = self.font.render(item['name'], True, (0, 0, 0))
                    price_text = self.font.render(f"{item['price']} coins", True, (0, 0, 0))
                    self.display_surface.blit(name_text, (icon_pos[0] + 180, icon_pos[1]))
                    self.display_surface.blit(price_text, (icon_pos[0] + 180, icon_pos[1] + 20))
        self.display_score_area()

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
        """Handle the game over screen"""
        # Create semi-transparent overlay
        overlay = pygame.Surface(self.display_surface.get_size())
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.display_surface.blit(overlay, (0, 0))
        
        # Calculate vertical positioning
        screen_center_y = self.display_surface.get_height() // 2
        line_spacing = 40
        start_y = screen_center_y - 100
        
        # Draw game over text
        game_over_text = self.large_font.render("Game Over", True, (255, 0, 0))
        game_over_rect = game_over_text.get_rect(center=(self.display_surface.get_width() // 2, start_y))
        self.display_surface.blit(game_over_text, game_over_rect)
        
        # Draw death count
        death_text = self.font.render(f"Total Deaths: {self.death_total}", True, (255, 255, 255))
        death_rect = death_text.get_rect(center=(self.display_surface.get_width() // 2, start_y + line_spacing))
        self.display_surface.blit(death_text, death_rect)
        
        # Draw final score
        if hasattr(self, 'player'):
            score_text = self.font.render(f"Score: {self.player.points}", True, (255, 255, 255))
            score_rect = score_text.get_rect(center=(self.display_surface.get_width() // 2, start_y + line_spacing * 2))
            self.display_surface.blit(score_text, score_rect)
        
        # Draw current level
        level_text = self.font.render(f"Level: {self.current_level} / {self.total_levels}", True, (255, 255, 255))
        level_rect = level_text.get_rect(center=(self.display_surface.get_width() // 2, start_y + line_spacing * 3))
        self.display_surface.blit(level_text, level_rect)

        # Draw restart prompt with different text based on level
        if self.current_level >= self.total_levels:
            restart_text = self.font.render("Press ENTER to Start New Game", True, (255, 255, 255))
        else:
            restart_text = self.font.render("Press ENTER to Retry Level", True, (255, 255, 255))
        restart_rect = restart_text.get_rect(center=(self.display_surface.get_width() // 2, start_y + line_spacing * 4))
        self.display_surface.blit(restart_text, restart_rect)

        # Add key handler in the event loop section
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RETURN]:
            if self.current_level >= self.total_levels:
                # Complete reset if at final level
                self.reset_game()
                self.player.points = 0
                self.player.health_pots = 0
                self.death_total = 0
            else:
                # Just reload current level if not at final level
                self.game_state = 'playing'
                self.level_loaded = False
                self.player.points = self.level_start_points

    def check_level_complete(self):
        if hasattr(self, 'player'):
            if (hasattr(self.player, 'cherries') and 
                hasattr(self.player, 'total_cherries') and 
                hasattr(self.player, 'coins') and 
                hasattr(self.player, 'total_coins')):
                return (self.player.cherries == self.player.total_cherries and 
                        self.player.coins == self.player.total_coins)
        return False

    def start_level_transition(self):
        """Start the level transition sequence"""
        self.game_state = 'level_transition'
        self.transition_timer = pygame.time.get_ticks()
        self.fade_alpha = 0
        self.fade_direction = 1

    def run_level_transition(self, dt):
        """Handle the level transition screen"""
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.transition_timer
        
        # Create overlay surface for fade effect
        overlay = pygame.Surface(self.display_surface.get_size())
        overlay.fill((0, 0, 0))
        
        # Calculate fade alpha
        if self.fade_direction == 1:  # Fading in
            self.fade_alpha = min(255, (elapsed / (self.transition_duration / 2)) * 255)
            if self.fade_alpha >= 255:
                self.fade_direction = -1
        else:  # Fading out
            self.fade_alpha = max(0, 255 - ((elapsed - (self.transition_duration / 2)) / (self.transition_duration / 2)) * 255)
        
        # Apply fade
        overlay.set_alpha(self.fade_alpha)
        
        # Draw background
        self.display_surface.fill(BG_COLOR)
        
        # Draw level text
        level_text = self.large_font.render(f"Level {self.current_level}", True, (255, 255, 255))
        level_rect = level_text.get_rect(center=(self.display_surface.get_width() // 2,
                                               self.display_surface.get_height() // 2))
        
        # Draw score if available
        if hasattr(self, 'player'):
            score_text = self.font.render(f"Score: {self.player.points}", True, (255, 255, 255))
            score_rect = score_text.get_rect(center=(self.display_surface.get_width() // 2,
                                                   self.display_surface.get_height() // 2 + 50))
            self.display_surface.blit(score_text, score_rect)
        
        self.display_surface.blit(level_text, level_rect)
        self.display_surface.blit(overlay, (0, 0))
        
        # Check if transition is complete
        if elapsed >= self.transition_duration:
            self.game_state = 'playing'
            self.level_loaded = False

if __name__ == '__main__':
    game = Game()
    game.run() 