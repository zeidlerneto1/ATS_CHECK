"""
Detecta seções comuns de CVs brasileiros.
"""
import re
from typing import Dict, List


class SectionDetector:
    SECTION_PATTERNS = {
        "summary": [
            r"^resumo\b", r"^sobre\b", r"^perfil\s+profissional",
            r"^objetivo\b", r"^apresentação"
        ],
        "experience": [
            r"^experiência\b", r"^experiencias\b", r"^histórico\s+profissional",
            r"^histórico\s+de\s+trabalho", r"^atuação\s+profissional"
        ],
        "education": [
            r"^formação\b", r"^formação\s+acadêmica", r"^educação\b",
            r"^escolaridade\b", r"^acadêmico\b"
        ],
        "skills": [
            r"^habilidades\b", r"^competências\b", r"^conhecimentos\b",
            r"^skills\b", r"^tecnologias\b"
        ],
        "languages": [
            r"^idiomas\b", r"^línguas\b"
        ],
        "certifications": [
            r"^certificações\b", r"^certificados\b", r"^cursos\b"
        ]
    }

    def detect(self, text: str) -> Dict[str, List[str]]:
        lines = text.split("\n")
        sections: Dict[str, List[str]] = {key: [] for key in self.SECTION_PATTERNS}
        sections["other"] = []
        current_section = "other"
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            for section_name, patterns in self.SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, stripped, re.IGNORECASE):
                        current_section = section_name
                        break
            sections[current_section].append(stripped)
        return sections
