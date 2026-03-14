"""agents — AI Civilization OS の6専門エージェント"""
from agents.historian import HistorianAgent
from agents.scientist import ScientistAgent
from agents.economist import EconomistAgent
from agents.strategist import StrategistAgent
from agents.builder import BuilderAgent
from agents.auditor import AuditorAgent

__all__ = [
    "HistorianAgent",
    "ScientistAgent",
    "EconomistAgent",
    "StrategistAgent",
    "BuilderAgent",
    "AuditorAgent",
]

ALL_AGENTS = {
    "historian": HistorianAgent,
    "scientist": ScientistAgent,
    "economist": EconomistAgent,
    "strategist": StrategistAgent,
    "builder": BuilderAgent,
    "auditor": AuditorAgent,
}
