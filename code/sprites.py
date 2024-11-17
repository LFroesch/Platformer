from settings import *
from timer import Timer
import pygame
import sys
from math import sin
from random import randint

class Sprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(topleft = pos)

class Bullet(Sprite):
    def __init__(self, surf, pos, direction, groups, bounds):
        super().__init__(pos, surf, groups)

        self.image = pygame.transform.flip(self.image, direction == -1, False)

        # movement
        self.direction = direction
        self.speed = 850
        self.bounds = bounds

    def update(self, dt):
        self.rect.x += self.direction * self.speed * dt
        if self.rect.x < -1000 or self.rect.x > self.bounds + 1000:
            self.kill()
        
class Fire(Sprite):
    def __init__(self, surf, pos, groups, player):
        super().__init__(pos, surf, groups)
        self.player = player
        self.flip = player.flip
        self.timer = Timer(100, autostart = True, func = self.kill)
        self.y_offset = pygame.Vector2(0,8)
        if self.player.flip:
            self.rect.midright = self.player.rect.midleft + self.y_offset
            self.image = pygame.transform.flip(self.image, True, False)
        else:
            self.rect.midleft = self.player.rect.midright + self.y_offset

    def update(self, _):
        self.timer.update()
        if self.player.flip:
            self.rect.midright = self.player.rect.midleft + self.y_offset
            
        else:
            self.rect.midleft = self.player.rect.midright + self.y_offset

        if self.flip != self.player.flip:
            self.kill()

class AnimatedSprite(Sprite):
    def __init__(self, frames, pos, groups):
        self.frames, self.frame_index, self.animation_speed = frames, 0, 10
        super().__init__(pos, self.frames[self.frame_index], groups)
    
    def animate(self, dt):
        self.frame_index += self.animation_speed * dt
        self.image = self.frames[int(self.frame_index) % len(self.frames)]

class Cherry(Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(pos, surf, groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft = pos)

class Collectible(AnimatedSprite):
    def __init__(self, frames, pos, groups):
        super().__init__(frames, pos, groups)
        
    def update(self, dt):
        self.animate(dt / 2)

class Coin(Collectible):
    def __init__(self, frames, rect, groups):
        super().__init__(frames, rect.topleft, groups)
        self.rect.bottomleft = rect.bottomleft
        self.main_rect = rect

class Diamond(Collectible):
    def __init__(self, frames, rect, groups):
        super().__init__(frames, rect.topleft, groups)
        self.rect.bottomleft = rect.bottomleft
        self.main_rect = rect

class Health_Potion(Collectible):
    def __init__(self, frames, rect, groups):
        super().__init__(frames, rect.topleft, groups)
        self.rect.bottomleft = rect.bottomleft
        self.main_rect = rect

class Enemy(AnimatedSprite):
    def __init__(self, frames, pos, groups):
        super().__init__(frames, pos, groups)
        self.death_timer = Timer(200, func = self.kill)

    def update(self, dt):
        self.death_timer.update()
        if not self.death_timer:
            self.move(dt)
            self.animate(dt)
        self.constraint()
    
    def destroy(self):
        self.death_timer.activate()
        self.animation_speed = 0
        self.image = pygame.mask.from_surface(self.image).to_surface()
        self.image.set_colorkey('black')
        
class Bee(Enemy):
    def __init__(self,frames, pos, groups, speed):
        super().__init__(frames, pos, groups)
        self.speed = speed
        self.amplitude = randint(400, 600)
        self.frequency = randint(300, 600)

    def move(self, dt):
        self.rect.x -= self.speed * dt
        # self.rect.y += sin(pygame.time.get_ticks() / self.frequency) * self.amplitude * dt

    def constraint(self):
        if self.rect.right == 0:
            self.kill()

class Worm(Enemy):
    def __init__(self, frames, rect, groups):
        super().__init__(frames, rect.topleft, groups)
        self.rect.bottomleft = rect.bottomleft
        self.main_rect = rect
        self.speed = randint(160, 200)
        self.direction = 1

    def move(self, dt):
        self.rect.x += self.direction * self.speed * dt

    def constraint(self):
        if not self.main_rect.contains(self.rect):
            self.direction *= -1
            self.frames = [pygame.transform.flip(surf, True, False) for surf in self.frames]

class Player(AnimatedSprite):

    def __init__(self, pos, groups, collision_sprites, collectible_sprites, frames, create_bullet, top_portal, bottom_portal, top_portal_two, bottom_portal_two):
        
        super().__init__(frames, pos, groups)
        
        # Movement and collision
        self.flip = False # Image Flip
        self.direction = pygame.Vector2()
        self.collision_sprites = collision_sprites
        self.create_bullet = create_bullet
        self.speed = 400
        self.gravity = 50
        self.cherries = 0
        self.health_pots = 0
        self.coins = 0
        self.diamonds = 0
        self.kills = 0
        self.points = 0
        self.collectible_sprites = collectible_sprites
        self.on_floor = True
        self.health = 100
        self.total_diamonds = 0
        self.total_cherries = 0
        self.total_coins = 0
        self.total_health_pots = 0
        self.top_portal = top_portal
        self.bottom_portal = bottom_portal
        self.top_portal_two = top_portal_two
        self.bottom_portal_two = bottom_portal_two

        # timer
        self.health_potion_cooldown = Timer(2000)
        self.points_tick_timer = Timer(300)
        self.damaged_buffer_timer = Timer(1500)
        self.shoot_timer = Timer(300)
        self.health_regen_timer = Timer(10000)
        self.teleport_timer = Timer(2000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = (int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - 
                   int(keys[pygame.K_LEFT] or keys[pygame.K_a]))
        if keys[pygame.K_SPACE] and self.on_floor:
            self.direction.y = -20
        if keys[pygame.K_v]:
            self.use_health_potion()
        if keys[pygame.K_f] and not self.shoot_timer:
            # print('shoot bullet')
            self.create_bullet(self.rect.center, -1 if self.flip else 1)
            self.shoot_timer.activate()
        if keys[pygame.K_c] and keys[pygame.K_LCTRL]:
            self.running = False

    def collect_collectibles(self):
        for collectible in self.collectible_sprites:
            if self.rect.colliderect(collectible.rect):
                if isinstance(collectible, Cherry):
                    self.cherries += 1
                    self.points += 1000
                    self.health = 100
                if isinstance(collectible, Health_Potion):
                    self.health_pots += 1
                    self.points += 1000
                    if self.health < 100:
                        self.health += 0
                if isinstance(collectible, Diamond):
                    self.diamonds += 1
                    self.points += 10000
                elif isinstance(collectible, Coin):
                    self.coins += 1
                    self.points += 500

                collectible.kill()  # This removes the sprite from all groups

    def move(self, dt):
        # horizontal
        self.rect.x += self.direction.x * self.speed * dt
        self.collision('horizontal')
        
        # vertical
        self.direction.y += self.gravity * dt
        self.rect.y += self.direction.y
        self.collision('vertical')

    def collision(self, direction):
        if not self.teleport_timer.active:
            if self.top_portal_two is not None and self.bottom_portal_two is not None:
                if self.rect.colliderect(self.top_portal_two.rect):
                    self.rect.centerx = self.bottom_portal_two.rect.centerx
                    self.rect.bottom = self.bottom_portal_two.rect.top
                    self.teleport_timer.activate()
                    return

                elif self.rect.colliderect(self.bottom_portal_two.rect):
                    self.rect.centerx = self.top_portal_two.rect.centerx
                    self.rect.top = self.top_portal_two.rect.top
                    self.teleport_timer.activate()
                    return
                
            if self.top_portal is not None and self.bottom_portal is not None:  # Check existence first
                if self.rect.colliderect(self.top_portal.rect):
                    self.rect.centerx = self.bottom_portal.rect.centerx
                    self.rect.bottom = self.bottom_portal.rect.top
                    self.teleport_timer.activate()
                    return

                elif self.rect.colliderect(self.bottom_portal.rect):
                    self.rect.centerx = self.top_portal.rect.centerx
                    self.rect.top = self.top_portal.rect.top
                    self.teleport_timer.activate()
                    return
            

        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.rect):
                if direction == 'horizontal':
                    if self.direction.x > 0: self.rect.right = sprite.rect.left
                    if self.direction.x < 0: self.rect.left = sprite.rect.right
                if direction == 'vertical':
                    if self.direction.y > 0: self.rect.bottom = sprite.rect.top
                    if self.direction.y < 0: self.rect.top = sprite.rect.bottom
                    self.direction.y = 0

    def check_floor(self):
        bottom_rect = pygame.FRect((0,0), (self.rect.width, 2)).move_to(midtop = self.rect.midbottom)
        level_rects = [sprite.rect for sprite in self.collision_sprites]
        self.on_floor = True if bottom_rect.collidelist(level_rects) >= 0 else False

    def animate(self, dt):
        if self.direction.x:
            self.frame_index += self.animation_speed * dt
            self.flip = self.direction.x < 0
        else:
            self.frame_index = 0
        self.frame_index = 1 if not self.on_floor else self.frame_index
        self.image = self.frames[int(self.frame_index) % len(self.frames)]
        self.image = pygame.transform.flip(self.image, self.flip, False)

    def take_damage(self, damage):
        if not self.damaged_buffer_timer.active:
            self.health -= damage
            self.damaged_buffer_timer.activate()

    def heal_over_time(self): # Also has passive point generation
        if self.health < 100:
            if not self.health_regen_timer.active:
                self.health += 0
                print(self.health)
                self.health_regen_timer.activate()

    def points_over_time(self):
        if not self.points_tick_timer.active:
            self.points += 0
            self.points_tick_timer.activate()
        
    def update(self, dt):

        self.points_over_time()
        self.heal_over_time()
        self.health_potion_cooldown.update()
        self.teleport_timer.update()
        self.points_tick_timer.update()
        self.health_regen_timer.update()   
        self.damaged_buffer_timer.update()
        self.shoot_timer.update()
        self.check_floor()
        self.input()
        self.move(dt)
        self.animate(dt)
        self.collect_collectibles()
    
    def use_health_potion(self):
        if self.health_pots >= 1:
            if not self.health_potion_cooldown.active:
                self.health_pots -= 1
                if self.health <= 50:
                    self.health += 50
                else:
                    self.health = 100
                self.health_potion_cooldown.activate()

class Portal(Sprite):
    def __init__(self, pos, surf, groups, portal_type):
        super().__init__(pos, surf, groups)
        self.portal_type = portal_type

        # Print Debug for portal init
        # print(f"Created {portal_type} portal at position {pos}")
        
