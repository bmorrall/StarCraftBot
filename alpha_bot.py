import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer

class AlphaBot(sc2.BotAI):
    async def on_step(self, iteration):
        if iteration == 0:
            await self.worker_attack();

    # Attack with all Workers
    async def worker_attack(self):
        for worker in self.workers:
            await self.do(worker.attack(self.enemy_start_locations[0]))

run_game(maps.get("Simple64"), [
    Bot(Race.Terran, AlphaBot()),
    Computer(Race.Protoss, Difficulty.Easy)
], realtime=True)
