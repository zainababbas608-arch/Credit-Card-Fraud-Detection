# Project Roadmap - Credit Card Fraud Detection using Big Data

**Course:** Big Data Analytics (Final Year)
**Team:** 2 members (Member 1 = technical lead, Member 2 = literature/docs/slides)
**Dataset:** IEEE-CIS Fraud Detection (Kaggle/Vesta) - ~690k train transactions, 400+ features
**Tech Stack:** Python | PySpark (MLlib + Structured Streaming) | Docker | Parquet | Kafka (stretch) | Streamlit | Jupyter | VS Code Dev Containers
**Scope decision:** Batch pipeline is the core deliverable; real-time streaming is a stretch goal only if time allows.
**Plan is phase-based, not week-based.**

---

## Goal
Build a distributed (Spark-based), end-to-end credit card fraud detection pipeline:
ingest -> store -> preprocess -> train -> evaluate -> visualize, plus a stretch goal of live streaming detection.
Deliverables must follow the course instructions: presentation of 10-15 slides, >=5 recent references (2024-2026), code + screenshots + results with explanations, conclusion covering key findings/limitations/future work, and every group member able to explain their part.

---

## Laptop Readiness (verified 2026-10-30)
- **Specs:** i7-1355U (10C/12T), 15.7 GB RAM, no dGPU (not needed - CPU-only pipeline), D: has ~189 GB free
- **Docker fixed & verified:**
  - Engine runs end-to-end (`hello-world` test passed twice)
  - Virtual disks relocated to `D:\Desktop\docker-data\wsl` via NTFS junction at `C:\Users\DELL\AppData\Local\Docker\wsl` - keep BOTH intact; deleting either breaks Docker
  - Resource caps: 6 GB RAM / 6 CPUs (Settings -> Resources honored)
  - Docker AutoStart OFF - launch Docker Desktop manually before each work session
- **Memory rule (measured):** free RAM must be >= 6 GB before every work session
  - Task Manager (Ctrl+Shift+Esc) -> sort by Memory -> close heavy apps (browsers eat 2-8 GB)
  - Monitor live during runs: `docker stats --no-stream`
  - Free everything after sessions: `docker desktop stop`
- **Rules for smooth runs:** Spark driver memory <= 3 g | tune on samples, train final model on full data | all large files on D: (C: has ~41 GB free)

---

## Phase 0 - Proposal
- [ ] 1-page project proposal: objective, architecture sketch, stack, evaluation plan (Member 2 drafts, Member 1 technically reviews)
- [ ] Get professor approval early

## Phase 1 - Environment & Data Setup
- [x] Download IEEE-CIS dataset from Kaggle into `data/`:
  - `train_transaction.csv` (~650 MB), `train_identity.csv` (~25 MB)
  - `test_transaction.csv` (~585 MB), `test_identity.csv` (~25 MB), `sample_submission.csv` (~6 MB)
- [x] Docker Desktop fixed, storage relocated to D:, engine verified running (see Laptop Readiness)
- [ ] Project skeleton folders: `notebooks/ src/ streaming/ dashboard/ reports/screenshots/` (with `.gitkeep`)
- [ ] Environment files: `.devcontainer/` (Dockerfile, spark-defaults.conf, devcontainer.json) + `docker-compose.yml`
- [ ] First container build (`Reopen in Container`; downloads jupyter/pyspark-notebook base image ~4-6 GB, one-time)
- [ ] `reports/references.bib` started - target 6-8 references, prioritizing 2024-2026 (Member 2 owns):
  - *Effective High-order Graph Representation Learning for Credit Card Fraud Detection* (IJCAI 2024)
  - *Barely Supervised Learning for Graph-Based Fraud Detection* (AAAI 2024)
  - *A Payment Transaction Pre-training Model for Fraud Transaction Detection* (CIKM 2024)
  - *Real-Time Fraud Detection using Apache Kafka, Apache Spark and PySpark MLlib* (2025)
  - IEEE-CIS/Vesta competition technical write-ups
  - Course-approved big data references

## Phase 2 - Environment Validation (Spark meets the data)
- [ ] `notebooks/00_environment_check.ipynb`: SparkSession -> read `train_transaction.csv`
  - Row count (~594k) + column count (~394)
  - `isFraud` class split (~20,918 fraud vs ~573,103 legit) - first EDA story number
- [ ] Spark UI live check at localhost:4040 - screenshot to `reports/screenshots/01_env_check.png`, `02_spark_ui.png`

## Phase 3 - EDA + Preprocessing (PySpark)
- [ ] Convert CSV -> **Parquet** (columnar, compressed; partitioned by date)
- [ ] EDA with Spark DataFrames (NOT pandas):
  - Fraud rate (~3.5%), transaction amount distributions, time-of-day patterns
  - Missing-value map, correlation sampling of the 400+ V-features
- [ ] Preprocessing decisions:
  - Drop columns with >80% missing values
  - Remove near-duplicate V-columns via correlation (Spark aggregation exercise)
- [ ] Join transaction + identity tables on `TransactionID`
- [ ] Feature engineering (explainable in viva - key marks area):
  - `TransactionDT` -> hour-of-day / day-of-week
  - Amount bins
  - Card velocity features ("txn count in last 1h per card") via **Spark window functions**
- [ ] Save cleaned feature set to Parquet

## Phase 4 - Modeling (Spark MLlib)
- [ ] **Time-based split** (train on past, test on latest) - never a random split for fraud
- [ ] Pipeline: `VectorAssembler -> StandardScaler -> model`
- [ ] Models in increasing sophistication:
  1. Logistic Regression (baseline, class weights for imbalance)
  2. Random Forest
  3. Gradient-Boosted Trees (likely winner)
- [ ] Hyperparameter tuning on samples with `CrossValidator` / `TrainValidationSplit` (laptop RAM discipline), final train on full data

## Phase 5 - Evaluation
NEVER lead with accuracy - the fraud class is what matters.
- [ ] Metrics: **PR-AUC, ROC-AUC, precision, recall, F1** (fraud class) + confusion matrix
- [ ] Threshold tuning with business justification (e.g., target recall >= 0.80)
- [ ] Model comparison table - becomes the results section of report + slide 10
- [ ] Spark UI screenshots (stages, executors, DAG) as proof of distributed execution
- [ ] For every result, write a 1-2 sentence "how it works" explanation (course instruction #5)

## Phase 6 - Stretch Goals (priority order, only if time allows)
1. [ ] **Streamlit dashboard** (effectively must-have for demo):
     - Fraud stats, feature importances, single-transaction "predict this" form
2. [ ] **Streaming** pipeline (Kafka + Spark Structured Streaming):
     - Kafka producer replays test transactions -> streaming job scores them -> alert output
     - Backed by the 2025 Kafka/Spark/PySpark MLlib paper - strong citation + demo value
3. [ ] Dockerize full pipeline into clean, re-runnable services

## Phase 7 - Deliverables
- [ ] **Final report** incl. architecture diagram and conclusion section (see checklist below)
- [ ] **Presentation 10-15 slides** (outline below) + **demo** (live or recorded)

### Presentation outline (12-15 slides)
1. Title + team & member roles
2. Problem statement & motivation (fraud cost, imbalance)
3. Why Big Data (velocity, volume, distributed need)
4. Related work - 2024-2026 papers
5. System architecture diagram (Docker, Spark, storage)
6. Dataset - IEEE-CIS stats, schema walkthrough
7. Implementation: ingestion -> Parquet (screenshots)
8. Implementation: preprocessing & feature engineering (explain window functions)
9. Implementation: model training in Spark MLlib
10. Results: comparison table, PR curves, confusion matrix
11. Demo: dashboard screenshot / live predict
12. Key findings
13. Limitations & future improvements
14. References slide
15. Q&A prep

### Team split - 2 members (both must be able to defend the project)

| | Member 1 (technical lead) | Member 2 |
|---|---|---|
| Pipeline work | Docker env, PySpark EDA/preprocessing, modeling, evaluation, dashboard | - |
| Supporting work | - | Literature review: 2024-2026 papers -> related-work slide + `reports/references.bib` |
| Report & slides | Implementation, architecture, results sections | Proposal, intro, conclusion; slide design & layout |
| Presentation | Walks through implementation live (Docker -> Spark -> results) | Problem statement, why-big-data, related work, conclusions |

Warning (instruction #8): since Member 1 does the core build, Member 2 must actively engage too (run the check notebook once + teach-back session ~1 week before the presentation) so both can answer questions under viva.

### Conclusion section checklist (course instruction #6)
- Key findings (e.g., GBT beats LR; PR-AUC = 0.XX)
- Limitations (single-laptop scale, anonymous/V-features, no true cluster)
- Future improvements (streaming at scale, graph-based detection per IJCAI/AAAI 2024, deep learning, model drift monitoring)

### Evidence folder (`reports/screenshots/`)
Spark UI, notebook outputs, Parquet listings, curves/matrices - everything shown on slides needs a screenshot + explanation.

---

## Risks
- **Laptop RAM (only 15.7 GB, ~11.8 GB held by OS+apps)** -> enforce >= 6 GB free rule; cap executor memory 2-3 g; sample for tuning
- **C: drive space (~41 GB)** -> all large files on D:; Docker already relocated
- **400+ feature volume** -> simple preprocessing first, iterate later
- **Data download** -> done, resolved
- **Streaming scope creep** -> batch-first; streaming only after core pipeline is solid

## Demo day checklist
- [ ] Live dashboard or recorded demo ready
- [ ] Docker services start with one command
- [ ] Both members rehearsed; Member 2 did the teach-back session
- [ ] References slide cites >=5 recent (2024-2026) sources
