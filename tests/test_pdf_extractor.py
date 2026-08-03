import pytest

from infrastructure.pdf_extractor import PdfTextExtractor


class TestPdfTextExtractor:
    def setup_method(self):
        self.extractor = PdfTextExtractor()

    def test_sanitize_filename(self):
        assert self.extractor.sanitize_filename("Meu CV (2024).pdf") == "meu_cv_2024_pdf"
        assert self.extractor.sanitize_filename("currículo@dev.pdf") == "curr_culo_dev_pdf"

    def test_normalize_text(self):
        text = "Linha 1\n\n\n   Linha 2\t\tTexto"
        normalized = self.extractor.normalize_text(text)
        assert "\n\n" in normalized
        assert "\t" not in normalized

    def test_validate_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            self.extractor.validate("/caminho/inexistente.pdf")

    def test_validate_large_file(self, tmp_path):
        large_file = tmp_path / "large.pdf"
        large_file.write_bytes(b"x" * (6 * 1024 * 1024))
        with pytest.raises(ValueError, match="excede limite"):
            self.extractor.validate(str(large_file))
