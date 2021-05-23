from pathlib import Path
__all__ = [p.stem for p in Path().iterdir() if p.is_file() and p.suffix == ".py" and p.stem != "__init__"]

import sys, logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

from .build_info import BuildInfo
from .building_constructor import BuildingConstructor
from .terran_bot import *
