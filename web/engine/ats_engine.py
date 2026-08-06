"""
Engine ATS principal - Onda 1: Fundação
- Metadados DOCX (core.xml)
- Peso por seção (Resumo 1.5x, Experiência 1.3x, Projetos 1.1x, Educação 0.9x, Skills 0.8x)
- Date parser MM/AAAA, DD/MM/AAAA
- Educação: Tecnólogo = nível 2 (superior)
- Parser de experiências robusto
"""
import re
import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.parsers import DocumentParser
from engine.logger import ATSLogger
from engine.date_parser import DateParser

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
    """Motor ATS com análise completa e logs em tempo real — Onda 1"""

    # Pesos por seção segundo o manual ATS Engineer (Cap. 5)
    SECTION_WEIGHTS = {
        "resumo": 1.5,
        "experiencia": 1.3,
        "experiência": 1.3,
        "projetos": 1.1,
        "portfolio": 1.1,
        "educacao": 0.9,
        "educação": 0.9,
        "formacao": 0.9,
        "formação": 0.9,
        "skills": 0.8,
        "habilidades": 0.8,
    }

    # Níveis educacionais (Cap. 6 do manual)
    EDUCATION_LEVELS = {
        "ensino medio": 1, "high school": 1, "medio": 1,
        "tecnico": 1, "técnico": 1, "technical": 1,
        "tecnologo": 2, "tecnólogo": 2, "tecnologa": 2, "tecnóloga": 2,
        "graduacao": 3, "graduação": 3, "bacharel": 3, "bacharelado": 3,
        "bachelor": 3, "bs": 3, "ba": 3, "licenciatura": 3,
        "pos": 4, "pós": 4, "mestrado": 4, "master": 4, "ms": 4,
        "doutorado": 5, "phd": 5, "doctorate": 5,
    }

    def __init__(self):
        self.parser = DocumentParser()
        self.logger = None
        self.date_parser = DateParser()
        self.synonyms = {
            "python": ["py"], "javascript": ["js", "node.js", "nodejs"],
            "typescript": ["ts"], "react": ["reactjs", "react.js"],
            "vue": ["vuejs", "vue.js"], "angular": ["angularjs"],
            "aws": ["amazon web services", "amazon web service"],
            "docker": ["containerization", "container"],
            "kubernetes": ["k8s", "kube"],
            "ci/cd": ["cicd", "github actions", "gitlab ci", "continuous integration"],
            "machine learning": ["ml", "deep learning", "dl"],
            "sql": ["mysql", "postgresql", "sqlite", "postgres"],
            "git": ["github", "gitlab", "version control"],
            "node.js": ["nodejs", "node"],
            "express": ["express.js"],
            "rest": ["restful", "rest api", "restful api", "apis rest"],
            "jwt": ["json web token", "token jwt"],
            "rbac": ["role based access control", "controle de acesso"],
        }
        self._debug_data = {
            "contact": {}, "parsed_metadata": {}, "keyword_details": {},
            "score_components": {}, "experience_years_detected": None,
            "education_level_detected": 0, "sections_found": [],
            "section_scores": {},
        }

    def get_debug_data(self) -> Dict[str, Any]:
        return self._debug_data

    def analyze(self, file_path: str, job: JobDescription, log_callback=None) -> ATSResult:
        self.logger = ATSLogger()
        if log_callback:
            self.logger.add_callback(log_callback)

        self.parser.logger = self.logger
        self._debug_data = {
            "contact": {}, "parsed_metadata": {}, "keyword_details": {},
            "score_components": {}, "experience_years_detected": None,
            "education_level_detected": 0, "sections_found": [],
            "section_scores": {},
        }

        # INGEST + PARSE
        parsed = self.parser.parse(file_path)
        raw_text = parsed["raw_text"]
        metadata = parsed.get("metadata", {})
        self._debug_data["parsed_metadata"] = metadata

        # Detectar seções e aplicar pesos
        sections = self._detect_sections(raw_text)
        self._debug_data["sections_found"] = list(sections.keys())

        # EXTRACT
        contact = self._extract_contact(raw_text)
        self._debug_data["contact"] = contact
        self.logger.candidate_name = contact.get("name", "Desconhecido")

        self.logger.log("EXTRACT", "Entidades extraídas", {
            "name": contact.get("name"),
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "linkedin": contact.get("linkedin"),
        })

        # MATCH com peso por seção
        all_keywords = job.required_skills + job.preferred_skills
        matched, missing, match_details = self._match_keywords_weighted(raw_text, all_keywords, sections)
        self._debug_data["keyword_details"] = match_details
        keyword_density = self._calc_keyword_density(raw_text, all_keywords)

        # SCORE
        skill_score = self._calc_skill_score(matched, job.required_skills, job.preferred_skills)
        exp_score = self._calc_experience_score(raw_text, job.required_experience_years)
        edu_score = self._calc_education_score(raw_text, job.education_level)
        fmt_score = self._calc_formatting_score(raw_text, parsed, metadata)
        sem_score = self._calc_semantic_score(raw_text, job.responsibilities, sections)

        scores = {
            "skill_match": skill_score,
            "experience": exp_score,
            "education": edu_score,
            "formatting": fmt_score,
            "semantic": sem_score
        }
        overall = self._calc_overall(scores)
        self._debug_data["score_components"] = {k: v["score"] for k, v in scores.items()}

        # FILTER
        red_flags = self._detect_red_flags(raw_text, parsed, contact, sections)
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

    # ============================================================
    # DETECÇÃO DE SEÇÕES COM PESOS
    # ============================================================
    def _detect_sections(self, text: str) -> Dict[str, str]:
        """Detecta seções do CV e retorna dict com nome -> conteúdo"""
        section_patterns = {
            "resumo": r"(?:resumo|summary|objetivo|perfil|about)[\s\w]*",
            "experiencia": r"(?:experiência|experiencia|histórico profissional|atuação|trabalho|employment)[\s\w]*",
            "projetos": r"(?:projetos|projects|portfolio|portfólio)[\s\w]*",
            "educacao": r"(?:formação|formacao|educação|educacao|escolaridade|acadêmico|academico)[\s\w]*",
            "skills": r"(?:skills|habilidades|competências|competencias|tecnologias|stack|ferramentas)[\s\w]*",
            "certificacoes": r"(?:certificações|certificacoes|certifications|cursos)[\s\w]*",
            "idiomas": r"(?:idiomas|languages|linguagens)[\s\w]*",
        }

        lines = text.split("\n")
        sections = {}
        current_section = "header"
        current_content = []

        for line in lines:
            stripped = line.strip().lower()
            if not stripped:
                continue
            found_section = None
            for sec_name, pattern in section_patterns.items():
                if re.search(r"^" + pattern + r"[\s:]*$", stripped, re.IGNORECASE):
                    if current_content:
                        sections[current_section] = "\n".join(current_content)
                    current_section = sec_name
                    current_content = []
                    found_section = sec_name
                    break
            if not found_section:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content)

        self.logger.log("EXTRACT", "Seções detectadas", {
            "sections": list(sections.keys()),
            "weights": {k: self.SECTION_WEIGHTS.get(k, 1.0) for k in sections.keys()}
        })
        return sections

    # ============================================================
    # MATCHING COM PESO POR SEÇÃO
    # ============================================================
    def _match_keywords_weighted(self, text: str, keywords: List[str], sections: Dict[str, str]) -> tuple:
        """Faz matching de keywords considerando peso por seção"""
        text_lower = text.lower()
        matched, missing, details = [], [], {}

        for kw in keywords:
            kw_lower = kw.lower().strip()
            found = False
            match_type = "none"
            freq = 0
            best_section = ""
            best_weight = 1.0

            # Verificar em cada seção com peso
            for sec_name, sec_content in sections.items():
                sec_lower = sec_content.lower()
                weight = self.SECTION_WEIGHTS.get(sec_name, 1.0)

                if kw_lower in sec_lower:
                    count = sec_lower.count(kw_lower)
                    if count > 0 and weight > best_weight:
                        best_weight = weight
                        best_section = sec_name
                        found = True
                        match_type = "exact"
                        freq = count
                elif re.search(r"\b" + re.escape(kw_lower) + r"\b", sec_lower):
                    count = len(re.findall(r"\b" + re.escape(kw_lower) + r"\b", sec_lower))
                    if count > 0 and weight > best_weight:
                        best_weight = weight
                        best_section = sec_name
                        found = True
                        match_type = "boundary"
                        freq = count
                elif kw_lower in self.synonyms:
                    for syn in self.synonyms[kw_lower]:
                        if syn in sec_lower:
                            if weight > best_weight:
                                best_weight = weight
                                best_section = sec_name
                                found = True
                                match_type = "synonym"
                                freq = sec_lower.count(syn)
                            break

            # Fallback: buscar no texto inteiro se não achou em seção
            if not found:
                if kw_lower in text_lower:
                    found = True
                    match_type = "exact"
                    freq = text_lower.count(kw_lower)
                elif re.search(r"\b" + re.escape(kw_lower) + r"\b", text_lower):
                    found = True
                    match_type = "boundary"
                    freq = len(re.findall(r"\b" + re.escape(kw_lower) + r"\b", text_lower))

            if found:
                matched.append(kw)
                details[kw] = {
                    "found": True, "type": match_type, "freq": freq,
                    "section": best_section, "weight": best_weight
                }
            else:
                missing.append(kw)
                details[kw] = {"found": False, "type": "none", "freq": 0, "section": "", "weight": 0}

        self.logger.log("MATCH", f"Keywords: {len(matched)}/{len(keywords)} match", {
            "matched": matched, "missing": missing[:10],
            "section_weights_applied": True
        })
        return matched, missing, details

    # ============================================================
    # CONTACT EXTRACTION
    # ============================================================
    def _extract_contact(self, text: str) -> Dict[str, Any]:
        contact = {}
        lines = [l.strip() for l in text.split("\n") if l.strip()][:5]
        for line in lines:
            if not re.search(r"[@+0-9]", line) and len(line.split()) <= 5 and len(line) > 3:
                if not any(k in line.lower() for k in ['curriculum', 'resume', 'cv', 'curriculo']):
                    contact["name"] = line.strip()
                    break

        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            contact["email"] = email_match.group(0)

        phone_patterns = [
            r'(?:\+55\s?)?(?:\(?(\d{2})\)?\s?)?(?:\d{4,5}[-.\s]?\d{4})',
            r'\+?\d{1,3}[-.\s]?\(?(\d{3})\)?[-.\s]?\d{3}[-.\s]?\d{4}',
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

    # ============================================================
    # KEYWORD DENSITY
    # ============================================================
    def _calc_keyword_density(self, text: str, keywords: List[str]) -> Dict:
        words = re.findall(r'\b\w+\b', text.lower())
        total = len(words)
        mentions = sum(text.lower().count(k.lower()) for k in keywords)
        density = (mentions / total * 100) if total > 0 else 0
        self.logger.log("MATCH", "Densidade calculada", {"density": round(density, 2), "words": total})
        return {"density": round(density, 2), "total_words": total, "mentions": mentions}

    # ============================================================
    # SKILL SCORE
    # ============================================================
    def _calc_skill_score(self, matched, required, preferred):
        req = len(set(matched) & set(required)) / len(required) * 100 if required else 0
        pref = len(set(matched) & set(preferred)) / len(preferred) * 50 if preferred else 0
        score = min(100, req + pref)
        self.logger.log("SCORE", "Skill score", {"score": round(score, 1), "req_match": req, "pref_match": pref})
        return {"score": round(score, 1), "weight": 0.35}

    # ============================================================
    # EXPERIENCE SCORE — COM DATE PARSER ROBUSTO
    # ============================================================
    def _calc_experience_score(self, text: str, required: int):
        # 1. Tentar extrair com DateParser (MM/AAAA, DD/MM/AAAA, texto)
        dates_found = self.date_parser.find_dates_in_text(text)
        total_months = 0
        years_from_dates = None

        if dates_found:
            for d in dates_found:
                total_months += d.get("duration_months", 0)
            years_from_dates = round(total_months / 12, 1)

        # 2. Fallback: regex clássico para "X anos de experiencia"
        patterns = [
            r'(\d+\.\d+)\s*anos?\s+de\s+experi[êe]ncia',
            r'(\d+)\s*anos?\s+de\s+experi[êe]ncia',
            r'(\d+)\+?\s*years?\s+of\s+experience',
            r'experi[êe]ncia\s+de\s+(\d+\.\d+)\s*anos?',
            r'experi[êe]ncia\s+de\s+(\d+)\s*anos?',
            r'total\s*[:\s]*\s*(\d+\.\d+)\s*anos?',
            r'total\s*[:\s]*\s*(\d+)\s*anos?',
        ]
        years_text = None
        for p in patterns:
            m = re.search(p, text.lower())
            if m:
                years_text = float(m.group(1))
                break

        # Priorizar anos declarados no texto, senão calcular das datas
        years = years_text if years_text is not None else years_from_dates
        self._debug_data["experience_years_detected"] = years

        if years and required:
            score = 100 if years >= required else max(20, (years / required) * 100)
        elif years:
            score = min(100, years * 20 + 40)  # Heurística: mais anos = mais score
        else:
            score = 50

        self.logger.log("SCORE", "Experience score", {
            "score": round(score, 1), "years": years, "required": required,
            "years_from_text": years_text, "years_from_dates": years_from_dates,
            "date_ranges_found": len(dates_found)
        })
        return {"score": round(score, 1), "weight": 0.25}

    # ============================================================
    # EDUCATION SCORE — TECNÓLOGO = NÍVEL 2
    # ============================================================
    def _calc_education_score(self, text: str, required: str):
        req = self.EDUCATION_LEVELS.get(required.lower(), 3)
        text_lower = text.lower()
        max_lvl = 0
        detected_terms = []

        for term, val in self.EDUCATION_LEVELS.items():
            if term in text_lower:
                max_lvl = max(max_lvl, val)
                detected_terms.append(term)

        self._debug_data["education_level_detected"] = max_lvl

        if max_lvl >= req:
            score = 100
        elif max_lvl == req - 1:
            score = 70
        elif max_lvl > 0:
            score = 40
        else:
            score = 0

        self.logger.log("SCORE", "Education score", {
            "score": score, "level": max_lvl, "required": req,
            "detected_terms": detected_terms[:5]
        })
        return {"score": score, "weight": 0.15}

    # ============================================================
    # FORMATTING SCORE — COM METADADOS
    # ============================================================
    def _calc_formatting_score(self, text: str, parsed: Dict, metadata: Dict):
        score = 100
        issues = []

        # Metadados do DOCX (se disponíveis)
        if metadata.get("title"):
            score += 5  # Bônus por metadados preenchidos
        else:
            issues.append("Metadados Title não preenchidos")

        if metadata.get("author"):
            score += 5
        else:
            issues.append("Metadados Author não preenchidos")

        if metadata.get("keywords"):
            score += 5
        else:
            issues.append("Metadados Keywords não preenchidos")

        # Problemas de formatação
        if len(text) < 200:
            score -= 40
            issues.append("PDF possivelmente imagem")
        if parsed["metadata"].get("is_image_pdf"):
            score -= 30
            issues.append("PDF de imagem detectado")
        weird = len(re.findall(r'[^\w\s\n]', text))
        if weird > 20:
            score -= 10
            issues.append("Caracteres estranhos")

        # Detectar tabelas (quebram linearidade)
        if parsed["metadata"].get("tables", 0) > 0:
            issues.append("Tabelas detectadas — podem quebrar parsing")
            score -= 5

        final_score = max(0, min(100, score))
        self.logger.log("SCORE", "Formatting score", {"score": final_score, "issues": issues, "metadata_bonus": metadata.get("title") is not None})
        return {"score": final_score, "weight": 0.1}

    # ============================================================
    # SEMANTIC SCORE — COM PESO POR SEÇÃO
    # ============================================================
    def _calc_semantic_score(self, text: str, responsibilities: List[str], sections: Dict[str, str]):
        text_lower = text.lower()
        matches = 0
        resp_details = []

        for resp in responsibilities:
            words = re.findall(r'\b[a-z]{4,}\b', resp.lower())
            important = [w for w in words if w not in {"deve", "ser", "para", "will", "must", "desenvolver", "criar", "implementar"}]
            found = sum(1 for w in important if w in text_lower)
            ratio = found / len(important) if important else 0
            if ratio > 0.3:
                matches += 1
            resp_details.append({"resp": resp[:60], "ratio": round(ratio, 2), "matched": ratio > 0.3})

        # Bônus se keywords de responsabilidades aparecem em seções de alto peso
        bonus = 0
        high_weight_sections = ["resumo", "experiencia", "experiência", "projetos"]
        for resp in responsibilities:
            resp_words = set(re.findall(r'\b[a-z]{4,}\b', resp.lower()))
            for sec_name in high_weight_sections:
                if sec_name in sections:
                    sec_words = set(re.findall(r'\b[a-z]{4,}\b', sections[sec_name].lower()))
                    overlap = len(resp_words & sec_words)
                    if overlap > 0:
                        bonus += overlap * 2

        base_score = (matches / len(responsibilities) * 100) if responsibilities else 50
        score = min(100, base_score + bonus)

        self._debug_data["semantic_details"] = resp_details
        self.logger.log("SCORE", "Semantic score", {"score": round(score, 1), "matched": matches, "bonus": bonus})
        return {"score": round(score, 1), "weight": 0.15}

    # ============================================================
    # OVERALL SCORE
    # ============================================================
    def _calc_overall(self, scores: Dict):
        total = sum(v["score"] * v["weight"] for v in scores.values())
        weight_sum = sum(v["weight"] for v in scores.values())
        overall = total / weight_sum if weight_sum > 0 else 0
        self.logger.log("SCORE", "Score final", {
            "overall": round(overall, 1),
            "components": {k: v["score"] for k, v in scores.items()}
        })
        return round(overall, 1)

    # ============================================================
    # RED FLAGS
    # ============================================================
    def _detect_red_flags(self, text: str, parsed: Dict, contact: Dict, sections: Dict):
        flags = []
        if not contact.get("email"): flags.append("❌ Sem email")
        if not contact.get("phone"): flags.append("⚠️ Sem telefone")
        if len(text) < 500: flags.append("⚠️ CV muito curto")
        if len(text) > 15000: flags.append("⚠️ CV muito longo")
        if parsed["file_type"] == "pdf" and parsed["metadata"].get("is_image_pdf"):
            flags.append("🚨 PDF é imagem - texto não extraível")

        # Detectar keyword stuffing por seção
        for sec_name, sec_content in sections.items():
            words = re.findall(r'\b\w+\b', sec_content.lower())
            if len(words) > 0:
                # Verificar repetição excessiva de qualquer palavra
                from collections import Counter
                word_counts = Counter(words)
                most_common = word_counts.most_common(1)[0]
                if most_common[1] > len(words) * 0.15:  # >15% de uma palavra
                    flags.append(f"⚠️ Keyword stuffing em '{sec_name}': '{most_common[0]}' repetido {most_common[1]}x")

        return flags

    # ============================================================
    # RECOMMENDATIONS
    # ============================================================
    def _generate_recommendations(self, overall, missing, flags, scores):
        recs = []
        if overall < 50: recs.append("🚨 Score baixo. Revisar CV completamente.")
        elif overall < 70: recs.append("⚠️ Score na faixa de revisão. Melhorias necessárias.")
        else: recs.append("✅ Score bom! CV bem otimizado.")
        if missing: recs.append(f"📌 Adicione keywords: {', '.join(missing[:10])}")
        if scores.get("formatting", {}).get("score", 100) < 70:
            recs.append("📝 Problemas de formatação detectados.")
        if scores.get("education", {}).get("score", 100) == 0:
            recs.append("🎓 Formação não detectada. Use termos como 'Graduação', 'Bacharelado' ou 'Tecnólogo'.")
        if scores.get("experience", {}).get("score", 100) < 30:
            recs.append("💼 Experiência mal detectada. Use formato 'MM/AAAA' e escreva 'X anos de experiência' explicitamente.")
        return recs
