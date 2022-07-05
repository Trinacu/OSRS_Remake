import pygame as pg
import os
import numpy as np
from random import choice
import json

import matplotlib.pyplot as plt

from settings import *
from tilemap import collide_hit_rect
from tilemap import collide_sense
from copy import copy
from dataclasses import asdict
vect = pg.math.Vector2

from skills import *
from gear import *
from items import *
from general import *

from functools import partial

from PIL import Image


def draw_circle_alpha(surface, color, center, radius):
    target_rect = pg.Rect(center, (0, 0)).inflate((radius * 2, radius * 2))
    shape_surf = pg.Surface(target_rect.size, pg.SRCALPHA)
    pg.draw.circle(shape_surf, color, (radius, radius), radius)
    surface.blit(shape_surf, target_rect)

def draw_text(surface, text, pos, bck_color=(222,222,222)):
    textsurface = arial10Font.render(text, True, BLACK, bck_color)
    surface.blit(textsurface, pos)


class Entity(pg.sprite.Sprite):
    def __init__(self, game, sprite_groups, x, y):
        self.groups = game.all_sprites, game.entities, sprite_groups
        super().__init__(self.groups)
        self.game = game
        self.pos = vect(x, y)
        self.prev_pos = copy(self.pos)
        self.respawn_pos = copy(self.pos)
        self.vel = vect(0, 0)
        self.target_entity = None
        self.target_coord = copy(self.pos)
        self.sense = SenseSprite(self.game, self, SENSE_RADIUS)
        self.movement_range = pg.Rect(0, 0, self.game.map.tilewidth, self.game.map.tileheight)
        #self.target = vect(np.random.randint(WIDTH // TILESIZE), np.random.randint(HEIGHT // TILESIZE))
        self.void = False
        self.attack_style = np.random.randint(2)
        self.gear = Gear(game, self)
        self.skills = {}
        for skill_name in SKILL_NAMES:
            self.skills[skill_name] = Skill(skill_name)
        self.prayer_bonus = {}
        for pray_bonus in PRAYER_BONUS_TYPES:
            self.prayer_bonus[pray_bonus] = 0

        self.hp_regen_ticks = 0
        
        self.projectiles = pg.sprite.Group()


        self.hitsplats = []
        self.hpbar = None
        # how do we do this?
        self.attack_delay = 0
        self.last_tick = 0
        
    def kill(self):
        self.sense.kill()
        super().kill()
        
    def set_movement_range(self, dist_from_spawn):
        # careful here with the move range - handle the higher limits if they go over the map size
        moverng_left = max(self.respawn_pos.x - dist_from_spawn, 0)
        moverng_top = max(self.respawn_pos.y - dist_from_spawn, 0)
        moverng_width = min(dist_from_spawn*2+1, self.game.map.tilewidth - moverng_left)
        moverng_height = min(dist_from_spawn*2+1, self.game.map.tileheight - moverng_top)
        self.movement_range = pg.Rect(moverng_left, moverng_top,
                                                moverng_width, moverng_height)

    def strategy_attack_style(self, strategy):
        if strategy == 0:
            # random
            self.attack_style = np.random.randint(4)
        if strategy == 1:
            rnd = np.random.random()
            if rnd < 0.5:
                self.attack_style = 1 # aggressive
            else:
                self.attack_style = choice([0,2,3])

    def eff_str_lvl(self):
        val = np.floor(self.skills['Strength'].level_current * (1 + self.prayer_bonus['strength']))
        if self.attack_style == 1: #aggressive
            val += 3
        elif self.attack_style == 3: # controlled
            val += 1
        val += 8
        if self.void:
            val = np.floor(val * 1.1)
        return val

    def eff_atk_lvl(self):
        val = np.floor(self.skills['Attack'].level_current * (1 + self.prayer_bonus['attack']))
        if self.attack_style == 0: # accurate
            val += 3
        elif self.attack_style == 3: # controlled
            val += 1
        val += 8
        if self.void:
            val = np.floor(val * 1.1)
        return val

    def eff_def_lvl(self):
        val = np.floor(self.skills['Defence'].level_current * (1 + self.prayer_bonus['defence']))
        if self.attack_style == 2: # defensive
            val += 3
        elif self.attack_style == 3: # controlled
            val += 1
        return val
    
    def melee_atk_roll(self):
        # get damage type from attack style and weapon?
        dmg_type = self.gear.items['weapon'].dmg_type
        val = self.eff_atk_lvl() * (self.gear.total_bonuses.attack[dmg_type] + 64)
        # void and stuff ...
        return val

    def melee_def_roll(self, dmg_type):
        #return (self.skills['Defence'].level_current + 9) * (self.total_bonuses[dmg_type] + 64)
        return self.eff_def_lvl() * (self.gear.total_bonuses.defence[dmg_type] + 64)

    def melee_hit_chance(self, target):
        atk_roll = self.melee_atk_roll()
        def_roll = target.melee_def_roll('slash')
        if atk_roll > def_roll:
            return 1 - (def_roll + 2) / (2 * atk_roll + 1)
        else:
            return atk_roll / (2 * def_roll + 1)

    # RANGED
    def ranged_atk_roll(self):
        return np.floor(self.eff_ranged_atk() * (self.gear.total_bonuses.attack['ranged'] + 64))

    def ranged_def_roll(self):
        return (self.skills['Defence'].level_current + 9) * (self.gear.total_bonuses.defence['ranged'] + 64)

    def eff_ranged_str(self):
        val = np.floor(self.skills['Ranged'].level_current * (1 + self.prayer_bonus['ranged']))
        if self.attack_style == 0: #accurate
            val += 3
        val += 8
        if self.void:
            val = np.floor(val * 1.1)
        return val

    def eff_ranged_atk(self):
        # slight difference needs to be accounted for rigour prayer
        return self.eff_ranged_str()

    def ranged_hit_chance(self, target):
        atk_roll = self.ranged_atk_roll()
        def_roll = target.ranged_def_roll()
        if atk_roll > def_roll:
            return 1 - (def_roll + 2) / (2 * atk_roll + 1)
        else:
            return atk_roll / (2 * def_roll + 1)

    def max_hit(self):
        dmg_type = self.gear.items['weapon'].dmg_type
        if dmg_type == 'ranged':
            eff_lvl = self.eff_ranged_atk()
            gear_bonus = self.gear.total_bonuses.other['ranged_str']
        else: # melee
            eff_lvl = self.eff_str_lvl()
            gear_bonus = self.gear.total_bonuses.other['melee_str']
            
        val = eff_lvl * (gear_bonus + 64)
        val = np.floor((val + 320) / 640)
        if self.void:
            val = np.floor(val * 1.1)
        return val
            
    def hit_chance(self, target):
        dmg_type = self.gear.items['weapon'].dmg_type
        if dmg_type == 'ranged':
            atk_roll = self.ranged_atk_roll()
            def_roll = target.ranged_def_roll()
        elif dmg_type == 'magic':
            # TODO ?
            atk_roll = 100
            def_roll = 100
        else: # melee
            atk_roll = self.melee_atk_roll()
            def_roll = target.melee_def_roll(dmg_type)
        
        if atk_roll > def_roll:
            return 1 - (def_roll + 2) / (2 * atk_roll + 1)
        else:
            return atk_roll / (2 * def_roll + 1)
        
    def dps(self, target):
        return (self.hit_chance(target) * self.max_hit()) * 0.5 / self.gear.items['weapon'].attack_delay
        
    def attack_if_ready(self, target):
        if self.target_entity != None:
            if self.attack_delay <= 0:
                if (self.pos - self.target_entity.pos).length() <= self.gear.items['weapon'].weapon_range:
                    if self.gear.items['weapon'].dmg_type == 'ranged':
                        self.fire(target)
                    else:
                        self.swing(target)
                    self.attack_delay = self.gear.items['weapon'].attack_delay
            
    def fire(self, target):
        # snapshot self at time of firing with copy()
        self.projectiles.add(Projectile(self.game, copy(self), target))
        
    def swing(self, target):
        self.hit(target)
            
    # returns None if missed, dmg if hit (zero is possible)
    def hit(self, target):
        # to prevent two players from getting loot/kill
        if target.skills['Hitpoints'].level_current <= 0:
            # this should return something (maybe None) to signify that we didn't swing! no timer reset
            return None
        if np.random.uniform() < self.hit_chance(target):
            dmg = np.random.randint(0, self.max_hit()+1)
            #print("{} hit {} for {} dmg".format(self.name, target.name, dmg))
            target.skills['Hitpoints'].level_current -= dmg

            # gain xp
            if ((isinstance(self, Player) or isinstance(self, Spectator)) and dmg > 0):
                self.gain_xp('Hitpoints', dmg*1.333 * XP_MULTIPLIER)
                
                if self.gear.items['weapon'].dmg_type == 'ranged':
                    self.gain_xp('Ranged', dmg*4 * XP_MULTIPLIER)
                else: # melee?
                    if self.attack_style == 0: #accurate
                        self.gain_xp('Attack', dmg*4 * XP_MULTIPLIER)
                    elif self.attack_style == 1: # aggressive
                        self.gain_xp('Strength', dmg*4 * XP_MULTIPLIER)
                    elif self.attack_style == 2: # defensive
                        self.gain_xp('Defence', dmg*4 * XP_MULTIPLIER)
                    elif self.attack_style == 3: # controlled
                        self.gain_xp('Attack', dmg*1.333 * XP_MULTIPLIER)
                        self.gain_xp('Strength', dmg*1.333 * XP_MULTIPLIER)
                        self.gain_xp('Defence', dmg*1.333 * XP_MULTIPLIER)
            
            # display hits and HP bars
            Hitsplat(self.game, dmg, target)
            HpBarPopup(self.game, target)

            # HANDLE LOOT DIFFERENTLY!!!
            if target.skills['Hitpoints'].level_current <= 0:
                if isinstance(self, Player):
                    loot = target.get_drops()
                    for item in loot:
                        # returns True if item was added
                        if (self.inventory.add(item)):
                            if item.equipable:
                                if item.equip_class == 'weapon':
                                    if ((self.gear.items['weapon'].name == 'Fists') or (item.bonuses.other['melee_str'] > self.gear.items['weapon'].bonuses.other['melee_str'])):
                                        print('{} got better weapon: {}'.format(self.name, item.name))
                                        self.equip(item)
                                    elif (any([item.name == owned_item.name for owned_item in self.inventory.items])):
                                        #print('\n{} already has item: {} - dropping\n'.format(self.name, item.name))
                                        self.inventory.items.remove(item)
                                else:
                                    if ((self.gear.items[item.equip_class] == None) or (item.bonuses.defence['slash'] > self.gear.items[item.equip_class].bonuses.defence['slash'])):
                                        print('{} got better armor: {}'.format(self.name, item.name))
                                        self.equip(item)
                                    elif (any([item.name == owned_item.name for owned_item in self.inventory.items])):
                                        #print('\n{} already has item: {} - dropping\n'.format(self.name, item.name))
                                        self.inventory.items.remove(item)
            """
            if target.skills['Hitpoints'].level_current <= 0:
                loot = target.get_drops()
                if isinstance(self, Player):
                    if loot:
                        for item in loot:
                            if isinstance(item, Equipment):
                                if item.equip_class == 'weapon':
                                    if item.name == 'Trident':
                                        print("omg got trident as drop!!")
                                    # better if check for dps increase
                                    if item.bonuses.other['melee_str'] > self.gear.items['weapon'].bonuses.other['melee_str']:
                                        self.equip(item)
                                elif item.equip_class == 'amulet':
                                    self.equip(item)
                            if isinstance(item, GoldPieces):
                                self.gp += item
            """
            return dmg
        else:
            Hitsplat(self.game, 0, target)
            HpBarPopup(self.game, target)
            return None

    def get_drops(self):
        return []

    def get_combat_lvl(self):
        base = 0.25 * (self.skills["Defence"].level + self.skills["Hitpoints"].level +
                                        np.floor(0.5*self.skills["Prayer"].level))
        melee = 13/40 * (self.skills["Attack"].level + self.skills["Strength"].level)
        ranged = 13/40 * np.floor(self.skills["Ranged"].level * 1.5)
        mage = 13/40 * np.floor(self.skills["Magic"].level * 1.5)
        return np.floor(base + max(melee, ranged, mage))
    
    def get_hp(self):
        return self.skills['Hitpoints'].level_current

    def __repr__(self):
        return "{} ({}): hp {}/{} atk {} str {} def {} magic {} ranged {}".format(self.name, int(self.get_combat_lvl()),
                                                                                                         self.skills['Hitpoints'].level_current,
                                                                                                         self.skills['Hitpoints'].level,
                                                                                                         self.skills["Attack"].level,
                                                                                                         self.skills["Strength"].level,
                                                                                                         self.skills["Defence"].level,
                                                                                                         self.skills["Magic"].level,
                                                                                                         self.skills["Ranged"].level)
        
    def get_combat_stats(self):
        return "atk {} str {} def {} magic {} ranged {}".format(self.skills["Attack"].level,
                                                                                                         self.skills["Strength"].level,
                                                                                                         self.skills["Defence"].level,
                                                                                                         self.skills["Magic"].level,
                                                                                                         self.skills["Ranged"].level)
        

    def update(self):
        # animate movement
        if self.vel.length() != 0:
            dist = (pg.time.get_ticks() - self.last_tick) / TICK_LENGTH
            self.rect.center = grid2screen_coord(self.prev_pos + dist * self.vel)
            
            #dist = (pg.time.get_ticks() - self.last_tick)/TICK_LENGTH
            #print(dist)
            #self.rect.move_ip(grid2screen_coord(dist * self.vel))
        else:
            pass
            self.rect.center = grid2screen_coord(self.pos)
        
    def tick_update(self):
        self.last_tick = pg.time.get_ticks()
        # SELECT DIFFERENT PUNISHMENT FOR PLAYERS FOR DYING? (like xp loss)
        if self.skills['Hitpoints'].level_current <= 0:
            if isinstance(self, Mob):
                self.kill()
                return
            
            # TODO - handle this differently
            # DIED, DEAD, DEATH
            elif isinstance(self, Player):
                self.skills['Hitpoints'].level_current = self.skills['Hitpoints'].level
                # buy respawn for 1000 gold pieces
                #if self.gp.amount >= 1000:
                #    self.gp.amount -= 1000
                #    print("{} bought an avoid death for 1000 gp".format(self.name))
                #    return
                self.pos = self.respawn_pos
                self.vel = vect(0, 0)
                self.gear.on_death()
                self.inventory.on_death()
                self.update_image()
                # Mario is cheating!
                if self.name == 'Mario' or self.name == 'John':
                    self.equip(self.game.item_list['shortbow'])
                    self.equip(self.game.item_list['iron_arrows'])
                
        # HP REGENERATION
        if self.hp_regen_ticks >= HP_REGEN_TICKDELAY:
            self.hp_regen_ticks = 0
            if self.skills['Hitpoints'].level_current < self.skills['Hitpoints'].level:
                self.skills['Hitpoints'].level_current += 1
        else:
            self.hp_regen_ticks += 1
            
        # ATTACK DELAY COUNTER
        # Maybe add exception for when eating (to add penalty to eating)
        if self.attack_delay > 0:
            self.attack_delay -= 1
            
        # MOVEMENT
        if self.vel.length() != 0:
            self.prev_pos = self.pos
            new_pos = self.pos + self.vel
            if not ((new_pos.x < self.movement_range.left) or (new_pos.x >= self.movement_range.right)
                  or (new_pos.y < self.movement_range.top) or (new_pos.y >= self.movement_range.bottom)):
                self.pos = new_pos
                # REQUIRED IF WE DIDN'T USE self.update() for continuous movement
                #self.rect.center = grid2screen_coord(self.pos)
            else:
                self.vel = vect(0,0)
                
    def move_away(self, target, distance=3):
        direction = self.pos - target
        if direction.length() >= distance:
            self.vel = vect(0, 0)
        else:
            angles = [abs(vector.angle_to(direction)) for vector in DIRECTIONS]
            best_direction = sorted(((value, index) for index, value in enumerate(angles)))[0]
            self.vel = copy(DIRECTIONS[best_direction[1]])

    def move_toward(self, target, distance=0):
        direction = target - self.pos
        if direction.length() <= distance:
            self.vel = vect(0, 0)
        else:
            angles = [abs(vector.angle_to(direction)) for vector in DIRECTIONS]
            best_direction = sorted(((value, index) for index, value in enumerate(angles)))[0]
            self.vel = copy(DIRECTIONS[best_direction[1]])

    def gain_xp(self, skill, amount):
        lvls = self.skills[skill].gain_xp(amount * XP_MULTIPLIER)
        #if any([(not n%19) for n in lvls]):
            #print("{} gained lvl {} {}".format(self.name, lvls[-1], skill))

    def equip(self, item):
        # print difference from previous gear? __add__ is implemented for Equipment
        # show increase over old equipment when equiping?
        #for [bonus in 
        self.gear.equip(item)
        #print("{} equipped {} (max hit: {})".format(self.name, item.name, self.max_hit()))
        self.update_image()


    #pos =  pos_center[0] - img.get_width()/2, pos_center[1] - img.get_height()/2
    #self.image.blit(img, pos)

    def update_image(self):
        # loop through all equip
        #print("{} is wearing: {} (updating image)".format(self.name, ', '.join([item[1].name for item in self.gear.items.items() if item[1].name!='Empty'])))
        self.image = copy(self.naked_image)
        for _, item in self.gear.items.items():
            #if item.name != 'Empty' and item.name != 'Fists':
            if item != None:
                if item.name != 'Fists':
                    pos = IMG_EQUIP_POS[item.equip_class]
                    img = self.game.item_images[item.name.lower().replace(' ', '_')]
                    pos_center = IMG_EQUIP_POS[item.equip_class]
                    pos = pos_center[0] - img.get_width()/2, pos_center[1] - img.get_height()/2
                    self.image.blit(img, pos)

        
class Spectator(Entity):
    def __init__(self, game, x, y, name='Spectator'):
        super().__init__(game, [], x, y)
        self.name = name
        self.naked_image = copy(game.player_img)
        self.image = copy(self.naked_image)
        #self.mask = pg.mask.from_surface(self.image)
        
        self.rect = self.image.get_rect()

    def get_keys(self):
        self.rot_speed = 0
        self.vel = vect(0, 0)
        keys = pg.key.get_pressed()
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            self.vel.x = -1
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            self.vel.x = 1
        if keys[pg.K_UP] or keys[pg.K_w]:
            self.vel.y = -1
        if keys[pg.K_DOWN] or keys[pg.K_s]:
            self.vel.y = 1

    def tick_update(self):
        self.get_keys()
        #self.swing(self)
        super().tick_update()
        
        #hits = pg.sprite.spritecollide(self.sense, self.game.entities, False, collide_sense)
        # targeting and stuff?

class Player(Entity):
    def __init__(self, game, x, y, name="Player"):
        super().__init__(game, game.players, x, y)
        self.name = name
        
        self.sense.set_radius(10)
        
        self.naked_image = copy(game.player_img)
        draw_text(self.naked_image, self.name, (30,10), (111,111,111))
        self.image = copy(self.naked_image)
        self.rect = self.image.get_rect()

        self.yolo_factor = 1.3

        # lvl 10 hp
        self.skills['Hitpoints'].gain_xp(1200)
        
        self.notarget_ticks = 0
        
        self.history = {}
        self.history['Attack'] = []
        self.history['Strength'] = []
        self.history['Defence'] = []
        self.history['Ranged'] = []
        self.history['Combat'] = []
        
        self.inventory = Inventory(self)


        
    def generate_skill_hist_pic(self, skill_name):
        fig, ax = plt.subplots()
        ax.plot(self.history[skill_name], label=self.name)
        ax.legend()
        ax.set_ylabel('{} xp'.format(skill_name))
        ax.set_xlabel('time / $\it{ticks}$')
        fig.savefig(os.path.join(pic_folder, "{}_{}_graph.png".format(self.name, skill_name)))


    def tick_update(self):
        self.history['Attack'].append(self.skills['Attack'].xp)
        self.history['Strength'].append(self.skills['Strength'].xp)
        self.history['Defence'].append(self.skills['Defence'].xp)
        self.history['Ranged'].append(self.skills['Ranged'].xp)
        self.history['Combat'].append(self.get_combat_lvl())
        # SENSE ENTITIES
        # TODO - at least get this logic into some functions (same with Mob's logic)
        hits = pg.sprite.spritecollide(self.sense, self.game.entities, False, collide_sense)

        def sortFun(e):
            return e.get_combat_lvl()
        
        hits.sort(reverse=True, key=sortFun)

        #print('{}'.join([hit.name for hit in hits]))
        
        if len(hits) > 0:
                self.target_entity = hits[0]
            
        # FIND NEW TARGET
        if self.target_entity == None:
            if any(isinstance(entity, Mob) for entity in hits):
                potential_targets = [e for e in hits if isinstance(e, Mob)]
                potential_targets = [e for e in potential_targets if self.movement_range.collidepoint(e.pos)]
                if len(potential_targets) > 0:
                    self.target_entity = potential_targets[np.random.randint(len(potential_targets))]
                    #print("{}: found new target in {}".format(self.name, self.target_entity.name))
        # if target entity wandered out of sense range
        elif self.target_entity not in hits:
            #print("{}: Target ({}) out of sight".format(self.name, self.target_entity.name))
            self.target_entity = None
                
        # target out of movement range, abandon
        elif not self.movement_range.collidepoint(self.target_entity.pos):
            #print("{}: Target ({}) out of movement range".format(self.name, self.target_entity.name))
            #self.vel = vect(0,0)
            self.target_entity = None


        if self.target_entity == None:
            if self.notarget_ticks >= MOB_WANDER_TICKDELAY:
            # if no target set random target square in self.movement_range?
                x = np.random.randint(self.movement_range.left, self.movement_range.right)
                y = np.random.randint(self.movement_range.top, self.movement_range.bottom)
                self.target_coord = vect(x, y)
                self.notarget_ticks = 0
            else:
                self.notarget_ticks += 1

            
            self.move_toward(self.target_coord)
        
        # MOVE TOWARDS THE TARGET ENTITY
        else:
            if (hits[0].dps(self) * self.get_hp()) > self.yolo_factor * (self.dps(hits[0]) * hits[0].get_hp()):
                self.move_away(hits[0].pos, 10)
            else:
                self.move_toward(self.target_entity.pos, self.gear.items['weapon'].weapon_range)
            
        # aggressive type of strategy
        self.strategy_attack_style(1)
        
        self.attack_if_ready(self.target_entity)

                    
        super().tick_update()
        

class Mob(Entity):
    def __init__(self, game, x, y, mob_class):
        super().__init__(game, game.mobs, x, y)
        init_dict = self.game.mob_json_list[mob_class.lower().replace(' ', '_')]
        for key, item in init_dict.items():
            if key == 'name':
                self.name = item
                self.naked_image = copy(game.mob_images[self.name.lower().replace(' ', '_')])
                draw_text(self.naked_image, self.name, (0,0), (111,111,111))
                self.image = copy(self.naked_image)
            elif key == 'init_xp':
                for skill, amount in item.items():
                    # use Skill (rather than Entity) method cause it doesn't print lvl-ups
                    self.skills[skill].gain_xp(amount)
            elif key == 'equipment':
                for equip_class, item_name in item.items():
                    self.equip(self.game.item_list[item_name])
                    #print(item_name)
                    #print("{} equipped {}".format(self.name, item_name))
                    #print(EQUIPLIST[item_name])
            elif key == 'drops':
                self.drops = { self.game.item_list[item_name]: chance for item_name, chance in item.items() }
            elif key == 'sense_range':
                self.sense.set_radius(item)
            elif key == 'movement_range':
                self.set_movement_range(item)
            
            #elif key == 'drop_table':


        self.rect = self.image.get_rect()
        self.notarget_ticks = 0

    def tick_update(self):
        # SENSE ENTITIES
        hits = pg.sprite.spritecollide(self.sense, self.game.entities, False, collide_sense)

        # FIND NEW TARGET
        if self.target_entity == None:
            if any(isinstance(entity, Player) for entity in hits):
                potential_targets = [e for e in hits if isinstance(e, Player)]
                potential_targets = [e for e in potential_targets if self.movement_range.collidepoint(e.pos)]
                if len(potential_targets) > 0:
                    self.target_entity = potential_targets[np.random.randint(len(potential_targets))]
                    #print("{}: found new target in {}".format(self.name, self.target_entity.name))
        elif self.target_entity not in hits:
            #print("{}: Target ({}) out of sight".format(self.name, self.target_entity.name))
            self.target_entity = None
                
        # target out of movement range, abandon
        elif not self.movement_range.collidepoint(self.target_entity.pos):
            #print("{}: Target ({}) out of movement range".format(self.name, self.target_entity.name))
            #self.vel = vect(0,0)
            self.target_entity = None


        if self.target_entity == None:
            if self.notarget_ticks >= MOB_WANDER_TICKDELAY:
            # if no target set random target square in self.movement_range?
                x = np.random.randint(self.movement_range.left, self.movement_range.right)
                y = np.random.randint(self.movement_range.top, self.movement_range.bottom)
                self.target_coord = vect(x, y)
                self.notarget_ticks = 0
            else:
                self.notarget_ticks += 1

            
            self.move_toward(self.target_coord)
        
        # MOVE TOWARDS THE TARGET ENTITY
        else:
            self.move_toward(self.target_entity.pos, self.gear.items['weapon'].weapon_range)
            
        self.attack_if_ready(self.target_entity)


        super().tick_update()

    def get_drops(self):
        rnd = np.random.random()
        drops = []
        x = 0
        for item, chance in self.drops.items():
            x += chance
            #print(x, item.name, chance)
            if x >= 1:
                if x > 1:
                    print('sum of drop chance is higher than 100%!')
                break
            if rnd < x:
                drops.append(copy(item))
                break
        #if drops:
        #    print('{} dropped {}'.format(self.name, [item.name for item in drops]))
        return drops
        
            
class Projectile(pg.sprite.Sprite):
    def __init__(self, game, shooter_snapshot, target):
        self.groups = game.all_sprites, game.projectiles
        super().__init__(self.groups)
        #self.image = pg.Surface((TILESIZE, TILESIZE))
        #self.image.fill(WHITE)
        
        # pointing right
        self.rot = -100
        self.game = game
        self.naked_image = self.game.item_images[shooter_snapshot.gear.items['ammunition'].name.lower().replace(' ', '_')]
        
        self.image = pg.transform.rotate(self.naked_image, self.rot)
        # TODO - figure out how not to have to set_colorkey every time we rotate?
        transColor = self.image.get_at((0,0))
        self.image.set_colorkey(transColor)
        
        self.rect = self.image.get_rect()
        self.pos = copy(shooter_snapshot.pos)
        self.vel = vect(0, 0)
        self.shooter_snapshot = shooter_snapshot
        self.target = target
        self.rect.center = grid2screen_coord(self.pos)
        self.last_tick = 0
        
    def tick_update(self):
        self.last_tick = pg.time.get_ticks()
        # kill self if target dies
        if self.target.skills['Hitpoints'].level_current < 1:
            self.kill()
            return
        # hit target and kill self when we reach target
        # TODO - why length < 2? something is off?
        if np.abs((self.target.pos - self.pos).length()) < 1:
            self.shooter_snapshot.hit(self.target)
            self.vel = vect(0,0)
            #print('proj pos: {}    target pos: {}'.format(self.pos, self.target.pos))
            self.kill()
            return
        else:
            self.vel = (self.target.pos - self.pos).normalize() * PROJECTILE_SPEED
            rot = self.vel.angle_to(vect(0,-1)) - 2
            if rot != self.rot:
                self.rot = rot
                self.image = pg.transform.rotate(self.naked_image, self.rot)
                # TODO - figure out how not to have to set_colorkey every time we rotate?
                transColor = self.image.get_at((0,0))
                self.image.set_colorkey(transColor)
                self.rect = self.image.get_rect()
                
        self.rect.center = grid2screen_coord(self.pos)
        self.prev_pos = self.pos
        self.pos += self.vel
    
    def update(self):
        # animate movement
        if self.vel.length() != 0:
            dist = (pg.time.get_ticks() - self.last_tick) / TICK_LENGTH
            self.rect.center = grid2screen_coord(self.prev_pos + dist * self.vel)
            
            #dist = (pg.time.get_ticks() - self.last_tick)/TICK_LENGTH
            #print(dist)
            #self.rect.move_ip(grid2screen_coord(dist * self.vel))


class Wall(pg.sprite.Sprite):
    def __init__(self, game, x, y):
        self.groups = game.all_sprites, game.walls
        super().__init__(self.groups)
        self.image = pg.Surface((TILESIZE, TILESIZE))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.pos = vect(x, y)
        self.rect.center = grid2screen_coord(self.pos)

    def tick_update(self):
        pass

class SenseSprite(pg.sprite.Sprite):
    def __init__(self, game, entity, radius):
        self.groups = game.all_sprites
        super().__init__(self.groups)
        self.entity = entity
        self.pos = self.entity.pos
        self.set_radius(radius)
        

    def set_radius(self, radius):
        self.radius = radius
        self.image = pg.Surface((self.radius*2*TILESIZE, self.radius*2*TILESIZE), pg.SRCALPHA)
        transColor = self.image.get_at((1,1))
        self.image.set_colorkey(transColor)
        draw_circle_alpha(self.image, (*SENSE_COLOR, SENSE_OPACITY), (self.radius*TILESIZE,self.radius*TILESIZE), self.radius*TILESIZE)
        self.rect = self.image.get_rect()
        self.rect.center = grid2screen_coord(self.entity.pos)


    def update(self):
        self.rect.center = self.entity.rect.center

    def tick_update(self):
        self.pos = self.entity.pos
        self.rect.center = grid2screen_coord(self.entity.pos)
        
class Hitsplat(pg.sprite.Sprite):
    def __init__(self, game, damage, entity):
        self.groups = game.all_sprites
        super().__init__(self.groups)
        self.damage = damage
        self.entity = entity
        
        if len(self.entity.hitsplats) == 0:
            # just append
            self.entity.hitsplats.append(self)
        elif len(self.entity.hitsplats) == MAX_HITSPLATS:
            # roll and replace first element
            self.entity.hitsplats = shift(self.entity.hitsplats, -1)
            self.entity.hitsplats[0] = self
        else:
            # append and roll so the new element is first?
            self.entity.hitsplats.append(self)
            self.entity.hitsplats = shift(self.entity.hitsplats, -1)
            
        if damage == 0:
            self.naked_image = game.blue_hitsplat_img
        else:
            self.naked_image = game.red_hitsplat_img
        self.image = copy(self.naked_image)
        self.image.set_alpha(140)

        #self.image = pg.Surface((HPBAR_WIDTH, HPBAR_HEIGHT), pg.SRCALPHA)
        #self.rect = self.image.get_rect()
        
        self.y_offset = 0
        textsurface = arial18Font.render(str(damage), True, BLACK)
        self.image.blit(textsurface, vect(self.image.get_size())/2 - vect(textsurface.get_size())/2)
        self.rect = self.image.get_rect()
        self.rect.center = grid2screen_coord(entity.pos)# + vect(0, self.y_offset)
        self.ticks_left = HITSPLAT_TICKDURATION

    def tick_update(self):
        
        self.ticks_left -= 1
        if self.ticks_left <= 0:
            if self in self.entity.hitsplats:
                self.entity.hitsplats.remove(self)
            self.kill()
            
        # update position of old hitsplats:
        for idx, splat in enumerate(self.entity.hitsplats):
            splat.y_offset = idx * self.image.get_height()
            
    def update(self):
        self.rect.center = (self.entity.rect.centerx, self.entity.rect.centery + self.y_offset)

class HpBar(pg.sprite.Sprite):
    def __init__(self, game, entity, pos=None):
        if isinstance(self, HpBarPopup):
            self.groups = game.all_sprites
        else:
            self.groups = game.all_sprites, game.gui_sprites
        super().__init__(self.groups)
        
        self.entity = entity
        self.game = game
        self.pos = pos
        
        self.naked_image = pg.Surface((HPBAR_WIDTH, HPBAR_HEIGHT), pg.SRCALPHA)
        self.naked_image.fill(HPBAR_COLOR)
        self.naked_image.set_alpha(HPBAR_OPACITY)
        self.image = copy(self.naked_image)
        self.rect = self.image.get_rect()
        if self.pos != None:
            self.rect.center = self.pos
        
        self.update_image()


    def update_image(self):
        w, h = self.rect.size
        self.dmg_value = self.entity.skills['Hitpoints'].level_current / self.entity.skills['Hitpoints'].level
        self.image = copy(self.naked_image)
        pg.draw.rect(self.image, (*HPBAR_DMGCOLOR, HPBAR_OPACITY),
                         (np.floor(w*self.dmg_value), 0, np.ceil((1-self.dmg_value)*w), h))
        
    def tick_update(self):
        self.update_image()
            
    #def update(self):
        
class HpBarPopup(HpBar):
    def __init__(self, game, entity):
        # if entity already has an hpBar, only reset timeout counter
        if entity.hpbar != None:
            entity.hpbar.ticks_left = HPBAR_TICKDURATION
            return

        super().__init__(game, entity, None)
        
        self.ticks_left = HPBAR_TICKDURATION

        self.entity.hpbar = self
        
    def tick_update(self):
        self.update_image()
        self.ticks_left -= 1
        if self.ticks_left <= 0:
            self.entity.hpbar = None
            self.kill()
            
    def update(self):
        self.rect.center = (self.entity.rect.centerx, self.entity.rect.centery + HPBAR_VERT_OFFSET)
        
        
class MobSpawner(pg.sprite.Sprite):
    def __init__(self, game, mob_class, x, y):
        self.game = game
        self.groups = game.all_sprites, game.spawners
        super().__init__(self.groups)
        self.idx = 0
        self.pos = vect(x, y)
        self.mob_class = mob_class
        self.image = pg.Surface((20,20))
        pg.draw.circle(self.image, WHITE, (10,10), 6)
        if mob_class == 'Boss':
            pg.draw.circle(self.image, RED, (10,10), 6)
        elif mob_class == 'Green Dragon':
            pg.draw.circle(self.image, GREEN, (10,10), 6)
        self.rect = self.image.get_rect()
        self.rect.center = grid2screen_coord(self.pos)

        self.game.map.tilewidth, self.game.map.tileheight
        self.mobs = pg.sprite.Group()
        self.respawn_delay = RESPAWN_DELAY_MOB
        self.respawn_count = self.respawn_delay

    def tick_update(self):
        if len(self.mobs) == 0:
            if self.respawn_count == 0:
                mob = Mob(self.game, *self.pos, self.mob_class)
                
                self.idx += 1
                self.mobs.add(mob)
                self.respawn_count = self.respawn_delay
            else:
                self.respawn_count -= 1

ENTITYINFO_NAME_POS = (5,5)
ENTITYINFO_CMBSTATS_POS = (5,17)

    
def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+1)
        n -= 1
    return start

class TextBox(pg.sprite.Sprite):
    def __init__(self, game, text, pos, boxsize, fontsize=10, textcolor=BLACK, backgroundcolor=None):
        self.groups = game.all_sprites, game.gui_sprites
        super().__init__(self.groups)
        
        self.width = boxsize[0]
        self.height = boxsize[1]
        
        self.rect = pg.Rect(pos, (self.width, self.height))
        self.image = pg.Surface(self.rect.size, pg.SRCALPHA)
        if backgroundcolor != None:
            self.image.fill((*backgroundcolor,111))
        
        start_idx = 0
        lines = []
        
        for idx in range(1, text.count(' ')):
            textsurface = pg.font.SysFont('Arial', fontsize).render(text[start_idx:find_nth(text, ' ', idx)], True, textcolor)
            if textsurface.get_width() > self.width:
                end_pos = find_nth(text, ' ', idx-1)
                
                lines.append(text[start_idx:end_pos])
                
                start_idx = end_pos+1
            # handle last row
            elif idx == text.count(' ')-1:
                lines.append(text[start_idx:])
                
        # print
        row = 0
        for line in lines:
            if backgroundcolor == None:
                textsurface = pg.font.SysFont('Arial', fontsize).render(line, True, textcolor)
            else:
                textsurface = pg.font.SysFont('Arial', fontsize).render(line, True, textcolor, backgroundcolor)
            self.image.blit(textsurface, (0, row * (fontsize + 2)))
            row += 1
                
        
        
    def tick_update(self):
        pass
        
    def update(self):
        pass
    
class Button(pg.sprite.Sprite):
    def __init__(self, game, pos, size, caption, function):
        self.groups = game.all_sprites, game.gui_sprites, game.button_sprites
        super().__init__(self.groups)
        self.function = function
        
        self.width = size[0]
        self.height = size[1]
        
        self.caption = caption
        
        self.rect = pg.Rect(pos, (self.width, self.height))
        self.image = pg.Surface(self.rect.size, pg.SRCALPHA)
        self.image.fill((0,0,0,255))
        pg.draw.rect(self.image, (200,200,200), pg.Rect(1, 1, self.width-2, self.height-2))
        

        textsurface = arial10Font.render(self.caption, True, BLACK)
        self.image.blit(textsurface, (self.width/2 - textsurface.get_width()/2, self.height/2 - textsurface.get_height()/2))
        
    def tick_update(self):
        pass
        
    def execute(self):
        self.function()
        
class Window(pg.sprite.Sprite):
    def __init__(self, game, pos, size=(140,300)):
        self.groups = game.all_sprites, game.gui_sprites
        super().__init__(self.groups)
        self.game = game
    
        self.pos = pos
        self.width = size[0]
        self.height = size[1]
        
        self.rect = pg.Rect(pos, (self.width, self.height))
        self.naked_image = pg.Surface(self.rect.size, pg.SRCALPHA)
        self.naked_image.fill((73,73,73,211))
        
        self.image = copy(self.naked_image)
        
        self.sprites = pg.sprite.Group()
        
        self.list = []
        # 1 pixel off top and right
        btn_pos = self.pos + vect(self.width-BTN_X_SIZE[0]-1,1)
        btn_close = Button(self.game, btn_pos, BTN_X_SIZE, "X", self.kill)
        self.sprites.add(btn_close)
        
    def tick_update(self):
        # update all? maybe not, it can only update on clicks..
        pass
        
    def kill(self):
        for sprite in self.sprites:
            sprite.kill()
        
        super().kill()
        
class PictureFrame(Window):
    def __init__(self, game, pos, image):
        size = (image.get_width(), image.get_height())
        super().__init__(game, pos, size)
        self.game = game

        self.image = image
        
class HighScores(Window):
    def __init__(self, game, pos):
        super().__init__(game, pos, HIGHSCORES_SIZE)
        self.game = game
        BTN_SIZE = (52,30)
        
        self.list = []
        offset = vect(1,1)
        btn_combat = Button(self.game, self.pos + offset, BTN_SIZE, "Combat", self.sort_by_combat)
        btn_attack = Button(self.game, self.pos + offset + vect(2 + BTN_SIZE[0], 0), BTN_SIZE, "Attack", self.sort_by_attack)
        btn_strength = Button(self.game, self.pos + offset + 2*vect(2 + BTN_SIZE[0], 0), BTN_SIZE, "Strength", self.sort_by_strength)
        btn_defence = Button(self.game, self.pos + offset + 3*vect(2 + BTN_SIZE[0], 0), BTN_SIZE, "Defence", self.sort_by_defence)
        btn_ranged = Button(self.game, self.pos + offset + 4*vect(2 + BTN_SIZE[0], 0), BTN_SIZE, "Ranged", self.sort_by_ranged)
        
        self.sprites.add(btn_combat)
        self.sprites.add(btn_attack)
        self.sprites.add(btn_strength)
        self.sprites.add(btn_defence)
        self.sprites.add(btn_ranged)
        
        
        
    def generate_skill_hist_pic(self, skill_name):
        self.list = sorted(self.game.players, key=lambda players: players.get_combat_lvl(), reverse=True)
        fig, ax = plt.subplots()
        for player in self.list:
            ax.plot(player.history[skill_name], label=player.name)
        ax.legend()
        if skill_name == 'Combat':
            ax.set_ylabel('{} level'.format(skill_name))
        else:
            ax.set_ylabel('{} xp'.format(skill_name))
        ax.set_xlabel('time / $\it{ticks}$')
        fig.savefig(os.path.join(pic_folder, "players_{}_graph.png".format(skill_name)))


    def show_skill_hist(self, skill_name):
        self.generate_skill_hist_pic(skill_name)
        if self.game.hist_window != None:
            self.game.hist_window.kill()
        img = pg.image.load(os.path.join(pic_folder, 'players_{}_graph.png'.format(skill_name)))
        self.game.hist_window = PictureFrame(self.game, (300,80), img)
        
    def sort_by_combat(self):
        self.list = None
        self.list = sorted(self.game.players, key=lambda players: players.get_combat_lvl(), reverse=True)
        self.update_image()
        self.generate_skill_hist_pic("Combat")
        self.show_skill_hist("Combat")
        
    def sort_by_attack(self):
        self.list = None
        self.list = sorted(self.game.players, key=lambda players: players.skills['Attack'].xp, reverse=True)
        self.update_image()
        self.generate_skill_hist_pic("Attack")
        self.show_skill_hist("Attack")
    def sort_by_strength(self):
        self.list = None
        self.list = sorted(self.game.players, key=lambda players: players.skills['Strength'].xp, reverse=True)
        self.update_image()
        self.generate_skill_hist_pic("Strength")
        self.show_skill_hist("Strength")
    def sort_by_defence(self):
        self.list = None
        self.list = sorted(self.game.players, key=lambda player: player.skills['Defence'].xp, reverse=True)
        self.update_image()
        self.generate_skill_hist_pic("Defence")
        self.show_skill_hist("Defence")
    def sort_by_ranged(self):
        self.list = None
        self.list = sorted(self.game.players, key=lambda player: player.skills['Ranged'].xp, reverse=True)
        self.update_image()
        self.generate_skill_hist_pic("Ranged")
        self.show_skill_hist("Ranged")
        
    def update_image(self):
        offset = 40
        self.image = copy(self.naked_image)
        for player in self.list:
            textsurface = arial10Font.render(player.__repr__(), True, BLACK)
            self.image.blit(textsurface, (0, offset))
            offset += 30
        # draw everything here
        pass
        
    def tick_update(self):
        # update all? maybe not, it can only update on clicks..
        pass
        
    def kill(self):
        self.game.highscores = None
        super().kill()
        
        
class EntityInfo(Window):
    # TODO - make each stat (text and value) have their own unique position so they don't move around when the values change
    def __init__(self, game, entity, pos):
        super().__init__(game, pos, ENTITYINFO_SIZE)
        self.entity = entity
        self.hpbar = None
        

        btn_pos = self.pos + vect(self.width-2*BTN_X_SIZE[0]-5,1)
        btn_teleport = Button(self.game, btn_pos, BTN_X_SIZE, "tp", self.teleport_spectator_to)
        self.sprites.add(btn_teleport)
        if isinstance(self.entity, Player):
            btn_pos = self.pos + vect(self.width-3*BTN_X_SIZE[0]-9,1)
            btn_atk_hist = Button(self.game, btn_pos, BTN_X_SIZE, "atk", partial(self.show_skill_hist, "Attack"))
            self.sprites.add(btn_atk_hist)
        
    def kill(self):
        self.game.entity_info = None     
        for sprite in self.sprites:
            sprite.kill()
        super().kill()
            

            
    def show_skill_hist(self, skill_name):
        self.entity.generate_skill_hist_pic(skill_name)
        if self.game.hist_window != None:
            self.game.hist_window.kill()
        img = pg.image.load(os.path.join(pic_folder, '{}_{}_graph.png'.format(self.entity.name, skill_name)))
        self.game.hist_window = PictureFrame(self.game, (40,40), img)
        
    def teleport_spectator_to(self):
        self.game.spectator.pos = copy(self.entity.pos)
        
    def update_image(self):
        self.image.fill((233,73,73,111))
        string = "{} cmb:{} HP: {}/{}".format(self.entity.name, int(self.entity.get_combat_lvl()), self.entity.skills['Hitpoints'].level_current, self.entity.skills['Hitpoints'].level)
        textsurface_name = arial10Font.render(string, True, BLACK, (170,170,170))
        self.image.blit(textsurface_name, ENTITYINFO_NAME_POS)
        #textsurface_stats = arial10Font.render(self.entity.get_combat_stats(), True, BLACK, (170,170,170))
        textsurface_stats = arial10Font.render(self.entity.__repr__(), True, BLACK, (170,170,170))
        self.image.blit(textsurface_stats, ENTITYINFO_CMBSTATS_POS)
        
        if self.hpbar == None:
            self.hpbar = HpBar(self.game, self.entity, pos=(textsurface_name.get_width() + 30, ENTITYINFO_NAME_POS[1] + textsurface_name.get_height()/2))
            self.sprites.add(self.hpbar)
        elif self.entity.name != self.hpbar.entity.name:
            self.hpbar.kill()
            self.hpbar = HpBar(self.game, self.entity, pos=(textsurface_name.get_width() + 30, ENTITYINFO_NAME_POS[1] + textsurface_name.get_height()/2))
            self.sprites.add(self.hpbar)
        else:
            self.hpbar.update_image()
        
        
        
    def tick_update(self):
        self.update_image()
        
    def update(self):
        pass
        