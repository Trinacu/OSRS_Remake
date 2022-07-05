from settings import EQUIP_TYPES, DAMAGE_TYPES, OTHER_EQUIPMENT_BONUS_TYPES

from items import *
from general import *

import pygame as pg
import os
from pickle import NONE


#EMPTY_EQUIP_SLOT = Equipment()

class Gear():
    def __init__(self, game, entity):
        # DEFINE ALL TYPES OF EQUIPMENT
        self.items = {}
        self.game = game
        self.entity = entity
        
        self.init()
        self.update_total_bonuses()
        
    def init(self):
        # create empty slots
        for equip_class in EQUIP_TYPES:
            self.items[equip_class] = None
            self.items['weapon'] = self.game.item_list['fists']
            
        self.total_bonuses = Equipment_Bonuses()
        
    def on_death(self):
        self.init()
        
    def unequip(self, item):
        if item not in [item for _, item in self.items.items()]:
            return
        if len(self.entity.inventory) < self.entity.inventory.size:
            self.items[item.equip_class] = None
            self.entity.inventory.append(item)

    def equip(self, item):
        # check for level requirements?
        # check if slot empty etc
        old_item = self.items[item.equip_class]
            
        self.items[item.equip_class] = item
        print('{} equipping {}'.format(self.entity.name, item.name))
        
        if hasattr(self.entity, 'inventory'):
            # if equiped from inventory
            if item in self.entity.inventory.items:
                #print("removed {} from {}'s inventory".format(item.name, self.entity.name))
                self.entity.inventory.items.remove(item)
                
            if ((old_item != None) and (old_item.name != 'Fists')):
                #print("added {} from {}'s gear to inventory".format(old_item.name, self.entity.name))
                self.entity.inventory.add(old_item)
        
        #print(item.name)
        # add up all items' bonuses
        self.update_total_bonuses()

    def update_total_bonuses(self):
        self.total_bonuses = Equipment_Bonuses()
        for _, item in self.items.items():
            if item != None:
                self.total_bonuses += item.bonuses

    def __repr__(self):
        tmp = "\nItems:\n"
        for item_type, item in self.items.items():
            # to align values in print
            if len(item_type) < 8:
                tmp += "{}:\t\t{}\n".format(item_type, item.name)
            else:
                tmp += "{}:\t{}\n".format(item_type, item.name)
        tmp += "Total gear bonuses:\n"
        tmp += repr(self.total_bonuses)
        return tmp

class Equipment_Bonuses():
    def __init__(self, init_dict=None):
        if init_dict != None:
            self.attack = init_dict['attack']
            self.defence = init_dict['defence']
            self.other = init_dict['other']
        else:
            self.attack = {}
            self.defence = {}
            self.other = {}
            for dmg_type in DAMAGE_TYPES:
                self.attack[dmg_type] = 0
                self.defence[dmg_type] = 0
            for bonus_type in OTHER_EQUIPMENT_BONUS_TYPES:
                self.other[bonus_type] = 0

    def __add__(self, other):
        total = Equipment_Bonuses()
        for dmg_type in DAMAGE_TYPES:
            total.attack[dmg_type] = self.attack[dmg_type] + other.attack[dmg_type]
            total.defence[dmg_type] = self.defence[dmg_type] + other.defence[dmg_type]
        for bonus_type in OTHER_EQUIPMENT_BONUS_TYPES:
            total.other[bonus_type] = self.other[bonus_type] + other.other[bonus_type]
        return total

    def __repr__(self):
        tmp = ""
        for dmg_type in DAMAGE_TYPES:
            tmp += "{}:\tatk={}\tdef={}\n".format(dmg_type, self.attack[dmg_type], self.defence[dmg_type])
        for bonus_type in OTHER_EQUIPMENT_BONUS_TYPES:
            tmp += "{}:\t{}\n".format(bonus_type, self.other[bonus_type])
        return tmp

class Equipment(Item):
    def __init__(self, init_dict=None):
        # read json into dict for initialisation
        if init_dict != None:
            super().__init__(init_dict)
            #name, stackable and equipable are init-ed in Item class
            self.equip_class = init_dict['equip_class']
            self.bonuses = Equipment_Bonuses(init_dict['bonuses'])
            if self.equip_class == 'weapon':
                self.weapon_range = init_dict['weapon_range']
                self.attack_delay = init_dict['attack_delay']
                self.dmg_type = init_dict['dmg_type']
        """
        else:
            # FISTS
            self.name = 'Empty'
            self.equip_class = 'weapon'
            
            if self.equip_class == 'weapon':
                self.weapon_range = 1
                self.dmg_type = 'crush'
                self.attack_delay = 3
        """
    def __repr__(self):
        tmp = "{}'s ({}) total bonuses:\n".format(self.name, self.equip_class)
        for dmg_type in DAMAGE_TYPES:
            tmp += "{}\tatk: {}\t def: {}\n".format(dmg_type, self.bonuses.attack[dmg_type], self.bonuses.defence[dmg_type])
        for bonus_type in OTHER_EQUIPMENT_BONUS_TYPES:
            tmp += "{}:\t{}\n".format(bonus_type, self.bonuses.other[bonus_type])
        return tmp
