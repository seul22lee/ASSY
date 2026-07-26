"""knowledge.cards — element card registry. Importing this package imports every card module
(one file per element, M18 refactor), which auto-registers it into base.CARD_REGISTRY."""

from knowledge.cards import base  # noqa: F401  (defines the ABCs + CARD_REGISTRY)
from knowledge.cards import pin_hinge  # noqa: F401
from knowledge.cards import snap_hook  # noqa: F401
from knowledge.cards import slide_rail  # noqa: F401
from knowledge.cards import rack_pinion  # noqa: F401
from knowledge.cards import pawl_detent  # noqa: F401
from knowledge.cards import stop_flange  # noqa: F401
from knowledge.cards import lead_screw  # noqa: F401
from knowledge.cards import coupling  # noqa: F401
from knowledge.cards import universal_joint  # noqa: F401
from knowledge.cards import journal_bearing  # noqa: F401
from knowledge.cards import bushing  # noqa: F401
from knowledge.cards import dowel_pin  # noqa: F401
from knowledge.cards import screw_boss  # noqa: F401
from knowledge.cards import press_fit  # noqa: F401

from knowledge.cards.base import CARD_REGISTRY, card_ports, is_passive  # noqa: F401,E402
