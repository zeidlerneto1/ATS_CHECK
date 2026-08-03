"""
Passo C - Extração de Texto Bruto de PDFs
"""
import re
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import pdfplumber


class PdfTextExtractor:
    MAX_SIZE_MB = 5
    ALLOWED_MIMETYPES = {"application/pdf"}

    def __init__(self):
        self.warnings: List[Dict[str, str]] = []

    def validate(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_SIZE_MB:
            raise ValueError(
                f"Arquivo excede limite de {self.MAX_SIZE_MB}MB ({size_mb:.2f}MB)"
            )
        mime, _ = mimetypes.guess_type(str(path))
        if mime not in self.ALLOWED_MIMETYPES:
            raise ValueError(f"MIME type não suportado: {mime}")

    def extract(self, file_path: str) -> Tuple[str, List[Dict[str, str]]]:
        self.warnings = []
        self.validate(file_path)
        raw_text = ""
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text or len(text.strip()) < 50:
                    self.warnings.append({
                        "severity": "warning",
                        "field": f"page_{i + 1}",
                        "message": "Página com pouco ou nenhum texto extraível - possível imagem ou scan"
                    })
                    continue
                lines = text.split("\n")
                short_lines = sum(1 for l in lines if len(l.strip()) < 30)
                if short_lines / max(len(lines), 1) > 0.6:
                    self.warnings.append({
                        "severity": "info",
                        "field": "layout",
                        "message": "Possível layout de duas colunas detectado"
                    })
                non_text_ratio = sum(
                    1 for c in text if ord(c) > 127 and not c.isalpha()
                ) / max(len(text), 1)
                if non_text_ratio > 0.15:
                    self.warnings.append({
                        "severity": "warning",
                        "field": "content",
                        "message": "Alta presença de caracteres não-textuais - possíveis elementos gráficos"
                    })
                raw_text += text + "\n"
        if not raw_text.strip():
            raise ValueError("Não foi possível extrair texto do PDF")
        return raw_text, self.warnings

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        sanitized = re.sub(r"[^\w\-_.]", "_", filename)
        sanitized = re.sub(r"_{2,}", "_", sanitized)
        return sanitized.lower().strip("_")

    @staticmethod
    def normalize_text(text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", text)
        return text.strip()
