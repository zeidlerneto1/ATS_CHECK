import pytest
from datetime import date

from domain.entities import (
    Resume, Experience, Skill, ParseResult, ParseWarning, WarningSeverity
)


class TestParseResult:
    def test_parse_result_with_critical_warning_is_not_usable(self):
        resume = Resume()
        warnings = [
            ParseWarning(
                severity=WarningSeverity.CRITICAL,
                field="extraction",
                message="Falha crítica"
            )
        ]
        result = ParseResult(resume=resume, confidence_score=0.9, warnings=warnings)
        assert result.is_usable is False

    def test_parse_result_with_high_confidence_is_usable(self):
        resume = Resume(full_name="João Silva", email="joao@teste.com")
        result = ParseResult(resume=resume, confidence_score=0.8, warnings=[])
        assert result.is_usable is True

    def test_parse_result_with_low_confidence_is_not_usable(self):
        resume = Resume()
        result = ParseResult(resume=resume, confidence_score=0.3, warnings=[])
        assert result.is_usable is False

    def test_parse_result_with_warning_but_high_confidence_is_usable(self):
        resume = Resume(full_name="João Silva")
        warnings = [
            ParseWarning(
                severity=WarningSeverity.WARNING,
                field="phone",
                message="Telefone não encontrado"
            )
        ]
        result = ParseResult(resume=resume, confidence_score=0.7, warnings=warnings)
        assert result.is_usable is True


class TestResumeEntity:
    def test_resume_default_values(self):
        resume = Resume()
        assert resume.full_name is None
        assert resume.experiences == []
        assert resume.skills == []
        assert resume.total_experience_months is None

    def test_resume_with_data(self):
        exp = Experience(company="Tech BR", role="Dev", duration_months=24)
        skill = Skill(name="Python", normalized="python", context="experiência")
        resume = Resume(
            full_name="Maria Oliveira",
            email="maria@teste.com",
            experiences=[exp],
            skills=[skill]
        )
        assert resume.full_name == "Maria Oliveira"
        assert len(resume.experiences) == 1
        assert resume.skills[0].normalized == "python"
