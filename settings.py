import pygame as pg
from os import path
vect = pg.math.Vector2

pg.font.init()
arial18Font = pg.font.SysFont('Arial', 18)
arial10Font = pg.font.SysFont('Arial', 10)

# TILES PER TICK
PROJECTILE_SPEED = 1

INVENTORY_SIZE = 5

ENTITYINFO_SIZE = (340,60)
HIGHSCORES_SIZE = (300,500)

BTN_X_SIZE = (20,20)


game_folder = path.dirname(__file__)

data_folder = path.join(game_folder, 'data')

pic_folder = path.join(data_folder, 'pic')

img_folder = path.join(data_folder, 'img')
json_folder = path.join(data_folder, 'json')

img_item_folder = path.join(img_folder, 'items')
img_mobs_folder = path.join(img_folder, 'mobs')

json_item_folder = path.join(json_folder, 'items')
json_mobs_folder = path.join(json_folder, 'mobs')

json_fists = path.join(path.join(json_item_folder, 'equipment'), 'fists.json')

GOLDPIECES_DICT = path.join(json_item_folder, 'gold_pieces.json')

XP_MULTIPLIER = 4

RESPAWN_DELAY_MOB = 10

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
DARKGREY = (40, 40, 40)
LIGHTGREY = (100, 100, 100)

TICKEVENT = pg.USEREVENT+1
TICK_LENGTH = 200

SENSE_RADIUS = 6
SENSE_OPACITY = 7
SENSE_COLOR = (179,255,255)

DIRECTIONS = [vect(-1,-1), vect(0,-1), vect(1,-1),
              vect(-1,0),             vect(1,0),
              vect(-1,1), vect(0,1), vect(1,1)]


SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 120


INFOBOX_HEIGHT = 400
INFOBOX_WIDTH = 280

BGCOLOR = DARKGREY

TITLE = 'game n. 1'

TILESIZE = 32
GRIDWIDTH = SCREEN_WIDTH / TILESIZE
GRIDHEIGHT = SCREEN_HEIGHT / TILESIZE


PLAYER_IMG = 'stickman.bmp'
ZOMBIE_IMG = 'zombie.png'
RED_HITSPLAT_IMG = 'red_hitsplat.bmp'
BLUE_HITSPLAT_IMG = 'blue_hitsplat.bmp'

PLAYER_NAMES = ['Mario', 'Pero', 'Jay', 'Pierre', 'Bato', 'Janez', 'Berto',
         'John', 'Miha', 'Jwza', 'Neo', 'Miro', 'Fago']



MOB_MOVE_RANGE = 12

PLAYER_HIT_RECT = pg.Rect(0, 0, 120, 120)
MOB_HIT_RECT = pg.Rect(0, 0, 30, 30)

SKILL_NAMES = ["Hitpoints", "Attack", "Strength", "Defence", "Magic", "Ranged", "Prayer"]
DAMAGE_TYPES = ['stab', 'slash', 'crush', 'magic', 'ranged']
OTHER_EQUIPMENT_BONUS_TYPES = ['melee_str', 'ranged_str', 'magic_dmg', 'prayer']
PRAYER_BONUS_TYPES = ['attack', 'strength', 'defence', 'magic', 'ranged']

EQUIP_TYPES = ["head", "body", "legs", "hands", "feet", "weapon", "shield", "ammunition", "amulet"]

MAX_HITSPLATS = 3

HP_REGEN_TICKDELAY = 60

MOB_WANDER_TICKDELAY = 10
HITSPLAT_TICKDURATION = 3

HPBAR_TICKDURATION = 4
HPBAR_HEIGHT = 8
HPBAR_WIDTH = 30
HPBAR_OPACITY = 120
HPBAR_COLOR = GREEN
HPBAR_DMGCOLOR = RED

HPBAR_VERT_OFFSET = -TILESIZE


# weapon positions on player image
#EQUIP_TYPES = ["head", "body", "legs", "hands", "feet", "weapon", "arrows", "amulet"]
IMG_EQUIP_POS = {}
IMG_EQUIP_POS['head'] = (31,10)
IMG_EQUIP_POS['body'] = (32,26)
IMG_EQUIP_POS['legs'] = (32,45)
IMG_EQUIP_POS['hands'] = (32,26)
IMG_EQUIP_POS['feet'] = (31,55)
IMG_EQUIP_POS['weapon'] = (48,30)
IMG_EQUIP_POS['shield'] = (15,30)
IMG_EQUIP_POS['ammunition'] = (10,10)
IMG_EQUIP_POS['amulet'] = (31,20)

MOB_TYPES = ['Zombie', 'Rat', 'Mob', 'Boss']

"""
shield (15,30)
weapon(48,30)
boots(32,55)
helmet(32,14)
body(32,26)
legs(32,45)
amulet(31,20)
"""
