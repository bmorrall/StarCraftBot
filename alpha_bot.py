
from botlib.build_queue import BuildQueue
import random

import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2 import position
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.player import Bot, Computer
from sc2.constants import COMMANDCENTER, BARRACKS, MARINE, SCV, \
    REFINERY, FACTORY, HELLION, REAPER, ORBITALCOMMAND, STARPORT, MEDIVAC, SUPPLYDEPOT

from botlib.terran_bot import TerranBot


class AlphaBot(TerranBot):
    def __init__(self):
        self.scout_target = None
        super().__init__()

        # Configure the Build Queue
        self.build_queue = BuildQueue()

        # https://lotv.spawningtool.com/build/111889/
        self.build_queue.add_step(COMMANDCENTER, 1)
        self.build_queue.add_step(BARRACKS, 1)
        self.build_queue.add_step(REFINERY, 1)
        self.build_queue.add_step(ORBITALCOMMAND, 1)
        self.build_queue.add_step(COMMANDCENTER, 1)
        self.build_queue.add_step(FACTORY, 1)
        self.build_queue.add_step(REFINERY, 1)
        self.build_queue.add_step(STARPORT, 1)
        self.build_queue.add_step(ORBITALCOMMAND, 1)

        # legacy win code
        self.build_queue.add_step(FACTORY, 1)
        self.build_queue.add_step(BARRACKS, 2)
        self.build_queue.add_step(REFINERY, 2)
        self.build_queue.add_step(FACTORY, 1)
        self.build_queue.add_step(BARRACKS, 2)

    async def on_step(self, iteration):
        # Configure all background services
        await self.build_queue.on_step(self.units, self.building_constructor)

        # Allow background services to do their thing
        await super().on_step(iteration)

        await self.resume_buildings()
        if self.units.of_type([COMMANDCENTER, ORBITALCOMMAND]):
            await self.distribute_workers()  # in sc2/bot_ai.py
            await self.call_down_mules()

        # Plan out Operations
        await self.train_workers()
        await self.train_reaper()
        await self.train_marines()
        await self.train_hellions()
        await self.train_medivacs()
        # await self.repair_command_center()

        await self.move_reaper()
        await self.marines_attack()
        await self.heal_marines()
        if self.units(MARINE).amount >= 20:
            await self.hellions_attack()

    @property
    def command_center_target(self) -> int:
        return 2

    @property
    def orbital_command_target(self) -> int:
        if self.units(FACTORY).ready:
            return 2
        elif self.units(BARRACKS).ready:
            return 1
        return 0

    @property
    def barracks_target(self) -> int:
        if not self.units.of_type([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.SUPPLYDEPOTDROP]).ready:
            return 0
        elif self.units.of_type([COMMANDCENTER, ORBITALCOMMAND]).amount == 1:
            return 1
        return 5

    @property
    def refinery_target(self) -> int:
        if not self.units(BARRACKS):
            return 0
        elif not self.units(FACTORY) and self.already_pending(FACTORY) == 0:
            return 1

        target = 0
        for cc in self.units.of_type([COMMANDCENTER, ORBITALCOMMAND]).ready:
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

    async def train_medivacs(self):
        if self.units(MEDIVAC).amount + self.already_pending(MEDIVAC) < 5:
            idle_starport = self.units(STARPORT).ready.idle
            if idle_starport and self.can_afford(MEDIVAC):
                starport = idle_starport.first
                await self.do(starport.train(MEDIVAC))

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

    async def heal_marines(self):
        injured_marines = self.units(MARINE).filter(
            lambda x: x.health < x.health_max and not self.units(MEDIVAC).filter(lambda m: m.order_target == x.tag))
        if not injured_marines:
            return

        for medivac in self.units(MEDIVAC).idle.filter(lambda x: not x.order_target):
            if medivac.energy > 5 and injured_marines:
                closest_marine = injured_marines.closest_to(medivac.position)
                await self.do(medivac(AbilityId.MEDIVACHEAL_HEAL, closest_marine))

    async def resume_buildings(self):
        ''' Resume all incomplete buildings '''

        # of_type([COMMANDCENTER, ORBITALCOMMAND, SUPPLYDEPOT]).
        # TODO: Handle Refineries
        incomplete_structures = self.units.structure.not_ready.filter(
            lambda x: x.health < x.health_max and not x.type_id == REFINERY and not self.units(SCV).filter(lambda s: s.is_constructing_scv and s.order_target == x.position or s.order_target == x.tag))

        for structure in incomplete_structures:
            idle_scvs = self.units(SCV).idle
            if idle_scvs:
                print("Fix with idle", structure)
                await self.repair_with_scv(idle_scvs, structure)
                return

            non_vespene_scvs = self.units(SCV).filter(
                lambda x: not x.is_carrying_vespene and not x.is_carrying_minerals)
            if non_vespene_scvs:
                print("Fix with worker", structure)
                await self.repair_with_scv(non_vespene_scvs, structure)
                return

    # Uses the "SMART" ability to resume construction
    async def repair_with_scv(self, scvs, structure):
        scv = scvs.closest_to(structure.position)
        await self.do(scv(AbilityId.SMART, structure))


run_game(maps.get("Simple64"), [
    Bot(Race.Terran, AlphaBot()),
    Computer(Race.Protoss, Difficulty.Easy)
], realtime=False)
