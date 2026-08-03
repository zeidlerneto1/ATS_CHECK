FROM python:3.12-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends     git     gcc     g++     && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baixa modelo spaCy pt-BR
RUN python -m spacy download pt_core_news_sm

# Copia código
COPY . .

# Variáveis de ambiente
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Entrypoint padrão: CLI
ENTRYPOINT ["python", "interfaces/cli.py"]
CMD ["--help"]
