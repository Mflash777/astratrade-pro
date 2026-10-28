from .base import Persona, PersonaOpinion, vote_from_score
from .fundamental_investor import FundamentalInvestor
from .macro_economist import MacroEconomist
from .optimizer import Optimizer
from .political_analyst import PoliticalAnalyst
from .quant_analyst import QuantAnalyst
from .risk_manager import RiskManager
from .sentiment_analyst import SentimentAnalyst

ANALYST_PERSONAS: list[type[Persona]] = [
    MacroEconomist, QuantAnalyst, FundamentalInvestor, PoliticalAnalyst, SentimentAnalyst, RiskManager,
]

__all__ = ["Persona", "PersonaOpinion", "vote_from_score", "ANALYST_PERSONAS", "Optimizer",
           "MacroEconomist", "QuantAnalyst", "FundamentalInvestor", "PoliticalAnalyst", "SentimentAnalyst", "RiskManager"]
