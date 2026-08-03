"""
SpacyPdfParser - Adapter concreto que implementa ParserPort
"""
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import spacy

from domain.entities import (
    Education, Experience, ParseResult, ParseWarning, Resume,
    Skill, WarningSeverity
)
from infrastructure.pdf_extractor import PdfTextExtractor
from infrastructure.date_parser import BrazilianDateParser
from infrastructure.section_detector import SectionDetector
from infrastructure.skill_normalizer import SkillNormalizer


class SpacyPdfParser:
    def __init__(self, model_name: str = "pt_core_news_lg"):
        self.extractor = PdfTextExtractor()
        self.date_parser = BrazilianDateParser()
        self.section_detector = SectionDetector()
        self.skill_normalizer = SkillNormalizer()
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            try:
                self.nlp = spacy.load("pt_core_news_sm")
            except OSError:
                raise RuntimeError(
                    "Modelo spaCy pt_core_news não encontrado. "
                    "Execute: python -m spacy download pt_core_news_lg"
                )
        self.email_pattern = re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )
        self.phone_pattern = re.compile(
            r"(?:\+55\s*)?(?:\(?\d{2}\)?[\s.-]?)?(?:\d{4,5}[\s.-]?\d{4})"
        )

    def parse(self, file_path: str) -> ParseResult:
        warnings = []
        raw_text = ""
        try:
            raw_text, extraction_warnings = self.extractor.extract(file_path)
            for w in extraction_warnings:
                warnings.append(
                    ParseWarning(
                        severity=WarningSeverity(w["severity"]),
                        field=w["field"],
                        message=w["message"]
                    )
                )
        except Exception as e:
            warnings.append(
                ParseWarning(
                    severity=WarningSeverity.CRITICAL,
                    field="extraction",
                    message=f"Falha na extração: {str(e)}"
                )
            )
            return self._build_result(None, warnings, 0.0)
        normalized_text = self.extractor.normalize_text(raw_text)
        resume = Resume(raw_text=normalized_text)
        try:
            doc = self.nlp(normalized_text)
        except Exception as e:
            warnings.append(
                ParseWarning(
                    severity=WarningSeverity.CRITICAL,
                    field="nlp",
                    message=f"Falha no processamento NLP: {str(e)}"
                )
            )
            return self._build_result(resume, warnings, 0.0)
        resume.full_name = self._extract_name(doc, normalized_text)
        resume.email = self._extract_email(normalized_text)
        resume.phone = self._extract_phone(normalized_text)
        resume.city, resume.state = self._extract_location(doc)
        sections = self.section_detector.detect(normalized_text)
        resume.summary = self._extract_section_content(sections.get("summary", []))
        resume.objective = self._extract_section_content(sections.get("summary", []))
        resume.experiences = self._parse_experiences(
            sections.get("experience", []), normalized_text
        )
        resume.education = self._parse_education(
            sections.get("education", []), normalized_text
        )
        resume.skills = self._extract_all_skills(sections, normalized_text)
        resume.total_experience_months = self._calculate_total_experience(
            resume.experiences
        )
        confidence = self._calculate_confidence(resume, warnings)
        return self._build_result(resume, warnings, confidence)

    def _extract_name(self, doc, text: str) -> Optional[str]:
        for ent in doc.ents:
            if ent.label_ == "PER" and ent.start_char < len(text) * 0.15:
                name = ent.text.strip()
                if len(name.split()) >= 2 and len(name) > 5:
                    return name
        lines = text.split("\n")
        for line in lines[:5]:
            stripped = line.strip()
            words = stripped.split()
            if 2 <= len(words) <= 4 and not any(c.isdigit() for c in stripped):
                if len(stripped) > 5 and "@" not in stripped:
                    return stripped
        return None

    def _extract_email(self, text: str) -> Optional[str]:
        match = self.email_pattern.search(text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        match = self.phone_pattern.search(text)
        return match.group(0) if match else None

    def _extract_location(self, doc) -> Tuple[Optional[str], Optional[str]]:
        cities = []
        states = []
        for ent in doc.ents:
            if ent.label_ in ("LOC", "GPE"):
                text = ent.text.strip()
                if re.match(r"^[A-Z]{2}$", text):
                    states.append(text)
                elif len(text) > 2:
                    cities.append(text)
        return (cities[0] if cities else None, states[0] if states else None)

    def _extract_section_content(self, lines: List[str]) -> Optional[str]:
        if not lines:
            return None
        content_lines = []
        for line in lines[1:]:
            if len(line) > 10:
                content_lines.append(line)
        return " ".join(content_lines) if content_lines else None

    def _parse_experiences(self, section_lines: List[str], full_text: str) -> List[Experience]:
        if not section_lines:
            return self._parse_experiences_from_text(full_text)
        content = "\n".join(section_lines[1:])
        return self._parse_experiences_from_text(content)

    def _parse_experiences_from_text(self, text: str) -> List[Experience]:
        experiences = []
        lines = text.split("\n")
        current_exp: Dict[str, Any] = {}
        current_desc = []
        for line in lines:
            line = line.strip()
            if not line:
                if current_exp:
                    current_exp["description"] = " ".join(current_desc)
                    experiences.append(self._build_experience(current_exp))
                    current_exp = {}
                    current_desc = []
                continue
            date_match = re.search(
                r"(\w{3,}\.?\s*\/?\s*\d{4}.*?(?:atual(?:mente)?|presente|\d{4}))",
                line, re.IGNORECASE
            )
            if date_match and not current_exp:
                current_exp["date_str"] = date_match.group(1)
                prefix = line[:date_match.start()].strip()
                if prefix:
                    current_exp["header"] = prefix
            elif date_match and current_exp:
                current_exp["description"] = " ".join(current_desc)
                experiences.append(self._build_experience(current_exp))
                current_exp = {"date_str": date_match.group(1)}
                prefix = line[:date_match.start()].strip()
                if prefix:
                    current_exp["header"] = prefix
                current_desc = []
            elif current_exp:
                current_desc.append(line)
            elif len(line) > 10 and not any(c.isdigit() for c in line):
                current_exp["header"] = line
        if current_exp:
            current_exp["description"] = " ".join(current_desc)
            experiences.append(self._build_experience(current_exp))
        return [e for e in experiences if e is not None]

    def _build_experience(self, exp_dict: Dict[str, Any]) -> Optional[Experience]:
        if not exp_dict:
            return None
        date_str = exp_dict.get("date_str", "")
        start_date, end_date, is_current = self.date_parser.parse(date_str)
        header = exp_dict.get("header", "")
        company = None
        role = None
        if header:
            parts = header.split(" - ")
            if len(parts) >= 2:
                company = parts[0].strip()
                role = parts[1].strip()
            else:
                doc = self.nlp(header)
                orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
                if orgs:
                    company = orgs[0]
                    role = header.replace(company, "").strip(" -|")
                else:
                    company = header
        duration = self.date_parser.calculate_duration(start_date, end_date, is_current)
        return Experience(
            company=company,
            role=role,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            description=exp_dict.get("description"),
            duration_months=duration
        )

    def _parse_education(self, section_lines: List[str], full_text: str) -> List[Education]:
        education = []
        if not section_lines:
            return education
        content = "\n".join(section_lines[1:])
        lines = content.split("\n")
        current_edu: Dict[str, Any] = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_edu:
                    education.append(self._build_education(current_edu))
                    current_edu = {}
                continue
            degree_patterns = [
                r"(bacharelado|licenciatura|tecnólogo|mestrado|doutorado|mba|pós[-\s]?graduação)",
                r"(graduação|graduado|formado)",
            ]
            has_degree = any(re.search(p, line, re.IGNORECASE) for p in degree_patterns)
            if has_degree or (current_edu and len(line) > 15):
                if "degree" not in current_edu:
                    current_edu["degree"] = line
                else:
                    current_edu["institution"] = line
            elif not current_edu:
                current_edu["institution"] = line
        if current_edu:
            education.append(self._build_education(current_edu))
        return education

    def _build_education(self, edu_dict: Dict[str, Any]) -> Education:
        return Education(
            institution=edu_dict.get("institution"),
            degree=edu_dict.get("degree"),
            field_of_study=None
        )

    def _extract_all_skills(self, sections: Dict[str, List[str]], full_text: str) -> List[Skill]:
        all_skills = []
        seen = set()
        skills_text = " ".join(sections.get("skills", []))
        for skill in self.skill_normalizer.extract_skills(skills_text, "lista"):
            key = skill["normalized"]
            if key not in seen:
                seen.add(key)
                all_skills.append(Skill(
                    name=skill["name"],
                    normalized=skill["normalized"],
                    context="lista"
                ))
        exp_text = " ".join(sections.get("experience", []))
        for skill in self.skill_normalizer.extract_skills(exp_text, "experiência"):
            key = skill["normalized"]
            if key not in seen:
                seen.add(key)
                all_skills.append(Skill(
                    name=skill["name"],
                    normalized=skill["normalized"],
                    context="experiência"
                ))
        edu_text = " ".join(sections.get("education", []))
        for skill in self.skill_normalizer.extract_skills(edu_text, "formação"):
            key = skill["normalized"]
            if key not in seen:
                seen.add(key)
                all_skills.append(Skill(
                    name=skill["name"],
                    normalized=skill["normalized"],
                    context="formação"
                ))
        return all_skills

    def _calculate_total_experience(self, experiences: List[Experience]) -> int:
        total = 0
        for exp in experiences:
            if exp.duration_months:
                total += exp.duration_months
        return total

    def _calculate_confidence(self, resume: Resume, warnings: List[ParseWarning]) -> float:
        score = 0.5
        if resume.full_name:
            score += 0.1
        if resume.email:
            score += 0.1
        if resume.phone:
            score += 0.05
        if resume.experiences:
            score += 0.1
        if resume.skills:
            score += 0.05
        if resume.education:
            score += 0.05
        warning_penalty = sum(
            0.1 if w.severity == WarningSeverity.WARNING else
            0.2 if w.severity == WarningSeverity.CRITICAL else 0
            for w in warnings
        )
        score -= warning_penalty
        return max(0.0, min(1.0, score))

    def _build_result(self, resume: Optional[Resume], warnings: List[ParseWarning], confidence: float) -> ParseResult:
        if resume is None:
            resume = Resume()
        return ParseResult(
            resume=resume,
            confidence_score=confidence,
            warnings=warnings
        )
