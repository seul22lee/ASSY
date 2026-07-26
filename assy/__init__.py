"""ASSY-Next: a general mechanical design framework.

Natural-language requirements -> structured engineering intent -> mechanical and
product architecture -> engineering integration -> deterministic CAD ->
simulation -> requirement evaluation -> revision.
"""

from assy.pipeline import Pipeline, PipelineResult, StageRecord

__version__ = "0.1.0"
__all__ = ["Pipeline", "PipelineResult", "StageRecord"]
