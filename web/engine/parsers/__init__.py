"""
Fábrica de parsers com auto-detecção de formato
"""
import os
from engine.parsers.pdf_parser import PDFParser
from engine.parsers.docx_parser import DOCXParser
from engine.logger import ATSLogger


class DocumentParser:
    """Fábrica que seleciona o parser correto e gerencia logs"""

    def __init__(self, logger: ATSLogger = None):
        self.logger = logger
        self.parsers = {
            '.pdf': PDFParser(logger),
            '.docx': DOCXParser(logger),
        }

    def parse(self, file_path: str) -> dict:
        ext = os.path.splitext(file_path.lower())[1]

        if ext not in self.parsers:
            raise ValueError(f"Formato não suportado: {ext}. Suportados: {list(self.parsers.keys())}")

        if self.logger:
            self.logger.log("INGEST", "Documento recebido", {
                "file": file_path,
                "format": ext,
                "size_bytes": os.path.getsize(file_path)
            })

        return self.parsers[ext].parse(file_path)
