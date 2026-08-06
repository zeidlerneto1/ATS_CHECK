"""
Detecta seções comuns de CVs brasileiros.
"""
import re
from typing import Dict, List


class SectionDetector:
    SECTION_PATTERNS = {
        "summary": [
            r"^resumo\b", r"^sobre\b", r"^perfil\s+profissional",
            r"^objetivo\b", r"^apresentação",
            # English
            r"^summary\b", r"^about\b", r"^professional\s+profile",
            r"^objective\b", r"^profile\b", r"^personal\s+statement",
        ],
        "experience": [
            r"^experiência\b", r"^experiencias\b", r"^histórico\s+profissional",
            r"^histórico\s+de\s+trabalho", r"^atuação\s+profissional",
            # English
            r"^experience\b", r"^experiences\b", r"^professional\s+experience",
            r"^work\s+experience", r"^employment\s+history", r"^career\s+history",
            r"^work\s+history", r"^professional\s+background",
        ],
        "education": [
            r"^formação\b", r"^formação\s+acadêmica", r"^educação\b",
            r"^escolaridade\b", r"^acadêmico\b",
            # English
            r"^education\b", r"^academic\s+background", r"^academic\s+history",
            r"^educational\s+background", r"^qualifications\b",
        ],
        "skills": [
            r"^habilidades\b", r"^competências\b", r"^conhecimentos\b",
            r"^skills\b", r"^tecnologias\b",
            # English
            r"^technical\s+skills", r"^core\s+competencies", r"^key\s+skills",
            r"^technologies\b", r"^tech\s+stack", r"^stack\b",
            r"^tools\b", r"^toolkit\b",
        ],
        "languages": [
            r"^idiomas\b", r"^línguas\b",
            # English
            r"^languages\b", r"^language\s+proficiency",
        ],
        "certifications": [
            r"^certificações\b", r"^certificados\b", r"^cursos\b",
            # English
            r"^certifications\b", r"^certificates\b", r"^courses\b",
            r"^professional\s+certifications", r"^licenses\b",
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
