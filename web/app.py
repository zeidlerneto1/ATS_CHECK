#!/usr/bin/env python3
"""
API Flask - ATS Web com streaming de logs e vaga personalizada
"""
import os
import re
import sys
import json
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.ats_engine import ATSEngine, JobDescription
from engine.job_scraper import JobScraper
from engine.job_text_parser import JobTextParser
from engine.logger import ATSLogger

# ONDA 3: Detecção de ATS por URL
ATS_PATTERNS = {
    "greenhouse": {
        "patterns": [r"greenhouse\.io", r"boards\.greenhouse"],
        "name": "Greenhouse",
        "tips": "Use keywords exatas da vaga. Greenhouse faz matching literal.",
        "format_preference": "PDF ou DOCX",
    },
    "workday": {
        "patterns": [r"myworkday\.com", r"workday\.com"],
        "name": "Workday",
        "tips": "Workday usa ML/NER. Use formato MM/AAAA para datas e seções claras.",
        "format_preference": "DOCX (metadados core.xml são lidos)",
    },
    "gupy": {
        "patterns": [r"gupy\.io", r"portal\.gupy"],
        "name": "Gupy",
        "tips": "Gupy é brasileiro e valoriza PT-BR. Use datas no formato DD/MM/AAAA.",
        "format_preference": "PDF ou DOCX",
    },
    "lever": {
        "patterns": [r"lever\.co", r"jobs\.lever"],
        "name": "Lever",
        "tips": "Lever aceita upload direto. Use 1-2 páginas máximo.",
        "format_preference": "PDF",
    },
    "linkedin": {
        "patterns": [r"linkedin\.com/jobs", r"linkedin\.com/in"],
        "name": "LinkedIn Easy Apply",
        "tips": "Easy Apply usa o perfil LinkedIn como CV. Mantenha perfil atualizado.",
        "format_preference": "Perfil LinkedIn",
    },
    "indeed": {
        "patterns": [r"indeed\.com", r"indeed\.com.br"],
        "name": "Indeed",
        "tips": "Indeed extrai texto puro. Evite PDFs com imagens ou colunas.",
        "format_preference": "DOCX",
    },
    "bamboohr": {
        "patterns": [r"bamboohr\.com", r"bamboo\.hr"],
        "name": "BambooHR",
        "tips": "BambooHR é simples. Foque em keywords e experiência relevante.",
        "format_preference": "PDF",
    },
    "recruitee": {
        "patterns": [r"recruitee\.com"],
        "name": "Recruitee",
        "tips": "Recruitee faz parsing semântico. Use bullets com verbos de ação.",
        "format_preference": "PDF ou DOCX",
    },
}

def detect_ats_platform(url: str) -> dict:
    """Detecta qual ATS a empresa usa baseado na URL da vaga"""
    url_lower = url.lower()
    for ats_id, ats_data in ATS_PATTERNS.items():
        for pattern in ats_data["patterns"]:
            if re.search(pattern, url_lower):
                return {
                    "id": ats_id,
                    "name": ats_data["name"],
                    "tips": ats_data["tips"],
                    "format_preference": ats_data["format_preference"],
                    "detected": True,
                }
    return {
        "id": "unknown",
        "name": "ATS Desconhecido",
        "tips": "Use formato padrão: single-column, sem imagens, texto selecionável.",
        "format_preference": "PDF ou DOCX",
        "detected": False,
    }

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Vagas pré-configuradas
JOBS = {
    "fullstack_junior": JobDescription(
        title="Desenvolvedor Full Stack Júnior/Pleno",
        company="TechCorp",
        required_skills=["node.js", "express", "react", "javascript", "typescript",
                        "postgresql", "sql", "rest", "git", "docker"],
        preferred_skills=["python", "flask", "jwt", "rbac", "ci/cd", "github actions",
                         "vtk.js", "knex.js", "mysql"],
        required_experience_years=1,
        education_level="tecnico",
        responsibilities=[
            "Desenvolver aplicações web full stack com Node.js e React",
            "Criar APIs RESTful com Express e autenticação JWT",
            "Implementar interfaces responsivas com React.js",
            "Gerenciar banco de dados PostgreSQL com queries otimizadas",
            "Realizar deploy e manutenção com Docker",
        ]
    ),
    "backend_senior": JobDescription(
        title="Desenvolvedor Backend Sênior",
        company="TechCorp",
        required_skills=["python", "django", "rest", "sql", "postgresql",
                        "docker", "git", "linux"],
        preferred_skills=["kubernetes", "aws", "ci/cd", "redis", "fastapi",
                         "graphql", "microservices", "kafka", "terraform"],
        required_experience_years=5,
        education_level="graduacao",
        responsibilities=[
            "Desenvolver APIs RESTful escaláveis",
            "Otimizar queries de banco de dados",
            "Implementar pipelines CI/CD",
            "Realizar code reviews",
            "Mentorar desenvolvedores júnior",
        ]
    ),
    "devops": JobDescription(
        title="DevOps Engineer",
        company="CloudCorp",
        required_skills=["docker", "kubernetes", "aws", "ci/cd", "linux", "terraform"],
        preferred_skills=["ansible", "jenkins", "github actions", "prometheus", "grafana"],
        required_experience_years=3,
        education_level="graduacao",
        responsibilities=[
            "Gerenciar infraestrutura em nuvem AWS",
            "Implementar pipelines CI/CD",
            "Orquestrar containers com Kubernetes",
            "Monitorar aplicações e infraestrutura",
        ]
    ),
    "frontend_react": JobDescription(
        title="Frontend React Developer",
        company="WebCorp",
        required_skills=["react", "javascript", "typescript", "html", "css", "git"],
        preferred_skills=["next.js", "redux", "tailwind", "jest", "webpack", "graphql"],
        required_experience_years=2,
        education_level="tecnico",
        responsibilities=[
            "Desenvolver interfaces com React.js",
            "Implementar componentes reutilizáveis",
            "Integrar com APIs RESTful e GraphQL",
            "Garantir responsividade e acessibilidade",
            "Escrever testes unitários e de integração",
        ]
    ),
    "data_engineer": JobDescription(
        title="Data Engineer",
        company="DataCorp",
        required_skills=["python", "sql", "postgresql", "docker", "git", "aws"],
        preferred_skills=["spark", "kafka", "airflow", "dbt", "snowflake", "terraform"],
        required_experience_years=3,
        education_level="graduacao",
        responsibilities=[
            "Construir pipelines de dados escaláveis",
            "Modelar bancos de dados analíticos",
            "Implementar ETL/ELT com Python e SQL",
            "Gerenciar infraestrutura de dados na nuvem",
            "Garantir qualidade e governança de dados",
        ]
    ),
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/logs")
def logs_page():
    return render_template("logs.html")

@app.route("/api/jobs")
def get_jobs():
    """Retorna todas as vagas pré-configuradas para preview"""
    jobs_data = {}
    for key, job in JOBS.items():
        jobs_data[key] = {
            "title": job.title,
            "company": job.company,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "required_experience_years": job.required_experience_years,
            "education_level": job.education_level,
            "responsibilities": job.responsibilities,
        }
    return jsonify(jobs_data)

def _parse_job_from_request() -> JobDescription:
    """Extrai JobDescription do request (preset ou custom)"""
    job_type = request.form.get("job_type", "preset")

    if job_type == "preset":
        job_key = request.form.get("job", "fullstack_junior")
        if job_key not in JOBS:
            raise ValueError(f"Vaga não encontrada: {job_key}")
        return JOBS[job_key]

    # Vaga personalizada
    title = request.form.get("custom_title", "Vaga Personalizada").strip()
    company = request.form.get("custom_company", "Empresa").strip()

    # Parse skills (separadas por vírgula, nova linha ou ponto-e-vírgula)
    required_raw = request.form.get("custom_required", "")
    required_skills = [s.strip().lower() for s in re.split(r'[,;\n]', required_raw) if s.strip()]

    preferred_raw = request.form.get("custom_preferred", "")
    preferred_skills = [s.strip().lower() for s in re.split(r'[,;\n]', preferred_raw) if s.strip()]

    exp_years = int(request.form.get("custom_exp", "0") or "0")
    edu_level = request.form.get("custom_edu", "tecnico")
    # Mapeia valores antigos para novos
    edu_map = {
        "tecnico": "tecnico",
        "tecnologo": "tecnologo",
        "graduacao": "graduacao",
        "mestrado": "mestrado",
        "phd": "phd"
    }
    edu_level = edu_map.get(edu_level, edu_level)

    resp_raw = request.form.get("custom_resp", "")
    responsibilities = [r.strip() for r in resp_raw.split("\n") if r.strip()]

    return JobDescription(
        title=title,
        company=company,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        required_experience_years=exp_years,
        education_level=edu_level,
        responsibilities=responsibilities
    )

@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "cv" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["cv"]
    if file.filename == "":
        return jsonify({"error": "Arquivo vazio"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ['.pdf', '.docx']:
        return jsonify({"error": f"Formato não suportado: {ext}"}), 400

    try:
        job = _parse_job_from_request()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    engine = ATSEngine()
    logs_buffer = []

    def log_callback(entry):
        logs_buffer.append({
            "timestamp": entry.timestamp,
            "stage": entry.stage,
            "stage_name": ATSLogger.STAGES.get(entry.stage, entry.stage),
            "action": entry.action,
            "details": entry.details,
            "severity": entry.severity,
        })

    result = engine.analyze(filepath, job, log_callback)

    # Dados extras para o modo debug/logger
    extra = engine.get_debug_data() if hasattr(engine, 'get_debug_data') else {}

    # Dados enriquecidos da Onda 1
    debug = engine.get_debug_data()

    return jsonify({
        "success": True,
        "job": {
            "title": result.job_title,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
        },
        "result": {
            "candidate_name": result.candidate_name,
            "job_title": result.job_title,
            "overall_score": result.overall_score,
            "skill_match_score": result.skill_match_score,
            "experience_score": result.experience_score,
            "education_score": result.education_score,
            "formatting_score": result.formatting_score,
            "semantic_score": result.semantic_score,
            "keyword_density_score": result.keyword_density_score,
            "matched_keywords": result.matched_keywords,
            "missing_keywords": result.missing_keywords,
            "red_flags": result.red_flags,
            "recommendations": result.recommendations,
        },
        "logs": logs_buffer,
        "raw_text_preview": result.raw_text[:500] + "..." if len(result.raw_text) > 500 else result.raw_text,
        "raw_text": result.raw_text,
        "debug": {
            **debug,
            "metadata": debug.get("parsed_metadata", {}),
            "file_type": debug.get("file_type", "unknown"),
            "semantic_clusters": debug.get("semantic_clusters", []),
            "career_gaps": debug.get("career_gaps", []),
            "bullet_analysis": debug.get("bullet_analysis", []),
            "bilingual_bonus": debug.get("bilingual_bonus", 0),
            "context_bleed": debug.get("context_bleed", []),
            # Cap. 2, 6, 9, 15
            "bom_detected": debug.get("bom_detected", False),
            "white_fonting": debug.get("white_fonting", []),
            "copied_bullets": debug.get("copied_bullets", []),
            "too_good_to_be_true": debug.get("too_good_to_be_true", []),
            "code_switching_issues": debug.get("code_switching_issues", []),
            "recruiter_view": debug.get("recruiter_view", {}),
            "file_format_issues": debug.get("file_format_issues", []),
        },
    })

@app.route("/api/detect-ats", methods=["POST"])
def detect_ats():
    """Detecta qual ATS a empresa usa pela URL"""
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"success": False, "error": "URL não fornecida"}), 400
    url = data["url"].strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"success": False, "error": "URL inválida"}), 400
    result = detect_ats_platform(url)
    return jsonify({"success": True, "ats": result})

@app.route("/api/scrape", methods=["POST"])
def scrape_job():
    """Extrai dados de uma URL de vaga"""
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"success": False, "error": "URL não fornecida"}), 400

    url = data["url"].strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"success": False, "error": "URL inválida"}), 400

    scraper = JobScraper()
    result = scraper.scrape(url)
    return jsonify(result)

@app.route("/api/parse-text", methods=["POST"])
def parse_job_text():
    """Extrai dados de vaga a partir de texto colado"""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"success": False, "error": "Texto não fornecido"}), 400

    text = data["text"].strip()
    if len(text) < 50:
        return jsonify({"success": False, "error": "Texto muito curto. Cole a descrição completa da vaga."}), 400

    parser = JobTextParser()
    result = parser.parse(text)
    return jsonify(result)

@app.route("/ab-test")
def ab_test_page():
    return render_template("ab_test.html")

@app.route("/api/ab-test", methods=["POST"])
def ab_test():
    """Compara 2 CVs na mesma vaga"""
    if "cv_a" not in request.files or "cv_b" not in request.files:
        return jsonify({"error": "Envie 2 CVs (cv_a e cv_b)"}), 400

    file_a = request.files["cv_a"]
    file_b = request.files["cv_b"]
    if file_a.filename == "" or file_b.filename == "":
        return jsonify({"error": "Arquivos vazios"}), 400

    try:
        job = _parse_job_from_request()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    results = {}
    for label, file in [("A", file_a), ("B", file_b)]:
        ext = Path(file.filename).suffix.lower()
        if ext not in ['.pdf', '.docx']:
            return jsonify({"error": f"Formato não suportado em CV {label}: {ext}"}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"ab_{label}_{filename}")
        file.save(filepath)

        engine = ATSEngine()
        result = engine.analyze(filepath, job)
        results[label] = {
            "filename": file.filename,
            "overall_score": result.overall_score,
            "skill_match_score": result.skill_match_score,
            "experience_score": result.experience_score,
            "education_score": result.education_score,
            "formatting_score": result.formatting_score,
            "semantic_score": result.semantic_score,
            "matched_keywords": result.matched_keywords,
            "missing_keywords": result.missing_keywords,
            "red_flags": result.red_flags,
            "recommendations": result.recommendations,
            "candidate_name": result.candidate_name,
        }

    # Determine winner
    score_a = results["A"]["overall_score"]
    score_b = results["B"]["overall_score"]
    winner = "A" if score_a > score_b else "B" if score_b > score_a else "tie"
    diff = abs(score_a - score_b)

    return jsonify({
        "success": True,
        "job_title": job.title,
        "cv_a": results["A"],
        "cv_b": results["B"],
        "winner": winner,
        "difference": round(diff, 1),
        "analysis": {
            "skill_diff": round(results["A"]["skill_match_score"] - results["B"]["skill_match_score"], 1),
            "exp_diff": round(results["A"]["experience_score"] - results["B"]["experience_score"], 1),
            "edu_diff": round(results["A"]["education_score"] - results["B"]["education_score"], 1),
            "format_diff": round(results["A"]["formatting_score"] - results["B"]["formatting_score"], 1),
            "semantic_diff": round(results["A"]["semantic_score"] - results["B"]["semantic_score"], 1),
        }
    })

# ONDA 3: Relatório em HTML otimizado para impressão
@app.route("/api/report", methods=["POST"])
def generate_report():
    """Gera relatório HTML otimizado para impressão (Ctrl+P → PDF)"""
    data = request.get_json()
    if not data or "result" not in data:
        return jsonify({"success": False, "error": "Dados da análise não fornecidos"}), 400

    r = data["result"]
    job = data.get("job", {})
    debug = data.get("debug", {})

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório ATS - {r.get('candidate_name', 'Candidato')}</title>
<style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 800px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #4f46e5; border-bottom: 3px solid #4f46e5; padding-bottom: 10px; }}
h2 {{ color: #4338ca; margin-top: 30px; font-size: 1.2rem; }}
.score-box {{ display: inline-block; padding: 20px 40px; border-radius: 12px; background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; font-size: 2.5rem; font-weight: 700; text-align: center; margin: 20px 0; }}
.score-label {{ font-size: 0.9rem; opacity: 0.9; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0; }}
.card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }}
.card h3 {{ margin: 0 0 8px; font-size: 0.9rem; color: #64748b; text-transform: uppercase; }}
.card .value {{ font-size: 1.5rem; font-weight: 700; color: #4f46e5; }}
.badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }}
.badge-success {{ background: #dcfce7; color: #166534; }}
.badge-warning {{ background: #fef3c7; color: #92400e; }}
.badge-danger {{ background: #fee2e2; color: #991b1b; }}
.keyword {{ display: inline-block; padding: 3px 10px; margin: 3px; border-radius: 4px; font-size: 0.8rem; }}
.keyword-match {{ background: #dcfce7; color: #166534; }}
.keyword-missing {{ background: #fee2e2; color: #991b1b; }}
.recommendation {{ padding: 10px 14px; margin: 6px 0; background: #eff6ff; border-left: 3px solid #3b82f6; border-radius: 0 6px 6px 0; font-size: 0.9rem; }}
.red-flag {{ padding: 10px 14px; margin: 6px 0; background: #fef2f2; border-left: 3px solid #ef4444; border-radius: 0 6px 6px 0; font-size: 0.9rem; }}
.footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 0.8rem; color: #94a3b8; }}
@media print {{ body {{ padding: 0; }} .no-print {{ display: none; }} }}
</style>
</head>
<body>
<h1>🤖 Relatório ATS Simulator</h1>
<p><strong>Candidato:</strong> {r.get('candidate_name', 'Não detectado')}<br>
<strong>Vaga:</strong> {job.get('title', '—')}<br>
<strong>Data:</strong> {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}</p>

<div class="score-box">
    <div class="score-label">Score Final</div>
    <div>{r.get('overall_score', 0):.1f}</div>
</div>

<h2>📊 Scores por Dimensão</h2>
<div class="grid">
    <div class="card"><h3>🎯 Skill Match</h3><div class="value">{r.get('skill_match_score', 0):.1f}</div></div>
    <div class="card"><h3>💼 Experiência</h3><div class="value">{r.get('experience_score', 0):.1f}</div></div>
    <div class="card"><h3>🎓 Educação</h3><div class="value">{r.get('education_score', 0):.1f}</div></div>
    <div class="card"><h3>📝 Formatação</h3><div class="value">{r.get('formatting_score', 0):.1f}</div></div>
    <div class="card"><h3>🧠 Semântico</h3><div class="value">{r.get('semantic_score', 0):.1f}</div></div>
    <div class="card"><h3>🔤 Densidade</h3><div class="value">{r.get('keyword_density_score', 0):.1f}</div></div>
</div>

<h2>🎯 Keywords</h2>
<p><strong>Match ({len(r.get('matched_keywords', []))}):</strong><br>
{" ".join(f'<span class="keyword keyword-match">{k}</span>' for k in r.get('matched_keywords', []))}</p>
<p><strong>Missing ({len(r.get('missing_keywords', []))}):</strong><br>
{" ".join(f'<span class="keyword keyword-missing">{k}</span>' for k in r.get('missing_keywords', []))}</p>

<h2>💡 Recomendações</h2>
{"".join(f'<div class="recommendation">{rec}</div>' for rec in r.get('recommendations', []))}

<h2>🚩 Red Flags</h2>
{"".join(f'<div class="red-flag">{flag}</div>' for flag in r.get('red_flags', [])) or '<p style="color:#166534;">✅ Nenhum red flag detectado</p>'}

<div class="footer">
    Gerado por ATS Simulator · github.com/zeidlerneto1/ATS_CHECK<br>
    Para uso educacional. Não substitui avaliação humana.
</div>

<div class="no-print" style="margin-top:30px;text-align:center;">
    <button onclick="window.print()" style="padding:12px 32px;font-size:1rem;background:#4f46e5;color:#fff;border:none;border-radius:8px;cursor:pointer;">🖨️ Imprimir / Salvar PDF</button>
</div>
</body>
</html>"""

    return jsonify({"success": True, "html": html})


# ONDA 3: Template LaTeX otimizado para ATS
@app.route("/api/latex", methods=["POST"])
def generate_latex():
    """Gera template LaTeX otimizado para ATS com metadados"""
    data = request.get_json() or {}
    contact = data.get("contact", {})
    summary = data.get("summary", "")
    experience = data.get("experience", [])
    education = data.get("education", [])
    skills = data.get("skills", [])

    name = contact.get("name", "Nome Completo")
    email = contact.get("email", "email@exemplo.com")
    phone = contact.get("phone", "")
    linkedin = contact.get("linkedin", "")
    location = contact.get("location", "")

    exp_latex = ""
    for exp in experience:
        bullets = "\n".join("  \\item " + b for b in exp.get("bullets", []))
        exp_latex += """
\\cventry{%s}{%s}{%s}{%s}{}{%
%s
}""" % (exp.get("dates", "MM/AAAA -- MM/AAAA"), exp.get("title", "Cargo"), exp.get("company", "Empresa"), location, bullets)

    edu_latex = ""
    for edu in education:
        edu_latex += """
\\cventry{%s}{%s}{%s}{}{}{}""" % (edu.get("dates", "AAAA -- AAAA"), edu.get("degree", "Grau"), edu.get("institution", "Instituição"))

    skills_str = ", ".join(skills) if skills else "Skill 1, Skill 2, Skill 3"

    header_line = email
    if phone:
        header_line += " \\textbar " + phone
    if location:
        header_line += " \\textbar " + location
    if linkedin:
        header_line += " \\textbar " + linkedin

    latex = (
        "% ATS-Optimized LaTeX CV Template\n"
        "% Compatível com: Greenhouse, Workday, Lever, Gupy\n"
        "% Instruções: Overleaf → Menu → Compiler → pdfLaTeX\n\n"
        "\\documentclass[11pt,a4paper]{article}\n\n"
        "% Metadados para ATS (core.xml equivalent)\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage[brazil]{babel}\n"
        "\\usepackage{hyperref}\n"
        "\\hypersetup{\n"
        "    pdftitle={" + name + " - CV},\n"
        "    pdfauthor={" + name + "},\n"
        "    pdfsubject={Curriculo Profissional},\n"
        "    pdfkeywords={" + skills_str + "},\n"
        "}\n\n"
        "% Layout ATS-friendly: single-column, sem margens exóticas\n"
        "\\usepackage[margin=2cm]{geometry}\n"
        "\\usepackage{enumitem}\n"
        "\\setlist[itemize]{leftmargin=1.2em,topsep=2pt,itemsep=1pt}\n\n"
        "% Cores sutis (ATS ignora, mas humanos apreciam)\n"
        "\\usepackage{xcolor}\n"
        "\\definecolor{accent}{HTML}{4F46E5}\n\n"
        "% Seções\n"
        "\\usepackage{titlesec}\n"
        "\\titleformat{\\section}{\\Large\\bfseries\\color{accent}}{}{0em}{}[\\titlerule]\n"
        "\\titlespacing*{\\section}{0pt}{12pt}{6pt}\n\n"
        "% Comando para experiência\n"
        "\\newcommand{\\cventry}[6]{\n"
        "  \\textbf{#2} \\hfill \\textit{#1}\\\\\n"
        "  \\textit{#3} \\hfill #4\\\\\n"
        "  #6\\vspace{6pt}\n"
        "}\n\n"
        "\\begin{document}\n\n"
        "% HEADER\n"
        "\\begin{center}\n"
        "  {\\Huge \\textbf{" + name + "}}\\\\[6pt]\n"
        "  " + header_line + "\n"
        "\\end{center}\n\n"
        "\\vspace{8pt}\n\n"
        "% RESUMO\n"
        "\\section{Resumo Profissional}\n"
        + summary + "\n\n"
        "% EXPERIÊNCIA\n"
        "\\section{Experiência Profissional}\n"
        + exp_latex + "\n\n"
        "% FORMAÇÃO\n"
        "\\section{Formação Acadêmica}\n"
        + edu_latex + "\n\n"
        "% SKILLS\n"
        "\\section{Habilidades Técnicas}\n"
        + skills_str + "\n\n"
        "\\end{document}\n"
    )

    return jsonify({"success": True, "latex": latex, "filename": name.lower().replace(" ", "_") + "_cv_ats.tex"})

@app.route("/cv-builder")
def cv_builder():
    return render_template("cv_builder.html")

@app.route("/recruiter-view")
def recruiter_view():
    return render_template("recruiter_view.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
