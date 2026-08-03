from domain.entities import Resume, Skill
from infrastructure.spacy_parser import SpacyPdfParser


class TestIntegration:
    def test_end_to_end_with_mock_text(self):
        parser = SpacyPdfParser()
        mock_text = """
        João Silva
        joao.silva@email.com.br
        (11) 98765-4321
        São Paulo, SP

        Resumo Profissional
        Desenvolvedor Full Stack com experiência em Python e React.

        Experiência
        Tech Solutions Brasil - Desenvolvedor Sênior
        mar/2020 - atual
        Desenvolvimento de aplicações web com Django e React.

        Formação
        Universidade de São Paulo
        Bacharelado em Ciência da Computação
        2015 - 2019

        Habilidades
        Python, JavaScript, React, Django, PostgreSQL, Docker, AWS
        """
        sections = parser.section_detector.detect(mock_text)
        assert len(sections["summary"]) > 0
        assert len(sections["experience"]) > 0
        assert len(sections["education"]) > 0
        assert len(sections["skills"]) > 0

        email = parser._extract_email(mock_text)
        assert email == "joao.silva@email.com.br"

        phone = parser._extract_phone(mock_text)
        assert phone is not None

        skills = parser._extract_all_skills(sections, mock_text)
        normalized_skills = [s.normalized for s in skills]
        assert "python" in normalized_skills
        assert "react" in normalized_skills

        experiences = parser._parse_experiences(sections["experience"], mock_text)
        assert len(experiences) > 0
        assert experiences[0].is_current is True
        assert experiences[0].company == "Tech Solutions Brasil"

        resume = Resume(
            full_name="João Silva",
            email=email,
            phone=phone,
            experiences=experiences,
            skills=skills
        )
        confidence = parser._calculate_confidence(resume, [])
        assert confidence > 0.7
