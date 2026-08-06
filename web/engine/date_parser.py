"""
Parser de datas brasileiras — múltiplos formatos
"""
import re
from datetime import datetime
from typing import Optional, Dict

MONTH_MAP = {
    "jan": 1, "jan.": 1, "janeiro": 1,
    "fev": 2, "fev.": 2, "fevereiro": 2,
    "mar": 3, "mar.": 3, "março": 3, "marco": 3,
    "abr": 4, "abr.": 4, "abril": 4,
    "mai": 5, "mai.": 5, "maio": 5,
    "jun": 6, "jun.": 6, "junho": 6,
    "jul": 7, "jul.": 7, "julho": 7,
    "ago": 8, "ago.": 8, "agosto": 8,
    "set": 9, "set.": 9, "setembro": 9,
    "out": 10, "out.": 10, "outubro": 10,
    "nov": 11, "nov.": 11, "novembro": 11,
    "dez": 12, "dez.": 12, "dezembro": 12,
}

CURRENT_TERMS = {"atual", "atualmente", "presente", "hoje", "current", "now", "ongoing"}


class DateParser:
    """Parser robusto de datas em CVs brasileiros"""

    # Padrões de data suportados
    DATE_PATTERNS = [
        # MM/AAAA ou DD/MM/AAAA
        (r'(?:(\d{1,2})[\/\-])?(\d{4})', 'numeric'),
        # Mês por extenso + ano: jan/2024, janeiro 2024, jan. 2024
        (r'(\w{3,})[\s\/\-]?(\d{4})', 'text'),
        # Ano isolado: 2024
        (r'\b(\d{4})\b', 'year_only'),
    ]

    RANGE_PATTERNS = [
        # MM/AAAA - MM/AAAA ou MM/AAAA — Atual
        r'(\d{1,2}[\/\-]\d{4})\s*[-—–]\s*(\d{1,2}[\/\-]\d{4}|atual|presente|hoje)',
        # Mês/Ano - Mês/Ano
        r'(\w{3,}\.?\s*\/?\s*\d{4})\s*[-—–]\s*(\w{3,}\.?\s*\/?\s*\d{4}|atual|presente|hoje)',
        # Ano - Ano
        r'(\d{4})\s*[-—–]\s*(\d{4}|atual|presente|hoje)',
    ]

    def parse_month_year(self, text: str) -> Optional[Dict]:
        """Extrai mês e ano de uma string"""
        text = text.lower().strip()

        # Tentar MM/AAAA ou DD/MM/AAAA
        m = re.match(r'^(\d{1,2})[\/\-](\d{4})$', text)
        if m:
            month = int(m.group(1))
            year = int(m.group(2))
            if 1 <= month <= 12 and 1900 <= year <= 2100:
                return {"month": month, "year": year, "format": "MM/AAAA"}

        # Tentar mês por extenso
        m = re.match(r'^(\w{3,})[\s\/\-]?(\d{4})$', text)
        if m:
            month_str = m.group(1).lower()
            year = int(m.group(2))
            if month_str in MONTH_MAP and 1900 <= year <= 2100:
                return {"month": MONTH_MAP[month_str], "year": year, "format": "texto"}

        # Tentar ano isolado
        m = re.match(r'^(\d{4})$', text)
        if m:
            year = int(m.group(1))
            if 1900 <= year <= 2100:
                return {"month": None, "year": year, "format": "ano"}

        return None

    def parse_range(self, text: str) -> Optional[Dict]:
        """Extrai intervalo de datas (início e fim)"""
        text_lower = text.lower()

        for pattern in self.RANGE_PATTERNS:
            m = re.search(pattern, text_lower, re.IGNORECASE)
            if m:
                start_str = m.group(1).strip()
                end_str = m.group(2).strip()

                start = self.parse_month_year(start_str)
                end = self.parse_month_year(end_str) if end_str.lower() not in CURRENT_TERMS else {
                    "month": datetime.now().month,
                    "year": datetime.now().year,
                    "format": "atual",
                    "is_current": True
                }

                if start and end:
                    return {
                        "start": start,
                        "end": end,
                        "raw": m.group(0),
                        "duration_months": self._calc_duration(start, end)
                    }
        return None

    def _calc_duration(self, start: Dict, end: Dict) -> int:
        """Calcula duração em meses"""
        sm = start.get("month") or 1
        sy = start["year"]
        em = end.get("month") or 12
        ey = end["year"]
        return (ey - sy) * 12 + (em - sm) + 1

    def find_dates_in_text(self, text: str) -> list:
        """Encontra todas as datas/intervalos em um texto"""
        found = []
        for pattern in self.RANGE_PATTERNS:
            for m in re.finditer(pattern, text.lower(), re.IGNORECASE):
                result = self.parse_range(m.group(0))
                if result:
                    found.append(result)
        return found

    def is_current(self, text: str) -> bool:
        """Verifica se uma data indica 'atual'"""
        return any(term in text.lower() for term in CURRENT_TERMS)
