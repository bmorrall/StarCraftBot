import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import COMMANDCENTER, SCV, SUPPLYDEPOT, SUPPLYDEPOTLOWERED, MORPH_SUPPLYDEPOT_LOWER, MORPH_SUPPLYDEPOT_RAISE


class AlphaBot(sc2.BotAI):
    async def on_step(self, iteration):
        await self.distribute_workers()  # in sc2/bot_ai.py
        await self.build_workers()
        await self.build_supply_depot()
        await self.raise_lower_depots()
        await self.expand()

    async def build_workers(self):
        ideal = 1 # one for construction
        for cc in self.units(COMMANDCENTER):
            ideal += cc.ideal_harvesters
        # Add pending command center units count
        ideal += self.already_pending(COMMANDCENTER) * 8

        for cc in self.units(COMMANDCENTER).idle:
            if self.workers.amount < ideal and self.can_afford(SCV) and cc.is_idle:
                await self.do(cc.train(SCV))

    async def build_supply_depot(self):
        # Find all urgently required depot locations
        depot_placement_positions = self.main_base_ramp.corner_depots | {
            self.main_base_ramp.depot_in_middle}
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
        elif self.supply_left < 5 and not self.already_pending(SUPPLYDEPOT):
            if self.can_afford(SUPPLYDEPOT) and self.units(COMMANDCENTER).ready:
                await self.build(SUPPLYDEPOT, near=depots.last)


    async def expand(self):
        cc_count = self.units(COMMANDCENTER).amount + self.already_pending(COMMANDCENTER)
        if cc_count < 2 and self.can_afford(COMMANDCENTER):
            await self.expand_now()

    async def raise_lower_depots(self):
        # Raise depos when enemies are nearby
        for depo in self.units(SUPPLYDEPOT).ready:
            for unit in self.known_enemy_units.not_structure:
                if unit.position.to2.distance_to(depo.position.to2) < 15:
                    break
            else:
                await self.do(depo(MORPH_SUPPLYDEPOT_LOWER))

        # Lower depos when no enemies are nearby
        for depo in self.units(SUPPLYDEPOTLOWERED).ready:
            for unit in self.known_enemy_units.not_structure:
                if unit.position.to2.distance_to(depo.position.to2) < 10:
                    await self.do(depo(MORPH_SUPPLYDEPOT_RAISE))
                    break

    # Attack with all Workers
    async def worker_attack(self):
        for worker in self.workers:
            await self.do(worker.attack(self.enemy_start_locations[0]))


run_game(maps.get("Simple64"), [
    Bot(Race.Terran, AlphaBot()),
    Computer(Race.Protoss, Difficulty.Easy)
], realtime=True)
