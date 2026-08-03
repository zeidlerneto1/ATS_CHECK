"""
Normaliza skills tecnológicas comuns no mercado brasileiro.
"""
import re
from typing import Dict, List, Optional


class SkillNormalizer:
    SKILL_ALIASES = {
        "javascript": ["js", "javascript", "ecmascript"],
        "typescript": ["ts", "typescript"],
        "python": ["python", "python3"],
        "java": ["java", "j2ee"],
        "csharp": ["c#", "csharp", ".net", "dotnet", "asp.net"],
        "golang": ["go", "golang"],
        "php": ["php"],
        "ruby": ["ruby", "ruby on rails", "rails"],
        "swift": ["swift"],
        "kotlin": ["kotlin"],
        "rust": ["rust"],
        "scala": ["scala"],
        "elixir": ["elixir"],
        "react": ["react", "reactjs", "react.js"],
        "vue": ["vue", "vuejs", "vue.js"],
        "angular": ["angular", "angularjs", "angular.js"],
        "svelte": ["svelte"],
        "nextjs": ["next.js", "nextjs"],
        "nodejs": ["node", "nodejs", "node.js"],
        "django": ["django"],
        "flask": ["flask"],
        "spring": ["spring", "spring boot", "springboot"],
        "laravel": ["laravel"],
        "express": ["express", "expressjs"],
        "postgresql": ["postgres", "postgresql", "pg"],
        "mysql": ["mysql", "maria db", "mariadb"],
        "mongodb": ["mongo", "mongodb"],
        "redis": ["redis"],
        "elasticsearch": ["elasticsearch", "elastic search", "elastic"],
        "dynamodb": ["dynamodb", "dynamo db"],
        "aws": ["aws", "amazon web services", "amazon aws"],
        "gcp": ["gcp", "google cloud", "google cloud platform"],
        "azure": ["azure", "microsoft azure"],
        "docker": ["docker", "containers"],
        "kubernetes": ["kubernetes", "k8s"],
        "terraform": ["terraform", "tf"],
        "jenkins": ["jenkins", "ci/cd"],
        "github_actions": ["github actions", "gha"],
        "gitlab_ci": ["gitlab ci", "gitlab"],
        "pandas": ["pandas"],
        "numpy": ["numpy"],
        "scikit_learn": ["scikit-learn", "sklearn", "scikitlearn"],
        "tensorflow": ["tensorflow", "tf"],
        "pytorch": ["pytorch", "torch"],
        "git": ["git", "versionamento"],
        "linux": ["linux", "unix"],
        "sql": ["sql", "structured query language"],
        "nosql": ["nosql"],
        "rest_api": ["rest", "restful", "api rest"],
        "graphql": ["graphql"],
        "swagger": ["swagger", "openapi"],
        "postman": ["postman"],
        "figma": ["figma"],
        "jira": ["jira"],
        "trello": ["trello"],
        "agile": ["agile", "ágil", "scrum", "kanban"],
        "tdd": ["tdd", "test driven development"],
        "ddd": ["ddd", "domain driven design"],
        "clean_architecture": ["clean architecture", "clean code", "arquitetura limpa"],
        "microservices": ["microservices", "micro serviços", "microserviços"],
    }
    _alias_to_canonical: Dict[str, str] = {}

    def __init__(self):
        if not self._alias_to_canonical:
            for canonical, aliases in self.SKILL_ALIASES.items():
                for alias in aliases:
                    self._alias_to_canonical[alias.lower()] = canonical

    def normalize(self, skill_name: str) -> Optional[str]:
        normalized = skill_name.lower().strip()
        return self._alias_to_canonical.get(normalized)

    def extract_skills(self, text: str, context: str = "") -> List[Dict[str, str]]:
        found = []
        text_lower = text.lower()
        for canonical, aliases in self.SKILL_ALIASES.items():
            for alias in aliases:
                pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
                if re.search(pattern, text_lower):
                    found.append({
                        "name": alias,
                        "normalized": canonical,
                        "context": context
                    })
                    break
        return found
