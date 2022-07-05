import pygame as pg
import numpy
import sys
from os import path

from settings import *
from sprites import *
from skills import *
from tilemap import *

from items import *
from general import *
from pickle import NONE

class Game:
    def __init__(self):
        pg.init()
        self.screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pg.display.set_caption(TITLE)
        self.clock = pg.time.Clock()
        pg.key.set_repeat(500, 100)
        
        self.load_data()
        
        self.hist_window = None

    def load_data(self):
        self.map = Map(path.join(game_folder, 'map2.txt'))
        
        
        self.player_img = pg.image.load(path.join(img_folder, PLAYER_IMG)).convert_alpha()
        transColor = self.player_img.get_at((1,1))
        self.player_img.set_colorkey(transColor)
        
        
        
        # MOB FILES
        self.mob_json_list = {}
        self.mob_images = {}
        for root, dirs, files in os.walk(json_mobs_folder, topdown=False):
            for json_file_name in files:
                mob_name = json_file_name[:-5]
                print(os.path.join(json_mobs_folder, json_file_name))
                self.mob_json_list[mob_name] = json_to_dict(os.path.join(json_mobs_folder, json_file_name))
                print("loaded stats from {}".format(json_file_name[:].lower()))
                
                img_file_name = json_file_name.replace('.json', '.bmp')
                img = pg.image.load(os.path.join(img_mobs_folder, img_file_name)).convert_alpha()
                transColor = img.get_at((0,0))
                img.set_colorkey(transColor)
                self.mob_images[mob_name] = img
                print("loaded image from {}".format(img_file_name))
                
                #self.mob_list[mob_name] = Mob(self, 0, 0, d)
                
        # ITEM FILES
        self.item_list = {}
        self.item_images = {}
        # some equip (like mob armor) is hidden - empty image is loaded
        hidden = False
        for root, dirs, files in os.walk(json_item_folder, topdown=True):
            for json_file_name in files:
                if len(files) > 0:
                    img_item_folder = root.replace('json', 'img')
                    item_name = json_file_name[:-5]
                    d = json_to_dict(os.path.join(root, json_file_name))
                    d['equipable'] = (d['equipable'] == 'True')
                    d['stackable'] = (d['stackable'] == 'True')
                    if d['equipable'] == True:
                        self.item_list[item_name] = Equipment(d)
                        hidden = d['hidden'] == 'True'
                    else:
                        self.item_list[item_name] = Item(d)
                        
                        
                    print("loaded stats from {} ({})".format(json_file_name[:].lower(),
                                                             self.item_list[item_name].name))
                    # TODO - FIX THIS (empty thing)
                    if json_file_name[:5].lower() != 'empty':
                        # TODO - try this replacement with .json -> .bmp
                        if hidden:
                            img_file_name = os.path.join(img_item_folder, json_file_name).rsplit('\\', 1)[0] +'\\empty.bmp'
                        else:
                            img_file_name = os.path.join(img_item_folder, json_file_name.replace('json', 'bmp'))
                        img = pg.image.load(os.path.join(img_item_folder, img_file_name)).convert_alpha()
                        transColor = img.get_at((0,0))
                        img.set_colorkey(transColor)
                        self.item_images[item_name] = img
                        print("loaded image from {}".format(img_file_name[:].lower()))
                        
                
        
        self.red_hitsplat_img = pg.image.load(path.join(img_folder, RED_HITSPLAT_IMG)).convert_alpha()
        transColor = self.red_hitsplat_img.get_at((0,0))
        self.red_hitsplat_img.set_colorkey(transColor)
        
        self.blue_hitsplat_img = pg.image.load(path.join(img_folder, BLUE_HITSPLAT_IMG)).convert_alpha()
        transColor = self.blue_hitsplat_img.get_at((0,0))
        self.blue_hitsplat_img.set_colorkey(transColor)
                

    def new(self):
        # init all variables and do all the setup
        self.all_sprites = pg.sprite.Group()
        self.walls = pg.sprite.Group()
        self.entities = pg.sprite.Group()
        self.mobs = pg.sprite.Group()
        self.bosses = pg.sprite.Group()
        self.players = pg.sprite.Group()
        self.projectiles = pg.sprite.Group()
        self.UI = pg.sprite.Group()
        self.spawners = pg.sprite.Group()
        self.gui_sprites = pg.sprite.Group()
        
        self.button_sprites = pg.sprite.Group()
        
        self.highscores = None
        
        # trigger TICKEVENT every TICK_LENGTH milliseconds
        pg.time.set_timer(TICKEVENT, TICK_LENGTH)
        player_names = np.unique(PLAYER_NAMES)
        player_name_idx = 0
        
        for row, tiles in enumerate(self.map.data):
            for col, tile in enumerate(tiles):
                if tile == '1':
                    Wall(self, col, row)
                if tile == 'M':
                    MobSpawner(self, 'Zombie', col, row)
                if tile == 'S':
                    self.spectator = Spectator(self, col, row)
                    # lvl 10 hp
                    self.spectator.skills['Hitpoints'].gain_xp(1200)
                    self.spectator.skills['Attack'].gain_xp(111200)
                    self.spectator.skills['Strength'].gain_xp(111200)
                    
                    
                    #self.b = TextBox(self, "testni text ki je malo dalsji da vidimo ce pravilno deluje funkcija ki dolg tekst razdeli v odsekn", (120,170), (100,300), 13, BLACK, WHITE)
                if tile == 'P':
                    #self.player = Player(self, col, row)
                    player = Player(self, col, row, player_names[player_name_idx])
                    player_name_idx += 1
                if tile == 'B':
                    MobSpawner(self, 'Boss', col, row)
                if tile == 'D':
                    MobSpawner(self, 'Green Dragon', col, row)
                    

        #self.entity_info = EntityInfo(self, self.spectator, (0,0), (300,200))
        self.entity_info = None
        
        self.camera = Camera(self.map.width, self.map.height)

    def run(self):
        # game loop - set self.playing = False to end game
        self.playing = True
        while self.playing:
            self.dt = self.clock.tick(FPS) / 1000
            #print(self.dt)
            self.events()
            self.update()
            self.draw()

    def quit(self):
        pg.quit()
        sys.exit()

    def update(self):
        #self.player.update()
        self.all_sprites.update()
        self.camera.update(self.spectator)

    def draw_grid(self):
        for x in range(0, SCREEN_WIDTH, TILESIZE):
            pg.draw.line(self.screen, LIGHTGREY, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, TILESIZE):
            pg.draw.line(self.screen, LIGHTGREY, (0, y), (SCREEN_WIDTH, y))

    def draw_player_info(self):
        spacing = 30
        box_startpos = vect(SCREEN_WIDTH-INFOBOX_WIDTH, 0)
        pg.draw.rect(self.screen, (200,200,200),
                         pg.Rect(*box_startpos, INFOBOX_WIDTH, INFOBOX_HEIGHT))
        for idx, player in enumerate(self.players):
            draw_text(self.screen, player.__repr__(), (box_startpos[0]+4,idx*spacing))
            draw_text(self.screen, 'gp: '+str(player.gp.amount), (box_startpos[0]+4,(idx+0.4)*spacing))
        idx_end = idx + 2
        for idx, mob in enumerate(self.mobs):
            draw_text(self.screen, mob.__repr__(), (box_startpos[0]+4,(idx+idx_end)*spacing))

    def draw(self):
        pg.display.set_caption("{:.2f}".format(self.clock.get_fps()))
        self.screen.fill(BGCOLOR)
        self.draw_grid()
        for sprite in self.all_sprites:
            if not sprite in self.gui_sprites:
                self.screen.blit(sprite.image, self.camera.apply(sprite))
        # blit UI elements separately and last 
        for sprite in self.gui_sprites:
            self.screen.blit(sprite.image, sprite)
                
                
        #self.draw_player_info()
        pg.display.flip()

    def events(self):
        global TICK_LENGTH
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()
                
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.quit()
                elif event.key == pg.K_i:
                    if self.highscores == None:
                        self.highscores = HighScores(self, (0,0))
                        print(self.entity_info.__repr__())
                elif event.key == pg.K_PERIOD:
                    TICK_LENGTH /= 2
                    pg.time.set_timer(TICKEVENT, int(TICK_LENGTH))
                    print('game speed changed. TICK_LENGTH={}'.format(TICK_LENGTH))
                elif event.key == pg.K_COMMA:
                    TICK_LENGTH *= 2
                    pg.time.set_timer(TICKEVENT, int(TICK_LENGTH))
                    print('game speed changed. TICK_LENGTH={}'.format(TICK_LENGTH))
                        
                elif event.key == pg.K_p:
                    for player in self.players:
                        if player.name == 'Mario':
                            player.inventory.add(copy(self.item_list['rune_scimitar']))
                    for player in self.players:
                        if len(player.inventory.items) > 0:
                            print(', '.join([item.name for item in player.inventory.items]))
                    

            if event.type == TICKEVENT:
                for sprite in self.all_sprites:
                    sprite.tick_update()
                
            # update entityInfo box with clicked entity's info
            if event.type == pg.MOUSEBUTTONDOWN:
                pos = pg.mouse.get_pos()
                if event.button == 3: # right click
                    
                    map_pos = (pos[0] - self.camera.camera.left, pos[1] - self.camera.camera.top)
                    # check if we clicked on any entities
                    entities = pg.sprite.Group()
                    for entity in self.entities:
                        if entity.rect.collidepoint(map_pos):
                            entities.add(entity)
                            
                    if entities:
                        # TODO - handle selecting if multiple entities are hit
                        # selection Sprite class to be implemented?
                        click_registered = True
                        if isinstance(entities.sprites()[0], Entity):
                            self.spectator.hit(entities.sprites()[0])
                            
                elif event.button == 1: # left click
                    click_registered = False
                    """
                    TODO
                    
                        PREVENT CLICKS THROUGH UI ELEMENTS!!!!
                        
                    TODO
                    """
                    
                    """
                    CHECK UI
                    """
                    # check if buttons were clicked
                    buttons = []
                    for button in self.button_sprites:
                        if button.rect.collidepoint(pos):
                            buttons.append(button)
                    # execute the last button hit (the one on top)
                    if buttons:
                        buttons[-1].execute()
                        click_registered = True
                    
                    """
                    CHECK CLICK ON MAP (IF NO UI CLICKED)
                    """
                    if not click_registered:
                        # adjust pos for camera offset
                        map_pos = (pos[0] - self.camera.camera.left, pos[1] - self.camera.camera.top)
                        # check if we clicked on any entities
                        entities = pg.sprite.Group()
                        for entity in self.entities:
                            if entity.rect.collidepoint(map_pos):
                                entities.add(entity)
                                
                        if entities:
                            # TODO - handle selecting if multiple entities are hit
                            # selection Sprite class to be implemented?
                            click_registered = True
                            if self.entity_info == None:
                                self.entity_info = EntityInfo(self, entities.sprites()[0], (0,0))
                            elif self.entity_info.entity.name != entities.sprites()[0].name:
                                # grab the first in the list
                                self.entity_info.kill()
                                self.entity_info = EntityInfo(self, entities.sprites()[0], (0,0))
                
                        
    def show_start_screen(self):
        pass

    def show_gameover_screen(self):
        pass

def testFun1():
    print('test fun 1')
def testFun2():
    print('test fun 2')
def testFun3():
    print('test fun 3')

def main():
    g = Game()
    g.show_start_screen()
    g.new()
    g.run()
    g.show_gameover_screen()



if __name__ == '__main__':
    main()
