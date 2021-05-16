import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import COMMANDCENTER, SCV, SUPPLYDEPOT


class AlphaBot(sc2.BotAI):
    async def on_step(self, iteration):
        await self.distribute_workers()  # in sc2/bot_ai.py
        await self.build_workers()
        await self.build_supply_depot()
        await self.expand()

    async def build_workers(self):
        for command_center in self.units(COMMANDCENTER).idle:
            if self.can_afford(SCV) and self.workers.amount < 16 and command_center.noqueue:
                await self.do(command_center.train(SCV))

    async def build_supply_depot(self):
        if self.supply_left < 5 and not self.already_pending(SUPPLYDEPOT):
            command_centers = self.units(COMMANDCENTER).ready
            if command_centers.exists:
                if self.can_afford(SUPPLYDEPOT):
                    await self.build(SUPPLYDEPOT, near=command_centers.first)

    async def expand(self):
        if self.units(COMMANDCENTER).amount < 2 and self.can_afford(COMMANDCENTER):
            await self.expand_now()

    # Attack with all Workers
    async def worker_attack(self):
        for worker in self.workers:
            await self.do(worker.attack(self.enemy_start_locations[0]))


run_game(maps.get("Simple64"), [
    Bot(Race.Terran, AlphaBot()),
    Computer(Race.Protoss, Difficulty.Easy)
], realtime=True)
