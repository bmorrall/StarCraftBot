from abc import abstractmethod

import sc2
from sc2 import units
from sc2.constants import COMMANDCENTER, ORBITALCOMMAND, BARRACKS, REFINERY, \
    SUPPLYDEPOT, SUPPLYDEPOTLOWERED, SUPPLYDEPOTDROP, \
    FACTORY
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class StructureBuilder:
    """ Builds Strucutres with each tick, ensuring the total is never exceeded """

    def __init__(self, game: sc2.BotAI, unit_type: UnitTypeId) -> None:
        self.unit_type = unit_type
        self.game = game

        self.pending_total = 0
        self.known_total = 0

    async def on_step(self, iteration):
        if not self.game.already_pending(self.unit_type):
            # No pending strucutres, so we should know the exact count
            self.pending_total = 0
            self.known_total = self.calculate_known_total
        elif self.pending_total:
            # Currently building units, but we can see how many structures have been placed
            current_total = self.game.units(self.unit_type).amount
            amount_created = max(current_total - self.known_total, 0)
            if amount_created:
                self.known_total = current_total
                self.pending_total = max(
                    self.pending_total - amount_created, 0)

        # Build a unit if we require one
        if self.should_build():
            err = await self.build_single()
            if err:
                self.debug(iteration, "Failed to build {}".format(
                    self.unit_type.name))
                return

            # Mark structure as pending
            self.pending_total += 1

            # Pring happy debug message
            self.debug(iteration, "{unit_type}({total})".format(
                unit_type=self.unit_type.name, total=self.estimated_total))

    # Build the single unit
    @abstractmethod
    async def build_single(self):
        pass

    # Override to control build
    def should_build(self) -> bool:
        return self.game.can_afford(self.unit_type)

    # Use the game logic to determine what we have build
    @property
    def calculate_known_total(self) -> int:
        return self.game.units(self.unit_type).amount

    # We cannot always know how many units we have pending,
    # keeps a summary based on what it thinks it has built
    @property
    def estimated_total(self) -> int:
        return self.known_total + self.pending_total

    def debug(self, iteration, message):
        print(iteration, "{}/{}".format(self.game.supply_used,
              self.game.supply_cap), message)


class SupplyDepotBuilder(StructureBuilder):
    """ Builds Supply Depots as required """

    def __init__(self, game: sc2.BotAI) -> None:
        super().__init__(game, SUPPLYDEPOT)

    @property
    def known_depots(self) -> Units:
        return self.game.units.of_type([SUPPLYDEPOT, SUPPLYDEPOTLOWERED, SUPPLYDEPOTDROP])

    @property
    def calculate_known_total(self) -> int:
        return self.known_depots.amount

    def should_build(self) -> bool:
        return super().should_build() and \
            (self.game.supply_left < 5 or not self.known_total or self.game.supply_cap > 50) and \
            self.pending_building < self.threshold and \
            self.game.supply_cap < 200

    async def build_single(self):
        return await self.game.build(self.unit_type, near=self.next_location())

    def next_location(self) -> Point2:
        # Find all urgently required depot locations
        depot_placement_positions = self.game.main_base_ramp.corner_depots
        depots = self.known_depots
        if depots:
            depot_placement_positions = {
                d for d in depot_placement_positions if depots.closest_distance_to(d) > 1}

        # Urgently build supply depots (anti-cheese)
        if len(depot_placement_positions) > 0:
            return depot_placement_positions.pop()

        # Build any other supply depots as needed
        map_center = self.game.game_info.map_center
        return self.game.units.of_type([COMMANDCENTER, ORBITALCOMMAND]).random.position.towards(map_center, 8)

    @property
    def pending_building(self) -> int:
        # return self.pending_total + self.known_depots.not_ready.amount
        return self.game.already_pending(SUPPLYDEPOT)

    @property
    def threshold(self) -> int:
        if self.game.supply_cap > 100:
            return 2
        return 1


class QuotaStructureBuilder(StructureBuilder):
    """ Builds Buildings up to a set Quota """

    def __init__(self, game: sc2.BotAI, unit_type: UnitTypeId, target: int = 0) -> None:
        super().__init__(game, unit_type)

        self._target = target

    def should_build(self):
        return super().should_build() and self._target > self.estimated_total

    async def build_single(self):
        return await self.game.build(self.unit_type, near=self.next_location())

    @abstractmethod
    def next_location(self) -> Point2:
        pass

    @property
    def target(self) -> int:
        return self._target

    @target.setter
    def target(self, target: int):
        self._target = target


class CommandCenterBuilder(QuotaStructureBuilder):
    def __init__(self, game: sc2.BotAI, target: int = 1) -> None:
        super().__init__(game, COMMANDCENTER, target=target)

    @property
    def calculate_known_total(self) -> int:
        return self.game.units.of_type([COMMANDCENTER, ORBITALCOMMAND]).amount

    async def build_single(self):
        return await self.game.expand_now()


class OrbitalCommandBuilder(QuotaStructureBuilder):
    def __init__(self, game: sc2.BotAI) -> None:
        super().__init__(game, ORBITALCOMMAND)

    def should_build(self):
        return super().should_build() and \
            self.game.can_afford(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND) and \
            self.game.units(COMMANDCENTER).ready.idle and \
            self.game.units(BARRACKS).ready

    async def build_single(self):
        for cc in self.game.units(COMMANDCENTER).ready.idle:
            return await self.game.do(cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND))

        return True


class RefineryBuilder(QuotaStructureBuilder):
    def __init__(self, game: sc2.BotAI) -> None:
        super().__init__(game, REFINERY)

    async def build_single(self):
        # Build a refinery on the first vacant geyser
        for cc in self.game.units.of_type([COMMANDCENTER, ORBITALCOMMAND]).ready:
            vespenes = self.game.state.vespene_geyser.closer_than(25.0, cc)
            for vespene in vespenes:
                if self.game.units(REFINERY).closer_than(distance=1, position=vespene.position):
                    # Already building a refinery on this geyser
                    continue

                worker = self.game.select_build_worker(vespene.position)
                if worker is None:
                    break

                return await self.game.do(worker.build(REFINERY, vespene))

        # No refinery built
        return True


class BarracksBuilder(QuotaStructureBuilder):
    def __init__(self, game: sc2.BotAI) -> None:
        super().__init__(game, BARRACKS)

    def should_build(self):
        return super().should_build() and self.game.units.of_type([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.SUPPLYDEPOTDROP]).ready

    def next_location(self) -> Point2:
        if self.known_total:
            return self.game.units(BARRACKS).first
        # Wall off the base
        return self.game.main_base_ramp.barracks_in_middle


class FactoryBuilder(QuotaStructureBuilder):
    def __init__(self, game: sc2.BotAI) -> None:
        super().__init__(game, FACTORY)

    def should_build(self):
        return super().should_build() and self.game.units(BARRACKS)

    def next_location(self) -> Point2:
        # Building near the most recently created Barracks
        return self.game.units(BARRACKS).first
