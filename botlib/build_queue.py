
from sc2.constants import COMMANDCENTER, SCV, SUPPLYDEPOT, BARRACKS, MARINE, \
    REFINERY, FACTORY, HELLION, REAPER, ORBITALCOMMAND
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units

from .building_constructor import BuildingConstructor


class BuildStep:
    TYPE_LOOKUP = {
        COMMANDCENTER: [COMMANDCENTER, ORBITALCOMMAND]
    }

    def __init__(self, unit_type: UnitTypeId, count: int) -> None:
        self.unit_type = unit_type
        self.count = count
        print(unit_type, count)

    def is_complete(self, units):
        return units.of_type(BuildStep.TYPE_LOOKUP.get(self.unit_type, [self.unit_type])).amount >= self.count

    def update_build_target(self, building_constructor: BuildingConstructor):
        building_constructor.set_build_target(self.unit_type, self.count)


class BuildQueue:
    def __init__(self) -> None:
        self.build_steps = []

    # Adds increment to the number of desired unit_type
    def add_step(self, unit_type: UnitTypeId, increment: int):
        count = 0
        for build_step in self.build_steps:
          if build_step.unit_type == unit_type:
            count = build_step.count # Use highest count

        self.build_steps.append(BuildStep(unit_type, count + increment))

    async def on_step(self, units: Units, building_constructor: BuildingConstructor):
        for step in self.build_steps:
            if not step.is_complete(units):
                step.update_build_target(building_constructor)
                return
