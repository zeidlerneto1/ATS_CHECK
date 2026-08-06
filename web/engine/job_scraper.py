"""
Web Scraper para extração de dados de vagas
Suporta: LinkedIn, Glassdoor, Indeed, vagas genéricas
"""
import re
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse


class JobScraper:
    """Extrai dados de vagas de sites de emprego"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def scrape(self, url: str) -> Dict[str, any]:
        """Extrai dados de uma URL de vaga"""
        domain = urlparse(url).netloc.lower()

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            return {"success": False, "error": f"Erro ao acessar URL: {str(e)}"}

        # Tenta extrair com base no domínio
        if "linkedin" in domain:
            return self._parse_linkedin(html, url)
        elif "glassdoor" in domain:
            return self._parse_glassdoor(html, url)
        elif "indeed" in domain:
            return self._parse_indeed(html, url)
        else:
            return self._parse_generic(html, url)

    def _clean_text(self, text: str) -> str:
        """Limpa texto extraído"""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_skills(self, text: str) -> List[str]:
        """Extrai skills do texto usando padrões comuns"""
        # Padrões de seção de skills
        skill_patterns = [
            r'(?:Requisitos|Requirements|Qualificações|Qualifications)[\s\S]{0,50}?:(.*?)(?:?:Benefícios|Benefits|Responsabilidades|Responsibilities|O que você fará|What you|Descrição|Description|$)',
            r'(?:Conhecimentos|Skills|Habilidades|Tecnologias)[\s\S]{0,30}?:(.*?)(?:?:Benefícios|Benefits|$)',
        ]

        skills = []
        for pattern in skill_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                skills_text = match.group(1)
                # Extrai itens de lista
                items = re.findall(r'[•\-\*]\s*([^\n•\-\*]+)', skills_text)
                if not items:
                    # Tenta split por vírgula ou nova linha
                    items = [s.strip() for s in re.split(r'[,;\n]', skills_text) if s.strip() and len(s.strip()) > 2]
                skills.extend(items)

        # Se não achou seção, procura por skills conhecidas no texto todo
        if not skills:
            common_skills = [
                "python", "javascript", "typescript", "java", "c#", "c++", "go", "rust", "ruby", "php",
                "node.js", "nodejs", "express", "react", "react.js", "vue", "vue.js", "angular", "next.js",
                "django", "flask", "fastapi", "spring", "laravel", "rails",
                "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "dynamodb",
                "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
                "jenkins", "github actions", "gitlab ci", "ci/cd", "cicd",
                "git", "github", "gitlab",
                "linux", "ubuntu", "windows server",
                "machine learning", "ml", "deep learning", "tensorflow", "pytorch",
                "html", "css", "sass", "tailwind", "bootstrap",
                "rest", "restful", "graphql", "grpc", "soap", "websocket",
                "agile", "scrum", "kanban",
            ]
            text_lower = text.lower()
            for skill in common_skills:
                if skill in text_lower:
                    skills.append(skill)

        return list(dict.fromkeys(skills))  # Remove duplicatas mantendo ordem

    def _extract_responsibilities(self, text: str) -> List[str]:
        """Extrai responsabilidades"""
        resp_patterns = [
            r'(?:Responsabilidades|Responsibilities|O que você fará|What you will do|Atividades)[\s\S]{0,50}?:(.*?)(?:?:Requisitos|Requirements|Qualificações|Qualifications|Benefícios|Benefits|$)',
            r'(?:Descrição da vaga|Job description|About the role)[\s\S]{0,50}?:(.*?)(?:?:Requisitos|Requirements|$)',
        ]

        responsibilities = []
        for pattern in resp_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                resp_text = match.group(1)
                items = re.findall(r'[•\-\*]\s*([^\n•\-\*]+)', resp_text)
                if not items:
                    items = [s.strip() for s in resp_text.split('\n') if s.strip() and len(s.strip()) > 10]
                responsibilities.extend(items)

        return responsibilities[:8]  # Limita a 8 responsabilidades

    def _extract_title(self, text: str, html: str) -> str:
        """Extrai título da vaga"""
        # Tenta do HTML primeiro
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1)
            # Remove sufixos comuns
            title = re.sub(r'\s*[\-|—]\s*(LinkedIn|Glassdoor|Indeed|Jobs).*', '', title, flags=re.IGNORECASE)
            return title.strip()

        # Tenta do texto
        title_patterns = [
            r'(?:Vaga|Job|Position)[\s]*:?\s*([^\n]{5,80})',
            r'^([^\n]{5,80})(?:\n|$)',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "Vaga"

    def _extract_company(self, text: str, html: str) -> str:
        """Extrai nome da empresa"""
        # Padrões comuns
        company_patterns = [
            r'(?:Empresa|Company)[\s]*:?\s*([^\n]{2,50})',
            r'(?:em|at)\s+([A-Z][^\n]{2,50})(?:\n|$)',
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "Empresa"

    def _extract_experience_years(self, text: str) -> int:
        """Extrai anos de experiência requeridos"""
        patterns = [
            r'(\d+)\+?\s*(?:anos?|years?).*?(?:experiência|experience)',
            r'(?:experiência|experience).*?(\d+)\+?\s*(?:anos?|years?)',
            r'(\d+)\+?\s*(?:anos?|years?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                years = int(match.group(1))
                if 0 <= years <= 20:
                    return years
        return 0

    def _extract_education(self, text: str) -> str:
        """Extrai nível de educação"""
        text_lower = text.lower()
        if any(w in text_lower for w in ["doutorado", "phd", "doctorate"]):
            return "phd"
        elif any(w in text_lower for w in ["mestrado", "master", "pós-graduação", "mba"]):
            return "mestrado"
        elif any(w in text_lower for w in ["bacharel", "bacharelado", "licenciatura", "graduação", "bachelor"]):
            return "graduacao"
        elif any(w in text_lower for w in ["tecnólogo", "tecnologo"]):
            return "tecnologo"
        elif any(w in text_lower for w in ["técnico", "tecnico", "technical"]):
            return "tecnico"
        return "graduacao"

    def _parse_linkedin(self, html: str, url: str) -> Dict:
        """Parse específico para LinkedIn"""
        # LinkedIn carrega conteúdo via JS, mas alguns dados estão no HTML
        text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html)
        text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = self._clean_text(text)

        # LinkedIn às vezes tem JSON-LD
        jsonld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        if jsonld:
            import json
            try:
                data = json.loads(jsonld.group(1))
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    return {
                        "success": True,
                        "title": data.get("title", self._extract_title(text, html)),
                        "company": data.get("hiringOrganization", {}).get("name", self._extract_company(text, html)),
                        "required_skills": self._extract_skills(text),
                        "preferred_skills": [],
                        "required_experience_years": self._extract_experience_years(text),
                        "education_level": self._extract_education(text),
                        "responsibilities": data.get("responsibilities", self._extract_responsibilities(text)),
                        "source": "linkedin",
                    }
            except:
                pass

        return self._parse_generic(html, url)

    def _parse_glassdoor(self, html: str, url: str) -> Dict:
        """Parse específico para Glassdoor"""
        return self._parse_generic(html, url)

    def _parse_indeed(self, html: str, url: str) -> Dict:
        """Parse específico para Indeed"""
        return self._parse_generic(html, url)

    def _parse_generic(self, html: str, url: str) -> Dict:
        """Parse genérico para qualquer site"""
        # Remove scripts e styles
        text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html)
        text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = self._clean_text(text)

        skills = self._extract_skills(text)

        # Separa em obrigatórias e desejáveis
        required = []
        preferred = []

        # Procura por seção "desejável"
        text_lower = text.lower()
        desirable_idx = -1
        for term in ["desejável", "desejaveis", "preferencial", "preferred", "desired", "diferencial"]:
            idx = text_lower.find(term)
            if idx != -1:
                desirable_idx = idx
                break

        if desirable_idx != -1:
            # Skills antes do "desejável" = obrigatórias
            # Skills depois = desejáveis
            for skill in skills:
                skill_lower = skill.lower()
                # Encontra posição da skill no texto
                pos = text_lower.find(skill_lower)
                if pos != -1 and pos < desirable_idx:
                    required.append(skill)
                elif pos != -1:
                    preferred.append(skill)

        if not required and not preferred:
            required = skills

        return {
            "success": True,
            "title": self._extract_title(text, html),
            "company": self._extract_company(text, html),
            "required_skills": required or skills[:10],
            "preferred_skills": preferred or skills[10:],
            "required_experience_years": self._extract_experience_years(text),
            "education_level": self._extract_education(text),
            "responsibilities": self._extract_responsibilities(text),
            "source": "generic",
            "raw_text_preview": text[:500] + "...",
        }
