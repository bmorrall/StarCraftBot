import math

import sc2
from sc2.constants import COMMANDCENTER, ORBITALCOMMAND, REFINERY, SCV, SUPPLYDEPOT


class BuildInfo:
    """Build Strategies for Games."""

    def __init__(self, game: sc2.BotAI):
        # create the instance
        self.game = game

    @property
    def workers_wanted(self) -> bool:
        existing_scvs = self.game.units(
            SCV).amount + self.game.already_pending(SCV)
        target_scvs = self._target_workers
        if existing_scvs >= target_scvs:
            return 0
        return target_scvs - existing_scvs

    @property
    def supply_wanted(self) -> bool:
        # The more units we have, the quicker we reach capacity
        build_capacity = math.floor(self.game.supply_used / 100) + 1

        if not self.game.units.of_type([COMMANDCENTER, ORBITALCOMMAND]).ready or self.game.supply_cap == self.game.supply_used:
            # Ensure we save money for a new command center
            return 0
        elif self.game.units(SUPPLYDEPOT).amount + self.game.already_pending(SUPPLYDEPOT) < 2:
            # Rush to wall off base
            return 1
        elif self.game.supply_left < (5 * build_capacity):
            return max(build_capacity - self.game.already_pending(SUPPLYDEPOT), 0)

        return 0

    @property
    def _target_workers(self):
        ideal = 1  # one for construction
        for cc in self.game.units.of_type([COMMANDCENTER, ORBITALCOMMAND]):
            ideal += cc.ideal_harvesters
        # Add pending command center units count
        ideal += self.game.already_pending(COMMANDCENTER) * 8
        # Add refinery counts
        ideal += self.game.units(REFINERY).amount * 3
        return ideal
