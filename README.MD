# Deal‑AI – MVP for AI‑Augmented Private‑Credit Deal Analysis

> **Status** – MVP under active development – last updated: 4 Jun 2025

---

## 1 Purpose & Scope (PRD)

**Goal** : Reduce analyst time spent on first‑pass lender overviews & term‑sheet drafting for private‑credit transactions by automating document ingestion, structured data extraction, and Retrieval‑Augmented Generation (RAG) chat.

### 1.1 Primary Outputs

| Output                 | Format                                    | Who consumes it                        |
| ---------------------- | ----------------------------------------- | -------------------------------------- |
| *Lender Overview*      | Markdown → PDF / Google Doc               | Credit committee, syndication partners |
| *Draft Term Sheet*     | Structured JSON → Jinja → DOCX/PDF        | Legal / deal team                      |
| *Structured Deal Data* | JSONB rows in Postgres; Chroma embeddings | Analytics / future comparables         |
| *Interactive Chat*     | REST API + Streamlit                      | Analysts, PMs                          |

### 1.2 User Stories

1. **Analyst uploads** a GDrive folder shared by sponsor → clicks “Process”.
   2. System **parses PDFs / XLSX / DOCX**, skipping unsupported types.
   3. Structured JSON is stored; text chunks indexed to Chroma.
   4. Analyst can **chat** (“What’s EBITDA run‑rate?”) → RAG answer with citations.
   5. Analyst works back and forth between the ai-driven assistant to prepare data and outputs.
   6. Human tweaks terms & exports DOCX / PDF for committee deck.

### 1.3 Acceptance Criteria (MVP)

* ✓ Parse ≥ 80 % of PDF text & Excel tables without runtime errors.
* ✓ Zero unhandled exceptions on unknown file types – skipped gracefully.
* ✓ /health endpoint returns `{"status":"ok"}` under Docker.
* ✓ /process‑deal returns correct `num_documents` for supported files.
* ✓ Embeddings created in Chroma collection `deal_embeddings`.
  - ☐ /chat returns coherent answer citing at least one source chunk.
  - ☐ /report/{deal\_id} returns Markdown lender overview template.

---

## 2 Architecture

![architecture diagram](docs/architecture.svg)

| Layer            | Service                | Tech                             |
| ---------------- | ---------------------- | -------------------------------- |
| Ingestion        | Google Drive → FastAPI | `google‑api‑python‑client`       |
| Parsing          | FastAPI worker         | `unstructured`, `pandas`         |
| Persistence      | Postgres (JSONB)       | `sqlalchemy`                     |
| Vector DB        | Chroma HTTP            | `chromadb`                       |
| LLM / Embeddings | OpenAI API             | `openai`, text‑embedding‑ada‑002 |
| Orchestration    | Docker Compose         | Python 3.11 slim images          |
| UI               | Streamlit              | REST calls to FastAPI            |

---

## 3 Getting Started (local)

```bash
# Clone & launch
$ git clone https://github.com/<you>/deal-ai.git
$ cd deal-ai
$ cp .env.example .env  # add your OPENAI_API_KEY etc.
$ docker compose up -d --build

# Health‑check
$ curl http://127.0.0.1:8000/health   # → {"status":"ok"}
```

### 3.1 Environment Variables (`.env`)

```
OPENAI_API_KEY=sk-...
POSTGRES_USER=deal
POSTGRES_PASSWORD=dealpw
POSTGRES_DB=deals
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
GDRIVE_CREDENTIALS_PATH=gdrive_sa.json
```

### 3.2 Processing a Deal

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/process-deal `
  -ContentType "application/json" -Body '{"folder_id":"<GDRIVE_FOLDER_ID>"}'
```

Returns:

```json
{"deal_id":"deal_<id>_<ts>", "num_documents":4}
```

---

## 4 API Reference

| Endpoint            | Method | Body                  | Returns                |
| ------------------- | ------ | --------------------- | ---------------------- |
| `/health`           | GET    | –                     | `{status: "ok"}`       |
| `/process-deal`     | POST   | `{folder_id}`         | `ProcessResponse`      |
| `/chat`             | POST   | `{deal_id, question}` | `ChatResponse` *(TBD)* |
| `/report/{deal_id}` | GET    | –                     | Markdown *(TBD)*       |

Models are defined in **`backend/schemas.py`** (Pydantic).

---

## 5 Development Notes

* **Python 3.11**, Poetry dependencies installed in Docker with `--no-root`.
* **Chroma client** auto‑connects (`Client()`); no host/port args.
* Unsupported file types return empty `ParsedDocument`, preventing crashes.
* Docker Desktop on Windows – port 8000 sometimes unreachable via `localhost`; use `127.0.0.1`.

### 5.1 Common Issues

| Symptom                                                    | Fix                                                                    |
| ---------------------------------------------------------- | ---------------------------------------------------------------------- |
| API container exits: `Missing OPENAI_API_KEY`              | Add key to `.env`                                                      |
| Chroma `TypeError: Client() got unexpected keyword 'host'` | Use `Client()` default                                                 |
| 0 documents returned                                       | Ensure `ParsedDocument` supplies all fields; unsupported types skipped |

---

## 6 Roadmap / TODO

* [ ] **/chat** RAG endpoint with cited chunks
* [ ] **/report** lender overview Jinja2 template
* [ ] Streamlit chat & report UI
* [ ] Prometheus metrics & Grafana dashboard
* [ ] Excel cash‑flow auto‑classifier (Great Expectations rules)
* [ ] Batch processing via n8n / Prefect pipeline

---

## 7 License / Authors

MIT License © 2025 Deal‑AI contributors.

---

> *Docs auto‑generated by ChatGPT + canmore canvas.*
