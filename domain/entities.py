"""
Domain Layer - Entidades puras e Ports (interfaces abstratas)
Nenhuma dependência externa permitida nesta camada.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional, Protocol


class WarningSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ParseWarning:
    severity: WarningSeverity
    field: str
    message: str


@dataclass
class Skill:
    name: str
    context: str = ""
    normalized: Optional[str] = None


@dataclass
class Experience:
    company: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    description: Optional[str] = None
    duration_months: Optional[int] = None


@dataclass
class Education:
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False


@dataclass
class Resume:
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    summary: Optional[str] = None
    objective: Optional[str] = None
    experiences: List[Experience] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    skills: List[Skill] = field(default_factory=list)
    total_experience_months: Optional[int] = None
    raw_text: Optional[str] = None


@dataclass
class ParseResult:
    resume: Resume
    confidence_score: float = 0.0
    warnings: List[ParseWarning] = field(default_factory=list)
    is_usable: bool = False

    def __post_init__(self):
        has_critical = any(
            w.severity == WarningSeverity.CRITICAL for w in self.warnings
        )
        self.is_usable = not has_critical and self.confidence_score >= 0.5


class ParserPort(Protocol):
    def parse(self, file_path: str) -> ParseResult:
        ...
