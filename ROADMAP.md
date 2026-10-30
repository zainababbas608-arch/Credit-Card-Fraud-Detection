# Project Roadmap — Credit Card Fraud Detection using Big Data

**Course:** Big Data Analytics (Final Year)
**Dataset:** IEEE-CIS Fraud Detection (Kaggle/Vesta) · ~690k train transactions, 400+ features
**Tech Stack:** Python · PySpark (MLlib + Structured Streaming) · Docker · Parquet · Kafka (stretch) · Streamlit · Jupyter
**Scope decision:** Batch pipeline is the core deliverable; real-time streaming is a stretch goal only if time allows.

---

## Goal
Build a distributed (Spark-based), end-to-end credit card fraud detection pipeline:
ingest → store → preprocess → train → evaluate → visualize, plus a stretch goal of live streaming detection.
Deliverables must follow the course instructions: presentation of 10–15 slides, ≥5 recent references (2024–2026), code + screenshots + results with explanations, conclusions on findings/limitations/future work, and every group member able to explain their part.

---

## Laptop Readiness (verified 2026-10-30)
- **Specs:** i7-1355U (10C/12T), 15.7 GB RAM, no dGPU (not needed — CPU-only pipeline), D: has ~189 GB free
- **Docker fixed & verified:**
  - Engine now runs end-to-end (`hello-world` test passed twice)
  - Docker virtual disks relocated to `D:\Desktop\docker-data\wsl` via NTFS junction at `C:\Users\DELL\AppData\Local\Docker\wsl` — keep BOTH intact; deleting either breaks Docker
  - Resource caps set: 6 GB RAM / 6 CPUs (Settings → Resources honored)
  - Docker AutoStart is OFF — launch Docker Desktop manually before each work session
- **Rules for smooth runs:** Spark executor memory ≤ 3–4 GB · tune on 5–10% samples, train final model on full data · keep everything big on D: (C: has <45 GB free)

---

## Week 1–2 — Setup, Data & References
- [ ] 1-page project proposal: objective, architecture sketch, stack, evaluation plan
- [ ] Download IEEE-CIS dataset from Kaggle (do this EARLY — it's ~1 GB):
  - `train_transaction.csv`, `train_identity.csv`, `test_transaction.csv`
- [x] Docker Desktop fixed, storage moved to D:, engine verified running
- [ ] Docker environment: `docker-compose` with **Jupyter + PySpark** containers on one network
- [ ] Git repo + folder structure:
```
├── data/raw, data/processed
├── notebooks/
├── src/ingest, src/pipeline, src/models
├── streaming/          # stretch: Kafka producer + Spark Structured Streaming
├── dashboard/
├── reports/            # proposal, screenshots/, references.bib, final paper
└── README.md           # + this ROADMAP.md
```
- [ ] Start `reports/references.bib` — target 6–8 references, prioritizing 2024–2026:
  - *Effective High-order Graph Representation Learning for Credit Card Fraud Detection* (IJCAI 2024)
  - *Barely Supervised Learning for Graph-Based Fraud Detection* (AAAI 2024)
  - *A Payment Transaction Pre-training Model for Fraud Transaction Detection* (CIKM 2024)
  - *Real-Time Fraud Detection using Apache Kafka, Apache Spark and PySpark MLlib* (2025)
  - IEEE-CIS/Vesta competition technical write-ups
  - Course-approved big data references

## Week 3–4 — EDA + Preprocessing (PySpark)
- [ ] Convert CSV → **Parquet** (columnar, compressed; partitioned by date)
- [ ] EDA with Spark DataFrames (NOT pandas):
  - Fraud rate (~3.5%), transaction amount distributions, time-of-day patterns
  - Missing-value map, correlation sampling of the 400+ V-features
- [ ] Preprocessing decisions:
  - Drop columns with >80% missing values
  - Remove near-duplicate V-columns via correlation (Spark aggregation exercise)
- [ ] Join transaction + identity tables on `TransactionID`
- [ ] Feature engineering (explainable in viva — key marks area):
  - `TransactionDT` → hour-of-day / day-of-week
  - Amount bins
  - Card velocity features ("txn count in last 1h per card") via **Spark window functions**
- [ ] Save cleaned feature set to Parquet

## Week 5–6 — Modeling (Spark MLlib)
- [ ] **Time-based split** (train on past, test on latest) — never a random split for fraud
- [ ] Pipeline: `VectorAssembler → StandardScaler → model`
- [ ] Models in increasing sophistication:
  1. Logistic Regression (baseline, class weights for imbalance)
  2. Random Forest
  3. Gradient-Boosted Trees (likely winner)
- [ ] Hyperparameter tuning with `CrossValidator` / `TrainValidationSplit` (cap parallelism for laptop RAM)

## Week 7 — Evaluation
NEVER lead with accuracy — the fraud class is what matters.
- [ ] Metrics: **PR-AUC, ROC-AUC, precision, recall, F1** (fraud class) + confusion matrix
- [ ] Threshold tuning with business justification (e.g., target recall ≥ 0.80)
- [ ] Model comparison table — becomes the results section of report + slide 10
- [ ] Take **Spark UI screenshots** (stages, executors, DAG) as proof of distributed execution
- [ ] For every result, write a 1–2 sentence *how it works* explanation (course instruction #5)

## Week 8–9 — Stretch Goals (priority order, only if time allows)
1. [ ] **Streamlit dashboard** (effectively must-have for demo):
     - Fraud stats, feature importances, single-transaction "predict this" form
2. [ ] **Streaming** pipeline (Kafka + Spark Structured Streaming):
     - Kafka producer replays test transactions → streaming job scores them → alert output
     - Backed by the 2025 Kafka/Spark/PySpark MLlib paper — strong citation + demo value
3. [ ] Dockerize full pipeline into clean, re-runnable services

## Week 10–11 — Deliverables (aligned to course instructions 1–8)

### Presentation outline (12–15 slides)
1. Title + team & member roles
2. Problem statement & motivation (fraud cost, imbalance)
3. Why Big Data (velocity, volume, distributed need)
4. Related work — 2024–2026 papers
5. System architecture diagram (Docker, Spark, storage)
6. Dataset — IEEE-CIS stats, schema walkthrough
7. Implementation: ingestion → Parquet (screenshots)
8. Implementation: preprocessing & feature engineering (explain window functions)
9. Implementation: model training in Spark MLlib
10. Results: comparison table, PR curves, confusion matrix
11. Demo: dashboard screenshot / live predict
12. Key findings
13. Limitations & future improvements
14. References slide
15. Q&A prep

### Group contribution plan (everyone must be able to defend their part)
- Member A: data ingestion + preprocessing
- Member B: modeling + tuning
- Member C: evaluation + dashboard
- Member D: architecture, Docker, (streaming), report writing
→ Each member builds one notebook section themselves.

### Conclusion section checklist
- Key findings (e.g., GBT beats LR; PR-AUC = 0.XX)
- Limitations (single-laptop scale, anonymous/V-features, no true cluster)
- Future improvements (streaming at scale, graph-based detection per IJCAI/AAAI 2024, deep learning, model drift monitoring)

### Evidence folder (`reports/screenshots/`)
Spark UI, notebook outputs, Parquet listings in Docker, curves/matrices — everything shown on slides needs a screenshot + explanation.

---

## Risks
- **Laptop RAM** → cap executor memory (2–4 GB), Parquet pushdown, sample for tuning
- **400+ feature volume** → simple preprocessing first, iterate later
- **Dataset download delay** → resolve Week 1
- **Streaming scope creep** → batch-first; streaming only after core pipeline is solid
- **C: drive space (only ~41 GB)** → all large files on D:; Docker already relocated

## Demo day checklist
- [ ] Live dashboard or recorded demo ready
- [ ] Docker services start with one command
- [ ] Every member has rehearsed their section
- [ ] References slide cites ≥5 recent (2024–2026) sources
