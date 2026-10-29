from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    """Supported claim categories for TruthLens verification."""
    FACTUAL = "FACTUAL"
    NUMERICAL = "NUMERICAL"
    TEMPORAL = "TEMPORAL"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    PERSON_ORGANIZATION = "PERSON/ORGANIZATION"
    POLICY = "POLICY"
    CAUSAL = "CAUSAL"
    COMPARATIVE = "COMPARATIVE"
    QUOTE_ATTRIBUTION = "QUOTE/ATTRIBUTION"
    OPINION = "OPINION"
    NON_VERIFIABLE = "NON_VERIFIABLE"


class Verifiability(str, Enum):
    """Whether a statement can be objectively evaluated against evidence."""
    VERIFIABLE = "VERIFIABLE"
    UNVERIFIABLE = "UNVERIFIABLE"
    SUBJECTIVE = "SUBJECTIVE"


class Importance(str, Enum):
    """Extraction priority for subsequent verification scheduling."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExtractedClaimItem(BaseModel):
    """Structured representation of an individual extracted atomic claim."""
    id: str = Field(..., description="Unique claim identifier within the extraction session")
    text: str = Field(..., description="Atomic claim assertion")
    normalized_text: str = Field(..., description="Canonical whitespace-cleaned representation")
    claim_type: ClaimType = Field(default=ClaimType.FACTUAL, description="Classified claim category")
    verifiability: Verifiability = Field(default=Verifiability.VERIFIABLE, description="Objective verifiability rating")
    importance: Importance = Field(default=Importance.MEDIUM, description="Extraction priority")
    entities: List[str] = Field(default_factory=list, description="Extracted named entities")
    dates: List[str] = Field(default_factory=list, description="Extracted dates or time frames")
    locations: List[str] = Field(default_factory=list, description="Extracted geographic locations")
    numbers: List[str] = Field(default_factory=list, description="Extracted percentages, currencies, or quantities")
    source_attributions: List[str] = Field(default_factory=list, description="Entities to which the statement is attributed")
    original_sentence: str = Field(..., description="The original sentence from which this claim was extracted")
    extraction_method: str = Field(default="rule_based", description="Extraction technique: rule_based, llm, or hybrid")
