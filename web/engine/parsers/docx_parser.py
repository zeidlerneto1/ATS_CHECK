"""
Parser de DOCX
"""
import re
from typing import Dict, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.logger import ATSLogger


class DOCXParser:
    def __init__(self, logger: ATSLogger = None):
        self.logger = logger

    def parse(self, file_path: str) -> Dict[str, Any]:
        if self.logger:
            self.logger.log("PARSE", "Iniciando parsing de DOCX", {"file": file_path})

        try:
            from docx import Document
        except ImportError:
            raise RuntimeError("python-docx não instalado. Execute: pip install python-docx")

        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        raw_text = "\n".join(paragraphs)

        # Extrai tabelas também
        tables_text = []
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text for cell in row.cells])
                tables_text.append(row_text)

        if tables_text:
            raw_text += "\n\n[TABELAS]\n" + "\n".join(tables_text)

        raw_text = self._clean_text(raw_text)

        if self.logger:
            self.logger.log("PARSE", "DOCX parseado com sucesso", {
                "paragraphs": len(paragraphs),
                "tables": len(doc.tables),
                "chars": len(raw_text)
            })

        return {
            "raw_text": raw_text,
            "pages": [raw_text],
            "metadata": {
                "paragraphs": len(paragraphs),
                "tables": len(doc.tables),
                "engine": "python-docx"
            },
            "file_type": "docx"
        }

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
