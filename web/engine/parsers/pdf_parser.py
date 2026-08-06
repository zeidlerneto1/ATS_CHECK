"""
Parser de PDF com fallback: pdfplumber → PyPDF2 → pdfminer
"""
import re
from typing import Dict, Any, Tuple, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.logger import ATSLogger


class PDFParser:
    """Parser de PDF com múltiplas engines e fallback automático"""

    def __init__(self, logger: ATSLogger = None):
        self.logger = logger
        self.engines = []
        self._load_engines()

    def _load_engines(self):
        """Tenta carregar engines na ordem de preferência"""
        engines = []

        try:
            import pdfplumber
            engines.append(("pdfplumber", self._parse_pdfplumber))
        except ImportError:
            pass

        try:
            import PyPDF2
            engines.append(("PyPDF2", self._parse_pypdf2))
        except ImportError:
            pass

        try:
            from pdfminer.high_level import extract_text
            engines.append(("pdfminer", self._parse_pdfminer))
        except ImportError:
            pass

        self.engines = engines

    def parse(self, file_path: str) -> Dict[str, Any]:
        if self.logger:
            self.logger.log("PARSE", "Iniciando parsing de PDF", {
                "file": file_path,
                "engines_available": [e[0] for e in self.engines]
            })

        if not self.engines:
            raise RuntimeError("Nenhum engine de PDF disponível. Instale: pip install pdfplumber PyPDF2 pdfminer.six")

        last_error = None
        for engine_name, engine_func in self.engines:
            try:
                result = engine_func(file_path)
                result["engine_used"] = engine_name

                if self.logger:
                    self.logger.log("PARSE", f"PDF parseado com {engine_name}", {
                        "pages": len(result.get("pages", [])),
                        "chars": len(result["raw_text"]),
                        "engine": engine_name
                    })

                return result
            except Exception as e:
                last_error = e
                if self.logger:
                    self.logger.log("PARSE", f"Falha no {engine_name}", {"error": str(e)}, "WARN")
                continue

        raise RuntimeError(f"Todos os engines falharam. Último erro: {last_error}")

    def _parse_pdfplumber(self, file_path: str) -> Dict[str, Any]:
        import pdfplumber
        raw_text = ""
        pages_text = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
                raw_text += text + "\n"

        return self._build_result(raw_text, pages_text, "pdfplumber", len(pages_text))

    def _parse_pypdf2(self, file_path: str) -> Dict[str, Any]:
        import PyPDF2
        raw_text = ""
        pages_text = []

        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
                raw_text += text + "\n"

        return self._build_result(raw_text, pages_text, "PyPDF2", len(pages_text))

    def _parse_pdfminer(self, file_path: str) -> Dict[str, Any]:
        from pdfminer.high_level import extract_text
        raw_text = extract_text(file_path)
        return self._build_result(raw_text, [raw_text], "pdfminer", 1)

    def _build_result(self, raw_text: str, pages: List[str], engine: str, num_pages: int) -> Dict[str, Any]:
        raw_text = self._clean_text(raw_text)

        # Detecta se é PDF de imagem (texto muito curto)
        is_image_pdf = len(raw_text) < 200 and num_pages > 0

        return {
            "raw_text": raw_text,
            "pages": pages,
            "metadata": {
                "pages": num_pages,
                "engine": engine,
                "is_image_pdf": is_image_pdf,
                "text_length": len(raw_text)
            },
            "file_type": "pdf"
        }

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
