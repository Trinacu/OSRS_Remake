import os
import json

from settings import *

def dict_to_json(dictionary, filename):
    if filename[-5:] != '.json':
        filename = filename+'.json'
    with open(os.path.join('json', filename), 'w+') as json_file:
         json.dump(dictionary, json_file, indent=4)

def json_to_dict(filename):
    if filename[-5:] != '.json':
        filename = filename+'.json'
    with open(filename) as json_file:
        return json.load(json_file)

def shift(seq, n):
    n = n % len(seq)
    return seq[n:] + seq[:n]

def grid2screen_coord(pos):
    return (pos + vect(0.5,0.5)) * TILESIZE
