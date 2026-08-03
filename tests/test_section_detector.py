from infrastructure.section_detector import SectionDetector


class TestSectionDetector:
    def setup_method(self):
        self.detector = SectionDetector()

    def test_detect_summary_section(self):
        text = """João Silva
joao@email.com

Resumo Profissional
Desenvolvedor com 5 anos de experiência.

Experiência
Tech BR - Desenvolvedor
jan/2020 - atual"""
        sections = self.detector.detect(text)
        assert len(sections["summary"]) > 0
        assert len(sections["experience"]) > 0

    def test_detect_education_section(self):
        text = """Formação Acadêmica
Universidade de São Paulo
Bacharelado em Ciência da Computação"""
        sections = self.detector.detect(text)
        assert len(sections["education"]) > 0

    def test_detect_skills_section(self):
        text = """Habilidades Técnicas
Python, JavaScript, React, Node.js"""
        sections = self.detector.detect(text)
        assert len(sections["skills"]) > 0

    def test_no_sections(self):
        text = "Apenas um texto sem seções claras."
        sections = self.detector.detect(text)
        assert len(sections["other"]) > 0
        assert all(len(v) == 0 for k, v in sections.items() if k != "other")
