import random

import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2 import position
from sc2.player import Bot, Computer
from sc2.constants import COMMANDCENTER, SCV, SUPPLYDEPOT, BARRACKS, MARINE, \
    REFINERY, FACTORY, HELLION, REAPER, \
    SUPPLYDEPOTLOWERED, MORPH_SUPPLYDEPOT_LOWER, MORPH_SUPPLYDEPOT_RAISE


class AlphaBot(sc2.BotAI):
    def __init__(self):
        self.scout_target = None

    async def on_step(self, iteration):
        await self.distribute_workers()  # in sc2/bot_ai.py
        await self.train_workers()
        await self.build_supply_depot()
        await self.build_barracks()
        await self.build_refineries()
        await self.build_factories()
        await self.train_reaper()
        await self.train_marines()
        await self.train_hellions()
        await self.raise_lower_depots()
        await self.expand()

        await self.move_reaper()
        await self.marines_attack()
        if self.units(MARINE).amount >= 20:
            await self.hellions_attack()

    def target_barracks(self):
        if self.units(COMMANDCENTER).amount == 1:
            return 1
        return 5

    def target_refineries(self):
        if not self.units(BARRACKS):
            return 0
        elif not self.units(FACTORY) and self.already_pending(FACTORY) == 0:
            return 1

        target = 0
        for cc in self.units(COMMANDCENTER).ready:
            target += self.state.vespene_geyser.closer_than(25.0, cc).amount
        return target

    def target_factories(self):
        if not self.units(BARRACKS):
            return 0

        return self.units(REFINERY).amount

    def target_workers(self):
        ideal = 1  # one for construction
        for cc in self.units(COMMANDCENTER):
            ideal += cc.ideal_harvesters
        # Add pending command center units count
        ideal += self.already_pending(COMMANDCENTER) * 8
        # Add refinery counts
        ideal += self.units(REFINERY).amount * 3
        return ideal

    async def train_workers(self):
        if self.workers.amount < self.target_workers():
            for cc in self.units(COMMANDCENTER).idle:
                if self.can_afford(SCV):
                    await self.do(cc.train(SCV))

    async def build_supply_depot(self):
        # Find all urgently required depot locations
        depot_placement_positions = self.main_base_ramp.corner_depots
        depots = self.units(SUPPLYDEPOT) | self.units(SUPPLYDEPOTLOWERED)
        if depots:
            depot_placement_positions = {
                d for d in depot_placement_positions if depots.closest_distance_to(d) > 1}

        # Urgently build supply depots (anti-cheese)
        if len(depot_placement_positions) > 0:
            target_depot_location = depot_placement_positions.pop()
            if self.can_afford(SUPPLYDEPOT):
                await self.build(SUPPLYDEPOT, target_depot_location)

        # Build any other supply depots as needed
        elif self.supply_left < 5 and self.already_pending(SUPPLYDEPOT) < self.units(BARRACKS).amount:
            if self.can_afford(SUPPLYDEPOT) and self.units(COMMANDCENTER).ready:
                await self.build(SUPPLYDEPOT, near=self.units(COMMANDCENTER).random.position.towards(self.game_info.map_center, 8))

    async def build_barracks(self):
        # barracks_placement_position = self.main_base_ramp.barracks_correct_placement
        barracks_placement_position = self.main_base_ramp.barracks_in_middle
        if self.can_afford(BARRACKS) and not self.already_pending(BARRACKS):
            barracks = self.units(BARRACKS)
            if barracks.amount > 0 and barracks.amount < self.target_barracks():
                await self.build(BARRACKS, near=barracks.first)
            elif barracks.amount == 0:
                # Build the safety barracks
                await self.build(BARRACKS, barracks_placement_position)

    async def build_refineries(self):
        target = self.target_refineries()
        target -= self.units(REFINERY).amount
        target -= self.already_pending(REFINERY)

        if target <= 0:
            return

        for cc in self.units(COMMANDCENTER).ready:
            vaspenes = self.state.vespene_geyser.closer_than(25.0, cc)
            for vaspene in vaspenes:
                if self.can_afford(REFINERY) and target > 0:
                    worker = self.select_build_worker(vaspene.position)
                    if worker is None:
                        break

                    target -= 1
                    await self.do(worker.build(REFINERY, vaspene))

    async def build_factories(self):
        factories_amount = self.units(FACTORY).amount
        target = self.target_factories()

        if factories_amount < target and self.can_afford(FACTORY):
            await self.build(FACTORY, near=self.units(BARRACKS).first)

    async def expand(self):
        cc_count = self.units(COMMANDCENTER).amount + \
            self.already_pending(COMMANDCENTER)
        if cc_count < 2 and self.can_afford(COMMANDCENTER):
            await self.expand_now()

    async def raise_lower_depots(self):
        # Raise depos when enemies are nearby
        for depo in self.units(SUPPLYDEPOT).ready:
            for unit in self.known_enemy_units.not_structure.visible:
                if unit.position.to2.distance_to(depo.position.to2) < 15:
                    break
            else:
                await self.do(depo(MORPH_SUPPLYDEPOT_LOWER))

        # Lower depos when no enemies are nearby
        for depo in self.units(SUPPLYDEPOTLOWERED).ready:
            for unit in self.known_enemy_units.not_structure.visible:
                if unit.position.to2.distance_to(depo.position.to2) < 10:
                    await self.do(depo(MORPH_SUPPLYDEPOT_RAISE))
                    break

    async def train_reaper(self):
        if self.units(REAPER).amount + self.already_pending(REAPER) == 0:
            if self.units(BARRACKS).idle and self.can_afford(REAPER):
                barracks = self.units(BARRACKS).idle.first
                await self.do(barracks.train(REAPER))

    async def train_marines(self):
        for barracks in self.units(BARRACKS).idle:
            if self.can_afford(MARINE) and barracks.is_idle:
                await self.do(barracks.train(MARINE))

    async def train_hellions(self):
        for factory in self.units(FACTORY).idle:
            if self.can_afford(HELLION):
                await self.do(factory.train(HELLION))

    async def move_reaper(self):
        if self.units(REAPER):
            reaper = self.units(REAPER).first
            if self.scout_target is None or reaper.distance_to(p=self.scout_target) < 5:
                print("Found target")
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

        for marine in self.units(MARINE):
            attackable_units = self.known_enemy_units.not_structure.visible.in_attack_range_of(
                unit=marine, bonus_distance=5)
            if attackable_units:
                await self.do(marine.attack(attackable_units.sorted_by_distance_to(marine).first))
            elif self.units(MARINE).amount >= 20:
                await self.do(marine.attack(target))

    # Attack with all Hellions
    async def hellions_attack(self):
        if self.known_enemy_units.visible:
            target = self.known_enemy_units.visible.first
        else:
            target = self.enemy_start_locations[0]

        for hellion in self.units(HELLION):
            await self.do(hellion.attack(target))

    # Attack with all Workers
    async def worker_attack(self):
        for worker in self.workers:
            await self.do(worker.attack(self.enemy_start_locations[0]))


run_game(maps.get("Simple64"), [
    Bot(Race.Terran, AlphaBot()),
    Computer(Race.Protoss, Difficulty.Easy)
], realtime=True)
