"""
Parser de datas em formatos brasileiros variados.
"""
import re
from datetime import date, datetime
from typing import Optional, Tuple


class BrazilianDateParser:
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

    CURRENT_TERMS = {"atual", "atualmente", "presente", "hoje", "atualidade", "agora"}

    def parse(self, date_str: str) -> Tuple[Optional[date], Optional[date], bool]:
        if not date_str:
            return None, None, False
        date_str = date_str.lower().strip()
        range_patterns = [
            r"(\w{3,}\.?\s*\/?\s*\d{4})\s*[-—]\s*(\w{3,}\.?\s*\/?\s*\d{4}|atual(?:mente)?|presente|hoje)",
            r"(\d{4})\s*[-—]\s*(\d{4}|atual(?:mente)?|presente|hoje)",
            r"desde\s+(\w{3,}\.?\s*\/?\s*\d{4})",
        ]
        for pattern in range_patterns:
            match = re.search(pattern, date_str)
            if match:
                start_raw = match.group(1)
                end_raw = match.group(2) if len(match.groups()) > 1 else None
                start_date = self._parse_single_date(start_raw)
                is_current = False
                end_date = None
                if end_raw:
                    if any(term in end_raw for term in self.CURRENT_TERMS):
                        is_current = True
                    else:
                        end_date = self._parse_single_date(end_raw)
                else:
                    is_current = True
                return start_date, end_date, is_current
        single_date = self._parse_single_date(date_str)
        if single_date:
            return single_date, None, False
        return None, None, False

    def _parse_single_date(self, date_str: str) -> Optional[date]:
        date_str = date_str.lower().strip()
        patterns = [
            r"(\w{3,})\s*[/.-]?\s*(\d{4})",
            r"(\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    month_str, year_str = groups
                    month = self.MONTH_MAP.get(month_str.replace(".", "").strip())
                    if month:
                        try:
                            return date(int(year_str), month, 1)
                        except ValueError:
                            continue
                elif len(groups) == 1:
                    try:
                        return date(int(groups[0]), 1, 1)
                    except ValueError:
                        continue
        return None

    def calculate_duration(self, start: date, end: Optional[date], is_current: bool) -> int:
        if not start:
            return 0
        end = end or (datetime.now().date() if is_current else start)
        months = (end.year - start.year) * 12 + (end.month - start.month)
        return max(0, months)
