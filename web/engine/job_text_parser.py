"""
Job Text Parser - Extrai dados de vaga a partir de texto colado
"""
import re
from typing import Dict, List, Tuple


class JobTextParser:
    """Parser inteligente para extrair dados de vagas de texto livre"""

    # Lista extensa de skills técnicas para detectar
    SKILL_PATTERNS = [
        # Linguagens
        r'\bpython\b', r'\bjavascript\b', r'\btypescript\b', r'\bjava\b', r'\bc\+\+\b',
        r'\bc#\b', r'\bgo\b', r'\brust\b', r'\bruby\b', r'\bphp\b', r'\bswift\b',
        r'\bkotlin\b', r'\bdart\b', r'\bscala\b', r'\br\b', r'\bmatlab\b',

        # Frameworks Frontend
        r'\breact\b', r'\breact\.js\b', r'\bvue\b', r'\bvue\.js\b', r'\bangular\b',
        r'\bsvelte\b', r'\bnext\.js\b', r'\bnuxt\b', r'\bremix\b', r'\bgatsby\b',

        # Frameworks Backend
        r'\bnode\.js\b', r'\bnodejs\b', r'\bexpress\b', r'\bdjango\b', r'\bflask\b',
        r'\bfastapi\b', r'\bspring\b', r'\bspring boot\b', r'\blaravel\b', r'\brails\b',
        r'\baspnet\b', r'\bnest\.js\b', r'\bfastify\b',

        # Bancos de dados
        r'\bsql\b', r'\bmysql\b', r'\bpostgresql\b', r'\bmongodb\b', r'\bredis\b',
        r'\belasticsearch\b', r'\bdynamodb\b', r'\bcassandra\b', r'\bneo4j\b',
        r'\bsqlite\b', r'\boracle\b', r'\bmariadb\b', r'\bfirebase\b',

        # Cloud/DevOps
        r'\baws\b', r'\bgcp\b', r'\bazure\b', r'\bdocker\b', r'\bkubernetes\b',
        r'\bk8s\b', r'\bterraform\b', r'\bansible\b', r'\bjenkins\b', r'\bcircleci\b',
        r'\btravis\b', r'\bgithub actions\b', r'\bgitlab ci\b', r'\bci/cd\b', r'\bcicd\b',
        r'\bheroku\b', r'\bvercel\b', r'\bnetlify\b', r'\bdigitalocean\b',

        # Ferramentas
        r'\bgit\b', r'\bgithub\b', r'\bgitlab\b', r'\bbitbucket\b',
        r'\bjira\b', r'\btrello\b', r'\bnotion\b', r'\bconfluence\b',
        r'\bfigma\b', r'\bsketch\b', r'\badobe xd\b',

        # Data/ML
        r'\bmachine learning\b', r'\bdeep learning\b', r'\btensorflow\b', r'\bpytorch\b',
        r'\bscikit-learn\b', r'\bpandas\b', r'\bnumpy\b', r'\bmatplotlib\b',
        r'\bjupyter\b', r'\bspark\b', r'\bhadoop\b', r'\bkafka\b',
        r'\bairflow\b', r'\bdbt\b', r'\bsnowflake\b', r'\bpower bi\b',
        r'\btableau\b', r'\blooker\b',

        # Mobile
        r'\breact native\b', r'\bflutter\b', r'\bionic\b', r'\bxamarin\b',
        r'\bandroid\b', r'\bios\b', r'\bswiftui\b',

        # Outros
        r'\bhtml\b', r'\bcss\b', r'\bsass\b', r'\bless\b', r'\btailwind\b',
        r'\bbootstrap\b', r'\bmaterial ui\b', r'\bchakra ui\b',
        r'\brest\b', r'\brestful\b', r'\bgraphql\b', r'\bgrpc\b', r'\bsoap\b',
        r'\bwebsocket\b', r'\bsocket\.io\b',
        r'\bagile\b', r'\bscrum\b', r'\bkanban\b',
        r'\btdd\b', r'\bbdd\b', r'\bclean code\b', r'\bsolid\b',
        r'\bmicroservices\b', r'\bserverless\b', r'\bapi gateway\b',
        r'\boauth\b', r'\bjwt\b', r'\bsso\b', r'\bldap\b',
        r'\bnginx\b', r'\bapache\b', r'\btraefik\b',
        r'\bprometheus\b', r'\bgrafana\b', r'\belk\b', r'\bdatadog\b',
        r'\blinux\b', r'\bubuntu\b', r'\bcentos\b', r'\bdebian\b',
        r'\bwindows server\b',
    ]

    # Termos que indicam skills desejáveis vs obrigatórias
    DESIRABLE_MARKERS = [
        'desejável', 'desejaveis', 'preferencial', 'preferenciais',
        'diferencial', 'diferenciais', 'plus', 'nice to have',
        'será um diferencial', 'desejado', 'preferred', 'desired',
        'beneficial', 'advantage', 'a plus',
    ]

    REQUIRED_MARKERS = [
        'obrigatório', 'obrigatorio', 'obrigatórios', 'requisitos',
        'requisito', 'necessário', 'necessarios', 'required',
        'requirements', 'must have', 'essential', 'mandatory',
        'pré-requisitos', 'pre-requisitos', 'qualificações',
        'qualificacoes', 'qualifications',
    ]

    def parse(self, text: str) -> Dict:
        """Extrai todos os dados de uma descrição de vaga em texto"""
        text_lower = text.lower()

        result = {
            "success": True,
            "title": self._extract_title(text),
            "company": self._extract_company(text),
            "required_skills": [],
            "preferred_skills": [],
            "required_experience_years": self._extract_experience(text),
            "education_level": self._extract_education(text),
            "responsibilities": self._extract_responsibilities(text),
            "raw_skills_found": [],
        }

        # Extrai todas as skills do texto
        all_skills = self._extract_all_skills(text)
        result["raw_skills_found"] = all_skills

        # Separa em obrigatórias vs desejáveis baseado na posição no texto
        required, preferred = self._separate_skills(text, all_skills)
        result["required_skills"] = required
        result["preferred_skills"] = preferred

        return result

    def _extract_all_skills(self, text: str) -> List[str]:
        """Encontra todas as skills no texto"""
        found = []
        text_lower = text.lower()

        for pattern in self.SKILL_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                skill = match.group(0).strip()
                if skill and skill not in found:
                    found.append(skill)

        return found

    def _separate_skills(self, text: str, skills: List[str]) -> Tuple[List[str], List[str]]:
        """Separa skills em obrigatórias vs desejáveis"""
        text_lower = text.lower()

        # Encontra onde começa a seção de desejáveis
        desirable_start = len(text_lower)  # Por padrão, tudo é obrigatório

        for marker in self.DESIRABLE_MARKERS:
            idx = text_lower.find(marker)
            if idx != -1 and idx < desirable_start:
                desirable_start = idx

        # Encontra onde começa a seção de requisitos
        required_start = 0
        for marker in self.REQUIRED_MARKERS:
            idx = text_lower.find(marker)
            if idx != -1 and idx > required_start:
                required_start = idx

        required = []
        preferred = []

        for skill in skills:
            skill_lower = skill.lower()
            # Encontra todas as ocorrências da skill
            positions = [m.start() for m in re.finditer(re.escape(skill_lower), text_lower)]

            if not positions:
                required.append(skill)
                continue

            # Se a skill aparece APENAS após o marcador de desejável → é desejável
            # Se aparece antes ou em ambos → é obrigatória
            only_after_desirable = all(pos >= desirable_start for pos in positions)
            any_before_desirable = any(pos < desirable_start for pos in positions)

            if only_after_desirable and desirable_start < len(text_lower):
                preferred.append(skill)
            elif any_before_desirable:
                required.append(skill)
            else:
                # Se não conseguiu determinar, verifica contexto próximo
                context = self._get_skill_context(text_lower, skill_lower)
                if any(m in context for m in self.DESIRABLE_MARKERS):
                    preferred.append(skill)
                else:
                    required.append(skill)

        return required, preferred

    def _get_skill_context(self, text: str, skill: str, window: int = 100) -> str:
        """Pega o contexto ao redor de uma skill"""
        idx = text.find(skill)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(skill) + window)
        return text[start:end]

    def _extract_title(self, text: str) -> str:
        """Extrai título da vaga das primeiras linhas"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Padrões comuns de título
        title_patterns = [
            r'^(?:Vaga|Job|Position|Cargo)[\s:]*(.{5,60})$',
            r'^(.{5,60})(?:\s*[\-|—]\s*(?:LinkedIn|Glassdoor|Indeed|Jobs|$))',
        ]

        for line in lines[:5]:
            for pattern in title_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        # Fallback: primeira linha que parece um cargo
        for line in lines[:3]:
            if any(word in line.lower() for word in ['desenvolvedor', 'developer', 'engenheiro', 'engineer', 'analista', 'analyst', 'gerente', 'manager']):
                return line.strip()

        return lines[0][:60] if lines else "Vaga"

    def _extract_company(self, text: str) -> str:
        """Extrai nome da empresa"""
        text_lower = text.lower()

        # Padrões comuns
        patterns = [
            r'(?:Empresa|Company)[\s:]*(.{2,50})(?:\n|$)',
            r'(?:em|at)\s+([A-Z][^\n]{2,50})(?:\n|$)',
            r'^(.{2,40})(?:\s*[\-|—]\s*(?:LinkedIn|Glassdoor|Indeed))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()

        return "Empresa"

    def _extract_experience(self, text: str) -> int:
        """Extrai anos de experiência requeridos"""
        text_lower = text.lower()

        patterns = [
            r'(\d+)\+?\s*(?:anos?|years?).*?(?:experiência|experience)',
            r'(?:experiência|experience).*?(\d+)\+?\s*(?:anos?|years?)',
            r'(\d+)\+?\s*(?:anos?|years?)\s*(?:de\s*)?(?:experiência|experience)',
            r'(?:mínimo|minimum|at least|pelo menos)[\s\w]*?(\d+)\+?\s*(?:anos?|years?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                years = int(match.group(1))
                if 0 <= years <= 30:
                    return years

        return 0

    def _extract_education(self, text: str) -> str:
        """Extrai nível de educação"""
        text_lower = text.lower()

        # Ordem: do mais específico para o mais genérico
        if any(w in text_lower for w in ['doutorado', 'phd', 'doctorate', 'doutor']):
            return 'phd'
        elif any(w in text_lower for w in ['mestrado', 'master', 'mba', 'pós-graduação', 'pos-graduacao', 'especialização']):
            return 'mestrado'
        elif any(w in text_lower for w in ['bacharelado', 'bacharel', 'licenciatura', 'graduação', 'graduacao', 'superior completo', 'bachelor']):
            return 'graduacao'
        elif any(w in text_lower for w in ['tecnólogo', 'tecnologo', 'tecnologia da informação', 'analise e desenvolvimento']):
            return 'tecnologo'
        elif any(w in text_lower for w in ['técnico', 'tecnico', 'technical', 'ensino médio', 'ensino medio']):
            return 'tecnico'

        return 'graduacao'

    def _extract_responsibilities(self, text: str) -> List[str]:
        """Extrai responsabilidades/atividades"""
        text_lower = text.lower()

        # Encontra a seção de responsabilidades
        section_patterns = [
            r'(?:Responsabilidades|Responsibilities|O que você fará|What you will do|Atividades|Atribuições|Activities)[\s:]*',
            r'(?:Descrição da vaga|Job description|About the role|Sobre a vaga)[\s:]*',
        ]

        responsibilities = []

        for pattern in section_patterns:
            match = re.search(pattern, text_lower)
            if match:
                start = match.end()
                # Pega texto até a próxima seção
                end_markers = ['requisitos', 'requirements', 'qualificações', 'qualifications', 
                              'benefícios', 'benefits', 'o que oferecemos', 'what we offer',
                              'sobre a empresa', 'about the company']
                end = len(text_lower)
                for marker in end_markers:
                    idx = text_lower.find(marker, start)
                    if idx != -1 and idx < end:
                        end = idx

                section_text = text[start:end]

                # Extrai bullets
                bullets = re.findall(r'[•\-\*►▸✓]\s*([^\n•\-\*►▸✓]+)', section_text)
                if bullets:
                    responsibilities = [b.strip() for b in bullets if len(b.strip()) > 10]
                else:
                    # Tenta split por nova linha
                    lines = [l.strip() for l in section_text.split('\n') if l.strip() and len(l.strip()) > 15]
                    responsibilities = lines

                break

        # Se não achou seção, procura por bullets no texto todo
        if not responsibilities:
            bullets = re.findall(r'[•\-\*►▸]\s*([^\n•\-\*►▸]{15,120})', text)
            responsibilities = [b.strip() for b in bullets[:8]]

        return responsibilities[:8]
