#!/usr/bin/env python3
"""
API Flask - ATS Web com streaming de logs via SSE
"""
import os
import sys
import json
import time
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.ats_engine import ATSEngine, JobDescription
from engine.logger import ATSLogger

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Job descriptions demo
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
}


@app.route("/")
def index():
    return render_template("index.html", jobs=list(JOBS.keys()))


@app.route("/api/jobs")
def get_jobs():
    return jsonify({k: {"title": v.title, "company": v.company} for k, v in JOBS.items()})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "cv" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["cv"]
    job_key = request.form.get("job", "fullstack_junior")

    if file.filename == "":
        return jsonify({"error": "Arquivo vazio"}), 400

    if job_key not in JOBS:
        return jsonify({"error": "Vaga não encontrada"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ['.pdf', '.docx']:
        return jsonify({"error": f"Formato não suportado: {ext}"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    job = JOBS[job_key]
    engine = ATSEngine()

    # Coleta logs em lista
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


@app.route("/api/analyze/stream", methods=["POST"])
def analyze_stream():
    """SSE endpoint para logs em tempo real"""
    if "cv" not in request.files:
        def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Nenhum arquivo'})}\n\n"
        return Response(error_gen(), mimetype="text/event-stream")

    file = request.files["cv"]
    job_key = request.form.get("job", "fullstack_junior")

    ext = Path(file.filename).suffix.lower()
    if ext not in ['.pdf', '.docx']:
        def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'message': f'Formato não suportado: {ext}'})}\n\n"
        return Response(error_gen(), mimetype="text/event-stream")

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    job = JOBS.get(job_key, JOBS["fullstack_junior"])

    def generate():
        engine = ATSEngine()
        result_container = {}

        def log_callback(entry):
            data = json.dumps({
                "type": "log",
                "timestamp": entry.timestamp,
                "stage": entry.stage,
                "stage_name": ATSLogger.STAGES.get(entry.stage, entry.stage),
                "action": entry.action,
                "details": entry.details,
                "severity": entry.severity,
            })
            yield f"data: {data}\n\n"

        # Executa análise
        result = engine.analyze(filepath, job)

        # Envia logs acumulados
        for log in result.logs:
            data = json.dumps({
                "type": "log",
                "timestamp": log["timestamp"],
                "stage": log["stage"],
                "stage_name": log["stage_name"],
                "action": log["action"],
                "details": log["details"],
                "severity": log["severity"],
            })
            yield f"data: {data}\n\n"
            time.sleep(0.05)  # Pequeno delay para efeito visual

        # Envia resultado final
        yield f"data: {json.dumps({'type': 'result', 'result': {\n"
        yield f"  'candidate_name': result.candidate_name,\n"
        yield f"  'job_title': result.job_title,\n"
        yield f"  'overall_score': result.overall_score,\n"
        yield f"  'skill_match_score': result.skill_match_score,\n"
        yield f"  'experience_score': result.experience_score,\n"
        yield f"  'education_score': result.education_score,\n"
        yield f"  'formatting_score': result.formatting_score,\n"
        yield f"  'semantic_score': result.semantic_score,\n"
        yield f"  'keyword_density_score': result.keyword_density_score,\n"
        yield f"  'matched_keywords': result.matched_keywords,\n"
        yield f"  'missing_keywords': result.missing_keywords,\n"
        yield f"  'red_flags': result.red_flags,\n"
        yield f"  'recommendations': result.recommendations\n"
        yield f"}})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
