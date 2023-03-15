from settings import *


def collide_hit_rect(one, two):
    return one.hit_rect.colliderect(two.rect)

def collide_sense(sense, entity):
    # don't sense self
    if sense == entity.sense:
        return False
    # check difference in position vs the higher of the entity's width/height
    return (sense.pos - entity.pos).length() - sense.radius < (entity.rect.width/2 + entity.rect.height/2)/2 / TILESIZE

class Map():
    def __init__(self, filename):
        self.data = []
        with open(filename, 'rt') as f:
            for line in f:
                self.data.append(line.strip())

        self.tilewidth = len(self.data[0])
        self.tileheight = len(self.data)
        self.width = self.tilewidth * TILESIZE
        self.height = self.tileheight * TILESIZE

class Camera():
    def __init__(self, width, height):
        self.camera = pg.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)

        # limit scrolling
        x = min(0, x)
        y = min(0, y)
        x = max(-(self.width - SCREEN_WIDTH), x)
        y = max(-(self.height - SCREEN_HEIGHT), y)
        self.camera = pg.Rect(x, y, self.width, self.height)