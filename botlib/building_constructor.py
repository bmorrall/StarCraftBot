from abc import abstractmethod
import sc2
from sc2.constants import COMMANDCENTER, SUPPLYDEPOT, BARRACKS, REFINERY
from sc2.data import Target
from sc2.ids.unit_typeid import UnitTypeId

from sc2.position import Point2
from sc2.unit import Unit

from .structure_builder import RefineryBuilder, SupplyDepotBuilder, CommandCenterBuilder, \
    BarracksBuilder, FactoryBuilder


class BuildingConstructor:
    def __init__(self, game: sc2.BotAI) -> None:
        self.game = game

        self.command_center_builder = CommandCenterBuilder(game)
        self.supply_depot_builder = SupplyDepotBuilder(game)
        self.barracks_builder = BarracksBuilder(game)
        self.factory_builder = FactoryBuilder(game)
        self.refinery_builder = RefineryBuilder(game)

    async def on_step(self, iteration):
        if not self.game.units(COMMANDCENTER):
            await self.rebuild_command_center()
            return  # There is no more build priority

        await self.command_center_builder.on_step(iteration)
        await self.supply_depot_builder.on_step(iteration)
        await self.barracks_builder.on_step(iteration)
        await self.factory_builder.on_step(iteration)
        await self.refinery_builder.on_step(iteration)

    def set_command_center_target(self, command_center_target: int):
        self.command_center_builder.target = command_center_target

    def set_barracks_target(self, barracks_target: int):
        self.barracks_builder.target = barracks_target

    def set_factory_target(self, factory_target: int):
        self.factory_builder.target = factory_target

    def set_refinery_target(self, refinery_target: int):
        self.refinery_builder.target = refinery_target

    async def rebuild_command_center(self):
        # Probably screwed at this point, but might as well keep things going
        if not self.game.already_pending(COMMANDCENTER) and self.game.can_afford(COMMANDCENTER):
            await self.game.build(COMMANDCENTER, self.game.start_location, max_distance=0, random_alternative=False)
