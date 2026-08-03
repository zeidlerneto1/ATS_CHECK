#!/usr/bin/env python3
"""
CLI mínimo para testar parsing de PDFs.
Uso: python cli.py <caminho_do_pdf> [--json]
"""
import sys
import json
from pathlib import Path

from infrastructure.spacy_parser import SpacyPdfParser


def main():
    if len(sys.argv) < 2:
        print("Uso: python cli.py <caminho_do_pdf>")
        print("Exemplo: python cli.py ./curriculos/joao_silva.pdf")
        print("Opções:")
        print("  --json    Exporta resultado para arquivo JSON")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"Erro: Arquivo não encontrado: {file_path}")
        sys.exit(1)

    print(f"🔍 Analisando: {file_path}")
    print("=" * 60)

    try:
        parser = SpacyPdfParser()
        result = parser.parse(file_path)

        print(f"\n📊 Confidence Score: {result.confidence_score:.2f}")
        print(f"✅ Usável: {'Sim' if result.is_usable else 'Não'}")

        print(f"\n👤 Nome: {result.resume.full_name or 'Não detectado'}")
        print(f"📧 Email: {result.resume.email or 'Não detectado'}")
        print(f"📱 Telefone: {result.resume.phone or 'Não detectado'}")
        print(f"📍 Localização: {result.resume.city or 'N/A'}, {result.resume.state or 'N/A'}")

        print(f"\n💼 Experiências ({len(result.resume.experiences)}):")
        for exp in result.resume.experiences:
            current = " (atual)" if exp.is_current else ""
            print(f"  • {exp.role or 'Cargo não detectado'} @ {exp.company or 'Empresa não detectada'}{current}")
            if exp.start_date:
                end = exp.end_date.strftime("%m/%Y") if exp.end_date else "atual"
                print(f"    {exp.start_date.strftime('%m/%Y')} - {end} | {exp.duration_months or 0} meses")

        print(f"\n🎓 Formação ({len(result.resume.education)}):")
        for edu in result.resume.education:
            print(f"  • {edu.degree or 'Curso não detectado'} - {edu.institution or 'Instituição não detectada'}")

        print(f"\n🛠️ Skills ({len(result.resume.skills)}):")
        for skill in result.resume.skills:
            print(f"  • {skill.normalized or skill.name} ({skill.context})")

        print(f"\n📅 Tempo Total de Experiência: {result.resume.total_experience_months or 0} meses")

        if result.warnings:
            print(f"\n⚠️ Warnings ({len(result.warnings)}):")
            for w in result.warnings:
                icon = "🔴" if w.severity.value == "critical" else "🟡" if w.severity.value == "warning" else "🔵"
                print(f"  {icon} [{w.severity.value.upper()}] {w.field}: {w.message}")

        if "--json" in sys.argv:
            output_path = Path(file_path).with_suffix(".parsed.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({
                    "confidence_score": result.confidence_score,
                    "is_usable": result.is_usable,
                    "resume": {
                        "full_name": result.resume.full_name,
                        "email": result.resume.email,
                        "phone": result.resume.phone,
                        "city": result.resume.city,
                        "state": result.resume.state,
                        "summary": result.resume.summary,
                        "objective": result.resume.objective,
                        "total_experience_months": result.resume.total_experience_months,
                        "experiences": [
                            {
                                "company": e.company,
                                "role": e.role,
                                "start_date": e.start_date.isoformat() if e.start_date else None,
                                "end_date": e.end_date.isoformat() if e.end_date else None,
                                "is_current": e.is_current,
                                "duration_months": e.duration_months,
                            }
                            for e in result.resume.experiences
                        ],
                        "education": [
                            {
                                "institution": e.institution,
                                "degree": e.degree,
                                "field_of_study": e.field_of_study,
                            }
                            for e in result.resume.education
                        ],
                        "skills": [
                            {"name": s.name, "normalized": s.normalized, "context": s.context}
                            for s in result.resume.skills
                        ],
                    },
                    "warnings": [
                        {"severity": w.severity.value, "field": w.field, "message": w.message}
                        for w in result.warnings
                    ]
                }, f, ensure_ascii=False, indent=2)
            print(f"\n💾 JSON exportado para: {output_path}")

    except Exception as e:
        print(f"\n❌ Erro durante o parsing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
