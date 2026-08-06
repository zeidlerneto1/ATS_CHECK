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
from engine.logger import ATSLogger

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
    })



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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
