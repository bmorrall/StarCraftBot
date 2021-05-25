from abc import abstractmethod
import sc2
from sc2.constants import COMMANDCENTER, ORBITALCOMMAND, SUPPLYDEPOT, BARRACKS, FACTORY, REFINERY, STARPORT
from sc2.data import Target
from sc2.ids.unit_typeid import UnitTypeId

from sc2.position import Point2
from sc2.unit import Unit

from .structure_builder import RefineryBuilder, SupplyDepotBuilder, CommandCenterBuilder, \
    BarracksBuilder, FactoryBuilder, OrbitalCommandBuilder, StarportBuilder


class BuildingConstructor:
    def __init__(self, game: sc2.BotAI) -> None:
        self.game = game

        self.builders = {
            COMMANDCENTER: CommandCenterBuilder(game),
            ORBITALCOMMAND: OrbitalCommandBuilder(game),
            SUPPLYDEPOT: SupplyDepotBuilder(game),
            BARRACKS: BarracksBuilder(game),
            FACTORY: FactoryBuilder(game),
            REFINERY: RefineryBuilder(game),
            STARPORT: StarportBuilder(game)
        }

    async def on_step(self, iteration):
        if not self.game.units.of_type([COMMANDCENTER, ORBITALCOMMAND]):
            await self.rebuild_command_center()
            return  # There is no more build priority

        for builder in self.builders.values():
            await builder.on_step(iteration)

    async def rebuild_command_center(self):
        # Probably screwed at this point, but might as well keep things going
        if not self.game.already_pending(COMMANDCENTER) and self.game.can_afford(COMMANDCENTER):
            await self.game.build(COMMANDCENTER, self.game.start_location, max_distance=0, random_alternative=False)

    def set_build_target(self, unit_type: UnitTypeId, target: int):
        self.builders[unit_type].target = target
