import pytest
from datetime import date

from infrastructure.date_parser import BrazilianDateParser


class TestBrazilianDateParser:
    def setup_method(self):
        self.parser = BrazilianDateParser()

    def test_parse_jan_2022(self):
        start, end, current = self.parser.parse("jan/2022")
        assert start == date(2022, 1, 1)
        assert end is None
        assert current is False

    def test_parse_janeiro_de_2023(self):
        start, end, current = self.parser.parse("janeiro de 2023")
        assert start == date(2023, 1, 1)

    def test_parse_range_mar_2022_dez_2023(self):
        start, end, current = self.parser.parse("mar 2022 - dez 2023")
        assert start == date(2022, 3, 1)
        assert end == date(2023, 12, 1)
        assert current is False

    def test_parse_2022_atual(self):
        start, end, current = self.parser.parse("2022 - atual")
        assert start == date(2022, 1, 1)
        assert end is None
        assert current is True

    def test_parse_2022_presente(self):
        start, end, current = self.parser.parse("2022 - presente")
        assert current is True

    def test_parse_desde_2022(self):
        start, end, current = self.parser.parse("desde 2022")
        assert start == date(2022, 1, 1)
        assert current is True

    def test_parse_range_com_ano(self):
        start, end, current = self.parser.parse("2020 - 2022")
        assert start == date(2020, 1, 1)
        assert end == date(2022, 1, 1)

    def test_parse_invalid_date(self):
        start, end, current = self.parser.parse("data desconhecida")
        assert start is None
        assert end is None
        assert current is False

    def test_calculate_duration_24_months(self):
        start = date(2022, 1, 1)
        end = date(2024, 1, 1)
        duration = self.parser.calculate_duration(start, end, False)
        assert duration == 24

    def test_calculate_duration_current(self):
        start = date(2022, 1, 1)
        duration = self.parser.calculate_duration(start, None, True)
        assert duration > 0
