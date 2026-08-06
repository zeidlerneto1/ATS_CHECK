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
        # Clusters semânticos de skills (Cap. 5 do manual)
        self.SKILL_CLUSTERS = {
            "node_ecosystem": {
                "skills": ["node.js", "express", "npm", "javascript", "typescript"],
                "bonus": 8, "label": "Ecossistema Node.js"
            },
            "react_ecosystem": {
                "skills": ["react", "redux", "next.js", "javascript", "typescript", "html", "css"],
                "bonus": 8, "label": "Ecossistema React"
            },
            "vue_ecosystem": {
                "skills": ["vue", "vuex", "nuxt", "javascript", "typescript"],
                "bonus": 8, "label": "Ecossistema Vue"
            },
            "python_data": {
                "skills": ["python", "pandas", "numpy", "scikit_learn", "tensorflow", "pytorch"],
                "bonus": 8, "label": "Data Science Python"
            },
            "python_web": {
                "skills": ["python", "django", "flask", "fastapi", "sql"],
                "bonus": 8, "label": "Web Python"
            },
            "java_spring": {
                "skills": ["java", "spring", "sql", "rest_api"],
                "bonus": 8, "label": "Java/Spring"
            },
            "devops_cloud": {
                "skills": ["docker", "kubernetes", "aws", "ci/cd", "terraform", "linux"],
                "bonus": 8, "label": "DevOps/Cloud"
            },
            "database_sql": {
                "skills": ["sql", "postgresql", "mysql", "redis"],
                "bonus": 6, "label": "Bancos SQL"
            },
            "frontend_core": {
                "skills": ["javascript", "typescript", "html", "css", "git"],
                "bonus": 5, "label": "Frontend Core"
            },
            "testing": {
                "skills": ["tdd", "jest", "cypress", "selenium"],
                "bonus": 5, "label": "Testing"
            },
        }

        # Verbos de ação para análise XYZ (Cap. 6)
        self.ACTION_VERBS = {
            "pt": ["desenvolvi", "criei", "implementei", "construí", "otimizei", "reduzi",
                   "aumentei", "melhorei", "liderou", "gerenciei", "coordenei", "automatizei",
                   "integrei", "deployei", "mantive", "refatorei", "projetei", "arquitetei",
                   "configurei", "instalei", "atualizei", "migrei", "testei", "documentei"],
            "en": ["developed", "created", "implemented", "built", "optimized", "reduced",
                   "increased", "improved", "led", "managed", "coordinated", "automated",
                   "integrated", "deployed", "maintained", "refactored", "designed", "architected",
                   "configured", "installed", "updated", "migrated", "tested", "documented"],
        }

        self._debug_data = {
            "contact": {}, "parsed_metadata": {}, "keyword_details": {},
            "score_components": {}, "experience_years_detected": None,
            "education_level_detected": 0, "sections_found": [],
            "section_scores": {}, "semantic_clusters": [], "career_gaps": [],
            "bullet_analysis": [], "bilingual_bonus": 0, "context_bleed": [],
        }

    def get_debug_data(self) -> Dict[str, Any]:
        return self._debug_data

    def analyze(self, file_path: str, job: JobDescription, log_callback=None) -> ATSResult:
        self.logger = ATSLogger()
        if log_callback:
            self.logger.add_callback(log_callback)

        self.parser.logger = self.logger
        # Clusters semânticos de skills (Cap. 5 do manual)
        self.SKILL_CLUSTERS = {
            "node_ecosystem": {
                "skills": ["node.js", "express", "npm", "javascript", "typescript"],
                "bonus": 8, "label": "Ecossistema Node.js"
            },
            "react_ecosystem": {
                "skills": ["react", "redux", "next.js", "javascript", "typescript", "html", "css"],
                "bonus": 8, "label": "Ecossistema React"
            },
            "vue_ecosystem": {
                "skills": ["vue", "vuex", "nuxt", "javascript", "typescript"],
                "bonus": 8, "label": "Ecossistema Vue"
            },
            "python_data": {
                "skills": ["python", "pandas", "numpy", "scikit_learn", "tensorflow", "pytorch"],
                "bonus": 8, "label": "Data Science Python"
            },
            "python_web": {
                "skills": ["python", "django", "flask", "fastapi", "sql"],
                "bonus": 8, "label": "Web Python"
            },
            "java_spring": {
                "skills": ["java", "spring", "sql", "rest_api"],
                "bonus": 8, "label": "Java/Spring"
            },
            "devops_cloud": {
                "skills": ["docker", "kubernetes", "aws", "ci/cd", "terraform", "linux"],
                "bonus": 8, "label": "DevOps/Cloud"
            },
            "database_sql": {
                "skills": ["sql", "postgresql", "mysql", "redis"],
                "bonus": 6, "label": "Bancos SQL"
            },
            "frontend_core": {
                "skills": ["javascript", "typescript", "html", "css", "git"],
                "bonus": 5, "label": "Frontend Core"
            },
            "testing": {
                "skills": ["tdd", "jest", "cypress", "selenium"],
                "bonus": 5, "label": "Testing"
            },
        }

        # Verbos de ação para análise XYZ (Cap. 6)
        self.ACTION_VERBS = {
            "pt": ["desenvolvi", "criei", "implementei", "construí", "otimizei", "reduzi",
                   "aumentei", "melhorei", "liderou", "gerenciei", "coordenei", "automatizei",
                   "integrei", "deployei", "mantive", "refatorei", "projetei", "arquitetei",
                   "configurei", "instalei", "atualizei", "migrei", "testei", "documentei"],
            "en": ["developed", "created", "implemented", "built", "optimized", "reduced",
                   "increased", "improved", "led", "managed", "coordinated", "automated",
                   "integrated", "deployed", "maintained", "refactored", "designed", "architected",
                   "configured", "installed", "updated", "migrated", "tested", "documented"],
        }

        self._debug_data = {
            "contact": {}, "parsed_metadata": {}, "keyword_details": {},
            "score_components": {}, "experience_years_detected": None,
            "education_level_detected": 0, "sections_found": [],
            "section_scores": {}, "semantic_clusters": [], "career_gaps": [],
            "bullet_analysis": [], "bilingual_bonus": 0, "context_bleed": [],
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

        # ONDA 2: Inteligência Semântica
        # 6. Clusterização semântica
        cluster_bonus, cluster_details = self._calc_semantic_clusters(raw_text, matched)
        self._debug_data["semantic_clusters"] = cluster_details

        # 7. Gaps de carreira
        gaps = self._detect_career_gaps(raw_text)
        self._debug_data["career_gaps"] = gaps
        if gaps:
            for g in gaps:
                if g["months"] >= 6:
                    self.logger.log("FILTER", f"Gap de carreira detectado: {g['months']} meses", g)

        # 8. Análise de bullets XYZ
        bullet_analysis = self._analyze_bullets_xyz(raw_text, sections)
        self._debug_data["bullet_analysis"] = bullet_analysis

        # 9. Regra bilíngue
        bilingual_bonus = self._detect_bilingual_bonus(raw_text, sections)
        self._debug_data["bilingual_bonus"] = bilingual_bonus

        # 10. Context bleed
        bleed_bonus, bleed_details = self._detect_context_bleed(sections, matched)
        self._debug_data["context_bleed"] = bleed_details

        # SCORE (com bônus da Onda 2)
        skill_score = self._calc_skill_score(matched, job.required_skills, job.preferred_skills)
        exp_score = self._calc_experience_score(raw_text, job.required_experience_years)
        edu_score = self._calc_education_score(raw_text, job.education_level)
        fmt_score = self._calc_formatting_score(raw_text, parsed, metadata)
        sem_score = self._calc_semantic_score(raw_text, job.responsibilities, sections)

        # Aplicar bônus semânticos
        sem_score["score"] = min(100, sem_score["score"] + cluster_bonus + bilingual_bonus + bleed_bonus)
        skill_score["score"] = min(100, skill_score["score"] + cluster_bonus * 0.5)

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
            # Padrões grudados (ex: "1.5+yearsoffull-stack", "1.5yearsofexperience")
            r'(\d+\.\d+)[+\-]?\s*years?\s*of\s*experience',
            r'(\d+)[+\-]?\s*years?\s*of\s*experience',
            r'(\d+\.\d+)[+\-]?\s*years?\s*of\s*\w+',
            r'(\d+)[+\-]?\s*years?\s*of\s*\w+',
            r'(\d+\.\d+)[+\-]?\s*anos?\s*de\s*\w+',
            r'(\d+)[+\-]?\s*anos?\s*de\s*\w+',
            r'(\d+\.\d+)\s*anos?\s*de\s*experi[êe]ncia',
            r'(\d+)\s*anos?\s*de\s*experi[êe]ncia',
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

        # Detectar keyword stuffing por seção (ignorando stop words)
        STOP_WORDS = {
            "a", "o", "as", "os", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
            "por", "para", "com", "sem", "sob", "sobre", "entre", "ante", "após", "até", "desde",
            "e", "ou", "mas", "nem", "que", "se", "como", "quando", "onde", "porque", "pois",
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
            "by", "from", "up", "about", "into", "through", "during", "before", "after", "above",
            "below", "between", "among", "within", "without", "against", "under", "over", "via",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
            "did", "will", "would", "could", "should", "may", "might", "must", "can", "shall",
            "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
            "my", "your", "his", "her", "its", "our", "their", "this", "that", "these", "those",
        }
        for sec_name, sec_content in sections.items():
            words = re.findall(r'\b\w+\b', sec_content.lower())
            # Filtrar stop words
            filtered_words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
            if len(filtered_words) > 0:
                from collections import Counter
                word_counts = Counter(filtered_words)
                most_common = word_counts.most_common(1)[0]
                if most_common[1] > len(filtered_words) * 0.15:  # >15% de uma palavra
                    flags.append(f"⚠️ Keyword stuffing em '{sec_name}': '{most_common[0]}' repetido {most_common[1]}x")

        return flags


    # ============================================================
    # ONDA 2: INTELIGÊNCIA SEMÂNTICA
    # ============================================================

    # 6. CLUSTERIZAÇÃO SEMÂNTICA DE SKILLS
    def _calc_semantic_clusters(self, text: str, matched_skills: List[str]) -> Tuple[float, List[Dict]]:
        """Detecta clusters de skills que aparecem juntas no mesmo contexto"""
        text_lower = text.lower()
        clusters_found = []
        total_bonus = 0

        for cluster_id, cluster in self.SKILL_CLUSTERS.items():
            cluster_skills = [s.lower() for s in cluster["skills"]]
            # Verificar quais skills do cluster foram detectadas no CV
            found_in_cv = [s for s in cluster_skills if s in [m.lower() for m in matched_skills]]
            if len(found_in_cv) >= 2:
                # Verificar se aparecem no mesmo contexto (mesmo parágrafo/bullet)
                paragraphs = text_lower.split("\n")
                context_matches = 0
                for para in paragraphs:
                    para = para.strip()
                    if len(para) < 10:
                        continue
                    matches_in_para = sum(1 for s in cluster_skills if s in para)
                    if matches_in_para >= 2:
                        context_matches += 1

                if context_matches > 0:
                    bonus = min(cluster["bonus"], cluster["bonus"] * context_matches)
                    total_bonus += bonus
                    clusters_found.append({
                        "cluster": cluster["label"],
                        "skills_found": found_in_cv,
                        "context_matches": context_matches,
                        "bonus": bonus,
                    })

        self.logger.log("MATCH", f"Clusters semânticos: {len(clusters_found)} encontrados", {
            "clusters": [c["cluster"] for c in clusters_found],
            "total_bonus": total_bonus,
        })
        return total_bonus, clusters_found

    # 7. VERIFICAÇÃO DE GAPS DE CARREIRA
    def _detect_career_gaps(self, text: str) -> List[Dict]:
        """Detecta gaps entre experiências profissionais (>3 meses = atenção)"""
        dates_found = self.date_parser.find_dates_in_text(text)
        if len(dates_found) < 2:
            return []

        # Ordenar por data de início
        sorted_dates = sorted(dates_found, key=lambda d: (d["start"]["year"], d["start"].get("month") or 1))
        gaps = []

        for i in range(1, len(sorted_dates)):
            prev_end = sorted_dates[i - 1]["end"]
            curr_start = sorted_dates[i]["start"]

            prev_year = prev_end["year"]
            prev_month = prev_end.get("month") or 12
            curr_year = curr_start["year"]
            curr_month = curr_start.get("month") or 1

            gap_months = (curr_year - prev_year) * 12 + (curr_month - prev_month)
            if gap_months > 3:
                severity = "critical" if gap_months >= 6 else "warning"
                gaps.append({
                    "gap_index": i,
                    "months": gap_months,
                    "from": f"{prev_month}/{prev_year}",
                    "to": f"{curr_month}/{curr_year}",
                    "severity": severity,
                })

        self.logger.log("FILTER", f"Gaps de carreira: {len(gaps)} detectados", {
            "gaps": [{"months": g["months"], "severity": g["severity"]} for g in gaps]
        })
        return gaps

    # 8. ANÁLISE DE BULLETS XYZ
    def _analyze_bullets_xyz(self, text: str, sections: Dict[str, str]) -> List[Dict]:
        """Analisa bullets segundo a Fórmula XYZ: [O quê] + [Quanto] + [Como]"""
        analysis = []
        exp_text = sections.get("experiencia", sections.get("experiência", ""))
        if not exp_text:
            return analysis

        bullets = [b.strip() for b in exp_text.split("\n") if b.strip().startswith(("-", "•", "*", "►", "▸", "→")) or len(b.strip()) > 20]

        for bullet in bullets[:20]:  # Limitar a 20 bullets
            bullet_lower = bullet.lower()
            # Verbo de ação no início
            has_action_verb = any(v in bullet_lower[:40] for v in self.ACTION_VERBS["pt"] + self.ACTION_VERBS["en"])
            # Métrica/numero
            has_metric = bool(re.search(r'\d+%|\d+\s*(?:x|vezes|times|h|horas|min|dias|meses|anos|k|mil|mi)', bullet_lower))
            # Stack/tecnologia mencionada
            has_stack = any(tech in bullet_lower for tech in ["node", "react", "python", "java", "sql", "docker", "aws", "git"])
            # Primeira linha (peso maior)
            is_first_line = bullet == bullets[0] if bullets else False

            score = 0
            if has_action_verb: score += 30
            if has_metric: score += 40
            if has_stack: score += 20
            if is_first_line: score += 10

            grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"

            analysis.append({
                "bullet_preview": bullet[:80] + "..." if len(bullet) > 80 else bullet,
                "has_action_verb": has_action_verb,
                "has_metric": has_metric,
                "has_stack": has_stack,
                "is_first_line": is_first_line,
                "score": score,
                "grade": grade,
            })

        # Calcular média
        if analysis:
            avg = sum(a["score"] for a in analysis) / len(analysis)
            self.logger.log("SCORE", f"Análise XYZ: {len(analysis)} bullets, média {avg:.1f}/100", {
                "bullets_analyzed": len(analysis),
                "average_score": round(avg, 1),
                "grade_a_count": sum(1 for a in analysis if a["grade"] == "A"),
            })
        return analysis

    # 9. REGRA BILÍNGUE
    def _detect_bilingual_bonus(self, text: str, sections: Dict[str, str]) -> float:
        """Dá bônus quando tecnologias em EN aparecem em contexto PT"""
        bonus = 0
        details = []

        # Tecnologias em inglês comuns
        en_techs = ["node.js", "react", "docker", "kubernetes", "aws", "sql", "rest", "api",
                    "javascript", "typescript", "python", "java", "git", "linux", "ci/cd"]

        for sec_name, sec_content in sections.items():
            sec_lower = sec_content.lower()
            # Verificar se a seção tem contexto em português
            pt_markers = ["desenvolvi", "criei", "implementei", "experiência", "profissional",
                          "trabalhei", "atuei", "responsável", "gestão", "equipe"]
            has_pt_context = any(m in sec_lower for m in pt_markers)

            if has_pt_context:
                for tech in en_techs:
                    if tech in sec_lower:
                        bonus += 1.5
                        details.append({"tech": tech, "section": sec_name})

        bonus = min(10, bonus)  # Cap em 10 pontos
        self.logger.log("MATCH", f"Bônus bilíngue: +{bonus:.1f} pts", {
            "matches": len(details), "bonus": bonus
        })
        return bonus

    # 10. CONTEXT BLEED
    def _detect_context_bleed(self, sections: Dict[str, str], matched_skills: List[str]) -> Tuple[float, List[Dict]]:
        """Detecta keywords no final de uma seção E início da próxima (context bleed)"""
        bonus = 0
        bleed_details = []

        section_order = ["resumo", "experiencia", "experiência", "projetos", "educacao", "educação", "skills", "habilidades"]
        ordered_sections = []
        for sec_name in section_order:
            if sec_name in sections:
                ordered_sections.append((sec_name, sections[sec_name]))

        for i in range(len(ordered_sections) - 1):
            curr_name, curr_content = ordered_sections[i]
            next_name, next_content = ordered_sections[i + 1]

            # Últimas 3 linhas da seção atual
            curr_lines = [l.strip().lower() for l in curr_content.split("\n") if l.strip()][-3:]
            # Primeiras 3 linhas da próxima seção
            next_lines = [l.strip().lower() for l in next_content.split("\n") if l.strip()][:3]

            curr_text = " ".join(curr_lines)
            next_text = " ".join(next_lines)

            for skill in matched_skills:
                skill_lower = skill.lower()
                in_curr = skill_lower in curr_text
                in_next = skill_lower in next_text
                if in_curr and in_next:
                    bonus += 2
                    bleed_details.append({
                        "skill": skill,
                        "from_section": curr_name,
                        "to_section": next_name,
                        "bonus": 2,
                    })

        bonus = min(15, bonus)  # Cap em 15 pontos
        self.logger.log("MATCH", f"Context bleed: {len(bleed_details)} ocorrências", {
            "bleed_count": len(bleed_details), "bonus": bonus
        })
        return bonus, bleed_details

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

        # ONDA 2: Recomendações semânticas
        clusters = self._debug_data.get("semantic_clusters", [])
        if clusters:
            incomplete = [c for c in clusters if len(c.get("skills_found", [])) < 3]
            if incomplete:
                recs.append(f"🔗 Cluster incompleto: {incomplete[0]['cluster']}. Adicione skills relacionadas para reforçar o ecossistema.")

        gaps = self._debug_data.get("career_gaps", [])
        if gaps:
            critical_gaps = [g for g in gaps if g["severity"] == "critical"]
            if critical_gaps:
                recs.append(f"⏳ Gap de carreira de {critical_gaps[0]['months']} meses detectado. Justifique com projetos ou cursos.")

        bullets = self._debug_data.get("bullet_analysis", [])
        if bullets:
            weak = [b for b in bullets if b["grade"] in ("C", "D")]
            if len(weak) > len(bullets) * 0.5:
                recs.append("📝 Mais da metade dos bullets são fracos. Use a Fórmula XYZ: [O quê] + [Quanto] + [Como].")
            no_metrics = [b for b in bullets if not b["has_metric"]]
            if len(no_metrics) > len(bullets) * 0.7:
                recs.append("📊 Adicione métricas nos bullets (números, %, tempo). Ex: 'Reduzi tempo de deploy de 2h para 15min'.")

        return recs
