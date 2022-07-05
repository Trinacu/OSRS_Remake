from settings import *
from general import json_to_dict
from copy import copy

class Inventory():
    def __init__(self, entity, size=INVENTORY_SIZE):
        self.entity = entity
        self.size = size
        self.items = []
        
    def on_death(self):
        self = Inventory(self.entity)
        
    def add(self, added_item):
        if (added_item.stackable):
            for item in self.items:
                if (item.name == added_item.name):
                    item = item + added_item
                    return True
            else:
                self.items.append(added_item)
                return True
        elif (len(self.items) < self.size):
            self.items.append(added_item)
            return True
        else:
            print("{}'s inventory is full".format(self.entity.name))
            print(' '.join([item.name for item in self.items]))
            return False

class Item():
    def __init__(self, init_dict=None, amount=1):
        # read json into dict for initialisation
        if init_dict != None:
            self.name = init_dict['name']
            self.equipable = init_dict['equipable']
            self.stackable = init_dict['stackable']
            if self.stackable:
                self.amount = amount
                
    """
                , name, stackable=False):
        self.name = name
        self.stackable = stackable
        if self.stackable:
            self.amount = 1
    """
    
    def __add__(self, other):
        if ((self.name == other.name) and (self.stackable == True)):
            self.amount += other.amount
            other = None
            return self
        
class GoldPieces(Item):
    def __init__(self, amount=0):
        super().__init__(json_to_dict(GOLDPIECES_DICT), amount)
