import numpy as np

class Skill():
    def __init__(self, name):
        self.name = name
        self.level = 1
        self.level_current = 1
        self.xp = 0
        self.next_lvl_xp = 0

    def update_xp_to_lvl(self):
        self.next_lvl_xp = np.floor(0.25 * np.sum([(lvl + 300 * 2**(lvl/7)) for lvl in range(1, self.level+1)]))

    def gain_xp(self, amount):
        self.xp += amount
        gained_lvls = []
        while(self.xp > self.next_lvl_xp):
            self.level += 1
            self.level_current += 1
            self.update_xp_to_lvl()
            gained_lvls.append(self.level)
        return gained_lvls

