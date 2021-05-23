import sc2
from sc2.constants import COMMANDCENTER, ORBITALCOMMAND, SCV
from sc2.constants import SUPPLYDEPOT, SUPPLYDEPOTLOWERED, MORPH_SUPPLYDEPOT_LOWER, MORPH_SUPPLYDEPOT_RAISE

from .build_info import BuildInfo
from .building_constructor import BuildingConstructor


class TerranBot(sc2.BotAI):
    def __init__(self):
        super().__init__()
        self.build_info = BuildInfo(self)
        self.building_constructor = BuildingConstructor(self)

    async def on_step(self, iteration: int):
        await self.raise_lower_depots()

        await self.building_constructor.on_step(iteration)

    async def train_workers(self):
        workers_wanted = self.build_info.workers_wanted
        for cc in self.units.of_type([COMMANDCENTER, ORBITALCOMMAND]).ready.idle:
            if workers_wanted > 0 and self.can_afford(SCV):
                workers_wanted -= 1
                await self.do(cc.train(SCV))

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
