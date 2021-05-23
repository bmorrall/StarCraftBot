
import random

import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2 import position
from sc2.ids.unit_typeid import UnitTypeId
from sc2.player import Bot, Computer
from sc2.constants import COMMANDCENTER, SCV, SUPPLYDEPOT, BARRACKS, MARINE, \
    REFINERY, FACTORY, HELLION, REAPER, \
    SUPPLYDEPOTLOWERED, MORPH_SUPPLYDEPOT_LOWER, MORPH_SUPPLYDEPOT_RAISE

from botlib.terran_bot import TerranBot

class AlphaBot(TerranBot):
    def __init__(self):
        self.scout_target = None
        super().__init__()

    async def on_step(self, iteration):
        # Plan out Operations
        await self.distribute_workers()  # in sc2/bot_ai.py
        await self.train_workers()
        await self.train_reaper()
        await self.train_marines()
        await self.train_hellions()
        # await self.repair_command_center()

        # Configure all background services
        self.building_constructor.set_command_center_target(self.command_center_target)
        self.building_constructor.set_barracks_target(self.barracks_target)
        self.building_constructor.set_factory_target(self.factory_target)
        self.building_constructor.set_refinery_target(self.refinery_target)

        await self.move_reaper()
        await self.marines_attack()
        if self.units(MARINE).amount >= 20:
            await self.hellions_attack()

        # Allow background services to do their thing
        await super().on_step(iteration)

    @property
    def command_center_target(self) -> int:
        return 2

    @property
    def barracks_target(self) -> int:
        if not self.units.of_type([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.SUPPLYDEPOTDROP]).ready:
            return 0
        elif self.units(COMMANDCENTER).amount == 1:
            return 1
        return 5

    @property
    def refinery_target(self) -> int:
        if not self.units(BARRACKS):
            return 0
        elif not self.units(FACTORY) and self.already_pending(FACTORY) == 0:
            return 1

        target = 0
        for cc in self.units(COMMANDCENTER).ready:
            target += self.state.vespene_geyser.closer_than(25.0, cc).amount
        return target

    @property
    def factory_target(self) -> int:
        if not self.units(BARRACKS).ready:
            return 0

        return self.units(REFINERY).amount

    async def train_reaper(self):
        if self.units(REAPER).amount + self.already_pending(REAPER) == 0:
            idle_barracks = self.units(BARRACKS).ready.idle
            if idle_barracks and self.can_afford(REAPER):
                barracks = idle_barracks.first
                await self.do(barracks.train(REAPER))

    async def train_marines(self):
        for barracks in self.units(BARRACKS).ready.idle:
            if self.can_afford(MARINE):
                await self.do(barracks.train(MARINE))

    async def train_hellions(self):
        for factory in self.units(FACTORY).ready.idle:
            if self.can_afford(HELLION):
                await self.do(factory.train(HELLION))

    async def move_reaper(self):
        if self.units(REAPER):
            reaper = self.units(REAPER).first
            if self.scout_target is None or reaper.distance_to(p=self.scout_target) < 5:
                self.scout_target = random.choice(
                    list(self.expansion_locations))
            await self.do(reaper.move(self.scout_target))
        else:
            self.scout_target = None

    # Attack with all Marines
    async def marines_attack(self):
        if self.known_enemy_structures:
            target = self.known_enemy_structures.first
        else:
            target = self.enemy_start_locations[0]

        for marine in self.units(MARINE).idle:
            attackable_units = self.known_enemy_units.not_structure.visible.in_attack_range_of(
                unit=marine, bonus_distance=20)
            if attackable_units:
                await self.do(marine.attack(attackable_units.sorted(lambda unit: unit.health).first))
            elif self.units(MARINE).amount >= 20:
                await self.do(marine.attack(target))

    # Attack with all Hellions
    async def hellions_attack(self):
        if self.known_enemy_units.visible:
            target = self.known_enemy_units.visible.first
        else:
            target = self.enemy_start_locations[0]

        for hellion in self.units(HELLION).idle:
            await self.do(hellion.attack(target))



run_game(maps.get("Simple64"), [
    Bot(Race.Terran, AlphaBot()),
    Computer(Race.Protoss, Difficulty.Easy)
], realtime=False)
