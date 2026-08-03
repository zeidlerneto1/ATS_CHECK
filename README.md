# 🧠 ATS Simulator BR - Fase 1

Simulador de parsing de currículos (CVs) em PDF no formato brasileiro, replicando a lógica de ATS como Gupy, Kenoby e Vagas.com.

## Arquitetura

```
ats_simulator/
├── domain/           # Entidades puras + Ports (Clean Architecture)
├── infrastructure/   # Adapters concretos (parsers, NLP)
├── interfaces/       # CLI / API
└── tests/            # Testes unitários + integração
```

## 🚀 Quick Start

### Local

```bash
pip install -r requirements.txt
python -m spacy download pt_core_news_sm
python interfaces/cli.py curriculos/seu_cv.pdf
```

### Docker

```bash
docker-compose up --build
# Ou para rodar um CV específico:
docker run --rm -v $(pwd)/curriculos:/app/curriculos ats-simulator-br curriculos/seu_cv.pdf
```

## 📋 Funcionalidades (Fase 1)

- ✅ Extração de texto de PDFs com validação de MIME e tamanho
- ✅ Detecção de problemas (CV-imagem, 2 colunas, elementos gráficos)
- ✅ NLP com spaCy pt-BR (entidades: Nome, Email, Telefone, Localização)
- ✅ Parsing de datas brasileiras (`jan/2022`, `2022 - atual`, `desde 2022`)
- ✅ Identificação de seções (Resumo, Experiência, Formação, Skills)
- ✅ Normalização de 50+ skills tecnológicas com contexto
- ✅ Cálculo de tempo total de experiência
- ✅ Confidence score e sistema de warnings

## 🧪 Testes

```bash
pytest tests/ -v
```

## 📦 Dependências

- `spacy` (modelo `pt_core_news_sm` ou `pt_core_news_lg`)
- `pdfplumber`
- `pytest`

## 🔮 Roadmap

| Fase | Escopo |
|------|--------|
| Fase 2 | API REST (FastAPI), Storage S3 |
| Fase 3 | OCR para PDFs scanneados (Tesseract) |
| Fase 4 | ML para ranking de candidatos |
| Fase 5 | Integração com ATS reais (webhooks) |

## 📄 Licença

MIT
