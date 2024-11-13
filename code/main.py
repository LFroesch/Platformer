from settings import * 
from sprites import *
from groups import AllSprites
import os
import pygame._sdl2 as sdl2
import pygame.display

class Game:
    def __init__(self):
        print("Starting platform game!")
        os.environ['SDL_VIDEO_DISPLAY'] = '1'
        os.environ['SDL_VIDEO_WINDOW_POS'] = '1920,0'	

        pygame.init()

        # Let's see what we're working with
        displays = pygame.display.get_desktop_sizes()
        print(f"Available displays: {displays}")

        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Platformer')

        self.clock = pygame.time.Clock()
        self.running = True

        # groups 
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()

        # Load Game
        self.setup()

    def setup (self):
        tmx_map = load_pygame(join('data', 'maps', 'world.tmx'))
        for x, y, image in tmx_map.get_layer_by_name('Main').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites, self.collision_sprites))
        for x, y, image in tmx_map.get_layer_by_name('Decoration').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites))
        for obj in tmx_map.get_layer_by_name('Entities'):
            if obj.name == 'Player':
                self.player = Player((obj.x, obj.y), self.all_sprites, self.collision_sprites)

    def run(self):
        while self.running:
            dt = self.clock.tick(FRAMERATE) / 1000 

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False 
            
            # update
            self.all_sprites.update(dt)

            # draw
              # draws red rectangles
            self.display_surface.fill(BG_COLOR)
            self.all_sprites.draw(self.player.rect.center)
            for sprite in self.collision_sprites:
                offset_rect = sprite.rect.copy()
                offset_rect.topleft += self.all_sprites.offset
                pygame.draw.rect(self.display_surface, (255,0,0), offset_rect, 1)
            pygame.display.update()
        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run() 