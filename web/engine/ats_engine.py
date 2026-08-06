"""
Engine ATS principal - análise completa com streaming de logs
"""
import re
import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.parsers import DocumentParser
from engine.logger import ATSLogger


@dataclass
class JobDescription:
    title: str
    company: str
    required_skills: List[str]
    preferred_skills: List[str]
    required_experience_years: int = 0
    education_level: str = ""
    responsibilities: List[str] = field(default_factory=list)


@dataclass
class ATSResult:
    candidate_name: str
    job_title: str
    overall_score: float
    skill_match_score: float
    experience_score: float
    education_score: float
    formatting_score: float
    semantic_score: float
    keyword_density_score: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    red_flags: List[str]
    recommendations: List[str]
    logs: List[Dict]
    raw_text: str = ""


class ATSEngine:
    """Motor ATS com análise completa e logs em tempo real"""

    def __init__(self):
        self.parser = DocumentParser()
        self.logger = None
        self.synonyms = {
            "python": ["py"], "javascript": ["js", "node.js", "nodejs"],
            "typescript": ["ts"], "react": ["reactjs"], "vue": ["vuejs"],
            "angular": ["angularjs"], "aws": ["amazon web services"],
            "docker": ["containerization"], "kubernetes": ["k8s"],
            "ci/cd": ["cicd", "github actions", "gitlab ci"],
            "machine learning": ["ml", "deep learning"],
            "sql": ["mysql", "postgresql", "sqlite"],
            "git": ["github", "gitlab"],
        }

    def analyze(self, file_path: str, job: JobDescription, log_callback=None) -> ATSResult:
        self.logger = ATSLogger()
        if log_callback:
            self.logger.add_callback(log_callback)

        self.parser.logger = self.logger

        # INGEST + PARSE
        parsed = self.parser.parse(file_path)
        raw_text = parsed["raw_text"]

        # EXTRACT
        contact = self._extract_contact(raw_text)
        self.logger.candidate_name = contact.get("name", "Desconhecido")

        self.logger.log("EXTRACT", "Entidades extraídas", {
            "name": contact.get("name"),
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "linkedin": contact.get("linkedin"),
        })

        # MATCH
        all_keywords = job.required_skills + job.preferred_skills
        matched, missing, match_details = self._match_keywords(raw_text, all_keywords)
        keyword_density = self._calc_keyword_density(raw_text, all_keywords)

        # SCORE
        skill_score = self._calc_skill_score(matched, job.required_skills, job.preferred_skills)
        exp_score = self._calc_experience_score(raw_text, job.required_experience_years)
        edu_score = self._calc_education_score(raw_text, job.education_level)
        fmt_score = self._calc_formatting_score(raw_text, parsed)
        sem_score = self._calc_semantic_score(raw_text, job.responsibilities)

        scores = {
            "skill_match": skill_score,
            "experience": exp_score,
            "education": edu_score,
            "formatting": fmt_score,
            "semantic": sem_score
        }
        overall = self._calc_overall(scores)

        # FILTER
        red_flags = self._detect_red_flags(raw_text, parsed, contact)
        self.logger.log("FILTER", "Red flags verificadas", {"count": len(red_flags), "flags": red_flags})

        # DECISION
        recommendations = self._generate_recommendations(overall, missing, red_flags, scores)
        self.logger.log("DECISION", "Análise concluída", {
            "overall_score": overall,
            "recommendation": "PASS" if overall >= 70 else "REVIEW" if overall >= 50 else "REJECT"
        })

        return ATSResult(
            candidate_name=contact.get("name", "Desconhecido"),
            job_title=job.title,
            overall_score=overall,
            skill_match_score=skill_score["score"],
            experience_score=exp_score["score"],
            education_score=edu_score["score"],
            formatting_score=fmt_score["score"],
            semantic_score=sem_score["score"],
            keyword_density_score=keyword_density["density"],
            matched_keywords=matched,
            missing_keywords=missing,
            red_flags=red_flags,
            recommendations=recommendations,
            logs=self.logger.to_dict(),
            raw_text=raw_text
        )

    def _extract_contact(self, text: str) -> Dict[str, Any]:
        contact = {}
        lines = [l.strip() for l in text.split('\n') if l.strip()][:5]
        for line in lines:
            if not re.search(r'[@+0-9]', line) and len(line.split()) <= 5 and len(line) > 3:
                if not any(k in line.lower() for k in ['curriculum', 'resume', 'cv']):
                    contact["name"] = line.strip()
                    break

        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            contact["email"] = email_match.group(0)

        phone_patterns = [
            r'(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:\d{4,5}[-.\s]?\d{4})',
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                contact["phone"] = match.group(0)
                break

        linkedin = re.search(r'linkedin\.com/in/[a-zA-Z0-9-]+', text, re.IGNORECASE)
        if linkedin:
            contact["linkedin"] = linkedin.group(0)

        return contact

    def _match_keywords(self, text: str, keywords: List[str]) -> tuple:
        text_lower = text.lower()
        matched, missing, details = [], [], {}

        for kw in keywords:
            kw_lower = kw.lower().strip()
            found = False

            if kw_lower in text_lower:
                found = True
            elif re.search(r'\b' + re.escape(kw_lower) + r'\b', text_lower):
                found = True
            elif kw_lower in self.synonyms:
                for syn in self.synonyms[kw_lower]:
                    if syn in text_lower:
                        found = True
                        break

            if found:
                matched.append(kw)
                details[kw] = {"found": True, "freq": text_lower.count(kw_lower)}
            else:
                missing.append(kw)
                details[kw] = {"found": False}

        self.logger.log("MATCH", f"Keywords: {len(matched)}/{len(keywords)} match", {
            "matched": matched, "missing": missing[:10]
        })
        return matched, missing, details

    def _calc_keyword_density(self, text: str, keywords: List[str]) -> Dict:
        words = re.findall(r'\b\w+\b', text.lower())
        total = len(words)
        mentions = sum(text.lower().count(k.lower()) for k in keywords)
        density = (mentions / total * 100) if total > 0 else 0
        self.logger.log("MATCH", "Densidade calculada", {"density": round(density, 2), "words": total})
        return {"density": round(density, 2), "total_words": total, "mentions": mentions}

    def _calc_skill_score(self, matched, required, preferred):
        req = len(set(matched) & set(required)) / len(required) * 100 if required else 0
        pref = len(set(matched) & set(preferred)) / len(preferred) * 50 if preferred else 0
        score = min(100, req + pref)
        self.logger.log("SCORE", "Skill score", {"score": round(score, 1), "req_match": req, "pref_match": pref})
        return {"score": round(score, 1), "weight": 0.35}

    def _calc_experience_score(self, text: str, required: int):
        patterns = [
            r'(\d+)\+?\s*anos?\s+de\s+experiência',
            r'(\d+)\+?\s*years?\s+of\s+experience',
            r'experiência\s+de\s+(\d+)',
        ]
        years = None
        for p in patterns:
            m = re.search(p, text.lower())
            if m:
                years = int(m.group(1))
                break

        if years and required:
            score = 100 if years >= required else max(20, (years/required)*100)
        else:
            score = 50

        self.logger.log("SCORE", "Experience score", {"score": round(score, 1), "years": years, "required": required})
        return {"score": round(score, 1), "weight": 0.25}

    def _calc_education_score(self, text: str, required: str):
        levels = {
            "ensino medio": 1, "high school": 1,
            "tecnico": 1, "technical": 1,  # técnico é nível médio, abaixo de superior
            "tecnologo": 2, "tecnólogo": 2,  # tecnólogo = superior (nível 2)
            "graduacao": 3, "bacharel": 3, "bachelor": 3, "bs": 3, "ba": 3, "licenciatura": 3,
            "pos": 4, "mestrado": 4, "master": 4, "ms": 4,
            "doutorado": 5, "phd": 5, "doctorate": 5
        }
        req = levels.get(required.lower(), 3)
        text_lower = text.lower()
        max_lvl = 0
        for term, val in levels.items():
            if term in text_lower:
                max_lvl = max(max_lvl, val)

        score = 100 if max_lvl >= req else (70 if max_lvl == req-1 else 40 if max_lvl > 0 else 0)
        self.logger.log("SCORE", "Education score", {"score": score, "level": max_lvl, "required": req})
        return {"score": score, "weight": 0.15}

    def _calc_formatting_score(self, text: str, parsed: Dict):
        score = 100
        issues = []
        if len(text) < 200:
            score -= 40; issues.append("PDF possivelmente imagem")
        if parsed["metadata"].get("is_image_pdf"):
            score -= 30; issues.append("PDF de imagem detectado")
        weird = len(re.findall(r'[^\w\s\n]', text))
        if weird > 20:
            score -= 10; issues.append("Caracteres estranhos")
        self.logger.log("SCORE", "Formatting score", {"score": max(0, score), "issues": issues})
        return {"score": max(0, score), "weight": 0.1}

    def _calc_semantic_score(self, text: str, responsibilities: List[str]):
        text_lower = text.lower()
        matches = 0
        for resp in responsibilities:
            words = re.findall(r'\b[a-z]{4,}\b', resp.lower())
            important = [w for w in words if w not in {"deve", "ser", "para", "will", "must"}]
            found = sum(1 for w in important if w in text_lower)
            if important and found / len(important) > 0.3:
                matches += 1

        score = (matches / len(responsibilities) * 100) if responsibilities else 50
        self.logger.log("SCORE", "Semantic score", {"score": round(score, 1), "matched": matches})
        return {"score": round(score, 1), "weight": 0.15}

    def _calc_overall(self, scores: Dict):
        total = sum(v["score"] * v["weight"] for v in scores.values())
        weight_sum = sum(v["weight"] for v in scores.values())
        overall = total / weight_sum if weight_sum > 0 else 0
        self.logger.log("SCORE", "Score final", {"overall": round(overall, 1), "components": {k: v["score"] for k, v in scores.items()}})
        return round(overall, 1)

    def _detect_red_flags(self, text: str, parsed: Dict, contact: Dict):
        flags = []
        if not contact.get("email"): flags.append("❌ Sem email")
        if not contact.get("phone"): flags.append("⚠️ Sem telefone")
        if len(text) < 500: flags.append("⚠️ CV muito curto")
        if len(text) > 15000: flags.append("⚠️ CV muito longo")
        if parsed["file_type"] == "pdf" and parsed["metadata"].get("is_image_pdf"):
            flags.append("🚨 PDF é imagem - texto não extraível")
        return flags

    def _generate_recommendations(self, overall, missing, flags, scores):
        recs = []
        if overall < 50: recs.append("🚨 Score baixo. Revisar CV completamente.")
        elif overall < 70: recs.append("⚠️ Score na faixa de revisão. Melhorias necessárias.")
        else: recs.append("✅ Score bom! CV bem otimizado.")
        if missing: recs.append(f"📌 Adicione keywords: {', '.join(missing[:10])}")
        if scores.get("formatting", {}).get("score", 100) < 70:
            recs.append("📝 Problemas de formatação detectados.")
        return recs
