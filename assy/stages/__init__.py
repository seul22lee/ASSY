"""Pipeline stages. One engineering question each (Rule A-1)."""

from assy.stages.base import DeterministicReasoner, PipelineStage, Reasoner, StageError
from assy.stages.s01_llm import LLMRequirementInterpreter
from assy.stages.s01_requirement import IncompleteRequirementProducer
from assy.stages.s02_mechanical import MechanicalArchitectureGenerator
from assy.stages.s03_product import ProductArchitecturePlanner
from assy.stages.s04_concept import ConceptVisualizer
from assy.stages.s05_engineering import Budget, EngineeringIntegration
from assy.stages.s06_solver import ParametricSolver
from assy.stages.s07_cad import CADBuilder
from assy.stages.s08_simplan import SimulationPlanBuilder
from assy.stages.s09_simrun import SimulationRunner
from assy.stages.s10_metrics import MetricExtraction
from assy.stages.s11_evaluate import RequirementEvaluation
from assy.stages.s12_revision import RevisionRouting

__all__ = [
    "Budget",
    "CADBuilder",
    "ConceptVisualizer",
    "DeterministicReasoner",
    "EngineeringIntegration",
    "MechanicalArchitectureGenerator",
    "MetricExtraction",
    "ParametricSolver",
    "PipelineStage",
    "ProductArchitecturePlanner",
    "Reasoner",
    "RequirementEvaluation",
    "IncompleteRequirementProducer",
    "LLMRequirementInterpreter",
    "RevisionRouting",
    "SimulationPlanBuilder",
    "SimulationRunner",
    "StageError",
]
