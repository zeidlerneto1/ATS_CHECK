from infrastructure.skill_normalizer import SkillNormalizer


class TestSkillNormalizer:
    def setup_method(self):
        self.normalizer = SkillNormalizer()

    def test_normalize_python(self):
        assert self.normalizer.normalize("python") == "python"
        assert self.normalizer.normalize("Python") == "python"

    def test_normalize_react_aliases(self):
        assert self.normalizer.normalize("react") == "react"
        assert self.normalizer.normalize("reactjs") == "react"
        assert self.normalizer.normalize("react.js") == "react"

    def test_normalize_unknown_skill(self):
        assert self.normalizer.normalize("tecnologia_desconhecida") is None

    def test_extract_skills_from_text(self):
        text = "Trabalhei com Python, Django e React no projeto."
        skills = self.normalizer.extract_skills(text, "experiência")
        normalized = [s["normalized"] for s in skills]
        assert "python" in normalized
        assert "django" in normalized
        assert "react" in normalized

    def test_extract_skills_no_duplicates(self):
        text = "React e reactjs são a mesma coisa."
        skills = self.normalizer.extract_skills(text, "lista")
        normalized = [s["normalized"] for s in skills]
        assert normalized.count("react") == 1

    def test_extract_skills_context(self):
        text = "Experiência com AWS e Docker."
        skills = self.normalizer.extract_skills(text, "experiência")
        assert skills[0]["context"] == "experiência"
