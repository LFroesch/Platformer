from settings import * 
from sprites import *
from groups import AllSprites
import os
import pygame._sdl2 as sdl2
import pygame.display
from support import *
from random import randint

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
        self.running = True

        # groups 
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()

        # Load Game
        self.load_assets()
        self.setup()

        # timers
        self.bee_timer = Timer(250, func = self.create_bee, autostart = True, repeat = True)

    def create_bee(self):
        Bee(frames = self.bee_frames,
            pos = ((self.level_width + WINDOW_WIDTH),(randint(0, self.level_height))),
            groups = (self.all_sprites, self.enemy_sprites),
            speed = randint(200, 400))

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

        # audio
        self.audio = audio_importer('audio')
        # self.audio['music'].play()

    def setup (self):
        tmx_map = load_pygame(join('data', 'maps', 'world.tmx'))
        print(f"W: {tmx_map.width}")
        print(f"H: {tmx_map.height}")
        self.level_width = tmx_map.width * TILE_SIZE
        self.level_height = tmx_map.height * TILE_SIZE

        for x, y, image in tmx_map.get_layer_by_name('Main').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites, self.collision_sprites))
        for x, y, image in tmx_map.get_layer_by_name('Decoration').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites))
        for obj in tmx_map.get_layer_by_name('Entities'):
            #print("Object name:", obj.name)
            if obj.name == 'Player':
                self.player = Player((obj.x, obj.y), self.all_sprites, self.collision_sprites, self.coins, self.player_frames, self.create_bullet)
            if obj.name == 'Cherry':  # Or whatever you named your objects in Tiled
                cherry_image = tmx_map.get_tile_image_by_gid(obj.gid)
                #print("Cherry position:", obj.x, obj.y)  # Debug position
                #print("Cherry image:", cherry_image) 
                Cherry((obj.x, obj.y), cherry_image, [self.all_sprites, self.coins])
            if obj.name == 'Worm':
                Worm(self.worm_frames, pygame.FRect(obj.x, obj.y, obj.width, obj.height), (self.all_sprites, self.enemy_sprites))
        
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
        x, y = 10, 10  # Starting position for texts
        width = 250    # Estimated width of the text area
        height = 150   # Estimated height to cover all 4 lines (adjust as needed)

        # Create a semi-transparent surface
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((128, 128, 128, 128))  # Gray color with 50% transparency

        # Render it on the display surface
        self.display_surface.blit(overlay, (x, y))

    def display_score(self):
        score_text = self.font.render(f'Cherries: {self.player.coins}', True, (0, 0, 0))
        score_rect = score_text.get_rect(topleft = (20, 20))
        self.display_surface.blit(score_text, score_rect)
        self.display_kills(score_rect)

    def display_kills(self, score_rect):
        kill_text = self.font.render(f'Kills: {self.player.kills}', True, (0,0,0))
        kill_rect = kill_text.get_rect(topleft = (20, score_rect.bottom + 10))
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
        health_rect = health_text.get_rect(topleft = (20, score_total_rect.bottom + 10))
        self.display_surface.blit(health_text, health_rect)

    def run(self):
        while self.running:
            dt = self.clock.tick(FRAMERATE) / 1000 

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False 
            
            # update
            self.bee_timer.update()
            self.all_sprites.update(dt)
            self.collision()
            if self.player.health <= 0:
                self.running = False

            # draw
            self.display_surface.fill(BG_COLOR)
            self.all_sprites.draw(self.player.rect.center)
            """
            # collision red square debug
            for sprite in self.collision_sprites:
                offset_rect = sprite.rect.copy()
                offset_rect.topleft += self.all_sprites.offset
                pygame.draw.rect(self.display_surface, (255,0,0), offset_rect, 1)
            """
            self.display_score_area()
            self.display_score()
            
            pygame.display.update()
        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run() 