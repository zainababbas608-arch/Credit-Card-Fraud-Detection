# 🗺️ Project Roadmap — Credit Card Fraud Detection using Big Data

**Course:** Big Data Analytics (Final Year)
**Dataset:** IEEE-CIS Fraud Detection (Kaggle/Vesta) · 590,540 train transactions (measured), 394 features
**Tech Stack:** Python · PySpark (MLlib + Structured Streaming) · Docker + VS Code Dev Containers · Parquet · Kafka (stretch) · Streamlit · Jupyter
**Scope decision:** Batch pipeline is the core deliverable; real-time streaming is a stretch goal only if time allows.

---

## 🎯 Goal
Build a distributed (Spark-based), end-to-end credit card fraud detection pipeline:
ingest → store → preprocess → train → evaluate → visualize, plus a stretch goal of live streaming detection.
Deliverables must follow the course instructions: presentation of 10–15 slides, ≥5 recent references (2024–2026), code + screenshots + results with explanations, conclusions on findings/limitations/future work.

---

## 📊 Overall Progress
| Phase | Name | Status |
|---|---|---|
| 1 | Foundation: Environment & Data | ✅ done (container `fraud-datascience`, replay-verified notebooks 00–01) |
| 2 | Data Pipeline: EDA & Preprocessing | ✅ done (notebooks 02–04 replay-verified; screenshots 01–14) |
| 3 | Modeling | ✅ done (notebook 05 + imbalance shootout; screenshots 15–23) |
| 4 | Evaluation | ✅ done (notebook 06 full-scale + RF sweep + curves; screenshots 24–32) |
| 5 | Extensions & Demo Assets | ✅ done (Streamlit officer console + scored artifact; streaming moved to Phase 6) |
| 6 | Streaming: Kafka + Spark Structured Streaming | ⬜ next (architecture agreed 2026-11-06) |
| 7 | Deliverables & Presentation | ⬜ (final phase) |

---

## ✅ Laptop Readiness (verified 2026-10-30)
- **Specs:** i7-1355U (10C/12T), 15.7 GB RAM, no dGPU (not needed — CPU-only pipeline), D: has ~189 GB free
- **Docker fixed & verified:**
  - Engine now runs end-to-end (`hello-world` test passed twice)
  - Docker virtual disks relocated to `D:\Desktop\docker-data\wsl` via NTFS junction at `C:\Users\DELL\AppData\Local\Docker\wsl` — keep BOTH intact; deleting either breaks Docker
  - Resource caps set: 6 GB RAM / 6 CPUs (Settings → Resources honored)
  - Docker AutoStart is OFF — launch Docker Desktop manually before each work session
- **Rules for smooth runs:** Spark driver memory = 3 GB (`spark-defaults.conf`) · tune on 5–10% samples, train final model on full data · keep everything big on D: (C: has <45 GB free) · close browser tabs while running Spark jobs

---

# 🧩 PHASE 1 — Foundation: Environment & Data

- [x] 1-page project proposal: objective, architecture sketch, stack, evaluation plan (async during phases)
- [x] Download IEEE-CIS dataset from Kaggle → `data/` (all 5 CSVs present)
- [x] Docker Desktop fixed, storage moved to D:, engine verified running
- [x] `.devcontainer/` (Dockerfile, spark-defaults.conf, devcontainer.json) + root `docker-compose.yml`
- [x] First image build: devcontainer image built; container renamed `fraud-datascience`; `pyspark 3.5.0` verified inside (green-badge recovery procedure documented and drilled)
- [x] Validation notebook `notebooks/00_environment_check.ipynb`: SparkSession → schema/count verification (+ `01_csv_to_parquet.ipynb`) → screenshots `01`–`03` in `reports/screenshots/`
- [x] Git repo initialized + pushed; folder skeleton with `.gitkeep`
- [ ] Populate `reports/references.bib` — target 6–8 references, prioritizing 2024–2026:
  - *Effective High-order Graph Representation Learning for Credit Card Fraud Detection* (IJCAI 2024)
  - *Barely Supervised Learning for Graph-Based Fraud Detection* (AAAI 2024)
  - *A Payment Transaction Pre-training Model for Fraud Transaction Detection* (CIKM 2024)
  - *Real-Time Fraud Detection using Apache Kafka, Apache Spark and PySpark MLlib* (2025)
  - IEEE-CIS/Vesta competition technical write-ups
  - Course-approved big data references

# 🧩 PHASE 2 — Data Pipeline: EDA & Preprocessing (PySpark)

- [x] Convert CSV → **Parquet** (columnar, compressed; verified lossless on all 4 files)
- [x] EDA with Spark DataFrames (NOT pandas):
  - Fraud rate **3.50%** (20,663 / 590,540), amount-band and time-of-day patterns
  - **14.47% fraud at $0–1** (card-testing signature)
  - Missing-value census: **55 columns >80% empty** (none >95%)
- [x] Preprocessing decisions:
  - Dropped 55 columns with >80% missing values
  - Removed **49** near-duplicate V-columns via |r|>0.98 (5% sample + np.corrcoef hybrid)
- [ ] Join transaction + identity tables on `TransactionID` — **DESCOPED** (transaction columns carried the signal; identity join = future work)
- [x] Feature engineering (explainable in viva — key marks area):
  - `TransactionDT` → `day` / `hour` / `wd` (relative time only)
  - **Velocity features** via Spark window functions: `card1_txn_24h`, `card1_amt_24h`, `card1_txn_all`, `card1_amt_avg`, `amt_vs_card` (trailing 24h windows = leakage-proof)
  - Density proof: 78.4% of rows have >1 txn in trailing 24h; max card = 881 txn/24h
- [x] Save cleaned feature set to Parquet (`train_features`, 590,540 × 298)
- [x] EDA output plots/screenshots → `reports/screenshots/` (`04`–`14`)

# 🧩 PHASE 3 — Modeling (Spark MLlib)

- [x] **Time-based split** (train days 0–165 / test 166–182, fraud 3.47% vs 3.88%) — never a random split for fraud
- [x] Pipeline: median-impute (train-only) → StringIndexer frequency-encoding (metadata stripped) → `VectorAssembler` (StandardScaler descoped — trees don't need it; frequency encoding chosen instead)
- [x] Models in increasing sophistication:
  1. Logistic Regression (baseline; weighted; floor)
  2. Random Forest (60 trees, depth 8)
  3. Gradient-Boosted Trees (d5 and d3 variants — dfull)
- [x] Hyperparameter tuning: **weight-scheme shootout** (28x balanced vs sqrt ~5x vs none) + GBT overfit configs (depth/step/subsampling) on the 5% sample — replaced CrossValidator as the laptop-friendly tuning story
- [x] `05_model_training.ipynb` replay-verified end-to-end (Restart & Run All clean)

# 🧩 PHASE 4 — Evaluation

⚠️ NEVER lead with accuracy — the fraud class is what matters.
- [x] Metrics: **PR-AUC, ROC-AUC, precision, recall, F1** (fraud class) + confusion counts (scorer applied identically to every model)
- [x] Threshold tuning with business justification: 19-point sweep on both champions; F1-optimal operating points (GBT-d5 @0.5, RF @0.4) + the precision-vs-recall trade card
- [x] Model comparison table (`29_full_comparison.png`) — becomes the results section of report + slide 10
- [x] Train final models on the FULL 543,948-row train split (tuning was on the 5% sample)
- [ ] Additional Phase-4 Spark UI screenshots (optional; distributed-execution proof already in `05`, `13` from Phase 2)
- [x] For every result, a 1–2 sentence *how it works* explanation (cells carry the narrative; this roadmap + chat carry the full one)

### Phase 4 measured results (2026-11-05)
- Full-scale comparison (test split): LR prAUC 0.177 / **RF 0.4863** / **GBT-d5 0.4860 (rocAUC 0.8874)** / GBT-d3 0.4531 — vs random baseline prAUC 0.039 (~12.5x lift)
- Operating points: **GBT-d5 @0.5 → precision 0.525, recall 0.469, F1 0.495, 1,618 alerts**; **RF @0.4 → precision 0.596, recall 0.430, F1 0.499, 1,303 alerts**
- RF and GBT-d5 = co-champions (statistical tie on ranking; calibration personalities differ — RF high-precision at high thresholds, e.g. 0.948 precision @0.9)
- Full-scale training collapsed the sample-era overfit gap: GBT-d5 train-test prAUC gap 0.27 → 0.078
- Top features of winner: V258, C13, C1, TransactionAmt, **card1_amt_avg (engineered velocity, 4.0%)**, C14, C11, day, card6, card3
- Artifacts: `models/gbt_winner`, `reports/figures/pr_roc_curves.png`, screenshots `24`–`32`

# 🧩 PHASE 5 — Extensions & Demo Assets (shipped 2026-11-06)

1. [x] **Streamlit "Fraud Watch" officer console — SHIPPED** (`src/dashboard/app.py`):
   - Officer-facing shift screen: one case card at a time (charge, suspicion % with
     red/amber/green risk badge, plain-language reasons computed from real percentiles
     of the scored data), Confirm fraud / False alarm buttons, notifications ticker,
     and an investigation log that scores officer decisions against truth labels
   - Single-model authority locked: GBT-d5 @ threshold 0.5 (RF stays a Statistics-tab
     footnote, per the Phase-4 decision)
   - Statistics tab holds the science: alarm-strictness dial, 19-row sweep recomputed
     live, score histograms, top-10 importances (engineered `card1_amt_avg`
     highlighted), transaction lookup, Phase-2 EDA facts
   - Replay engine: reads precomputed artifact `data/processed/dashboard_test.csv`
     (46,592 scored rows, 18 cols, written by notebook 06 Cell 17) — no Spark in the
     UI. Shift pre-primes on the first alert (row 50, day 166) and auto-plays; the
     full 17-day window replays in ~26 s at default speed 3 — cases appear instantly
     from load (pacing rebuilt after v1 feedback: no dead shifts)
2. [x] **Environment incident + fix (2026-11-04)**: pip-installing Streamlit into the
     shared conda env upgraded numpy to 2.4.6 and broke every NumPy-1.x-compiled
     library in it (pandas/pyarrow/scipy/sklearn ABI failures, `numpy.dtype size
     changed`). Fix: Streamlit isolated in a dedicated venv `/opt/venv/fraudui`
     (Dockerfile layer); environment rule — notebooks `/opt/conda`, dashboard
     `/opt/venv/fraudui`, one environment per artifact, never mixed
3. [x] **Evidence**: `33` Cell-17 artifact checkpoint · `34` shift end (46,592 seen |
     1,618 suspicious | 4 case decisions | ~52% alarm accuracy) · `35` Statistics tab
     at the locked operating point (0.495 F1 @ 0.5 — matches Phase 4 to the digit)
   - Record correction (confirmed in CSV + dashboard): test window holds **1,809 real
     frauds** (849 caught + 960 missed) — supersedes the 1,781 quoted in early notes
4. [ ] Dockerize full pipeline into clean, re-runnable services (venv layer done;
     remaining: one-command bring-up of broker + notebook + console)

# 🧩 PHASE 6 — Real-Time Streaming (Kafka + Spark Structured Streaming, agreed 2026-11-06)

> Scoped with the 2026-11-06 reality check: a public live fraud-labeled card feed does
> not exist (PII/PCI) — broker + benchmark corpus is the standard evaluation setup for
> fraud streaming; the report states this and cites the Kafka/Spark 2025 paper for the
> transport tier.

1. [ ] **Broker**: docker-compose service, KRaft single node; create topics
      `transactions` / `alerts`
2. [ ] **Producer**: `src/stream/producer.py` (container process) — IEEE-CIS test-window
      transactions → JSON → `transactions` topic at configurable rows/s
3. [ ] **Streaming job**: `notebooks/07_streaming_preview.ipynb` (kernel /opt/conda):
      readStream kafka → from_json → PipelineModel.load(models/gbt_winner) →
      filter fraud → `alerts` topic + parquet + checkpoints under `data/stream`
4. [ ] **Measured scoreboard**: processed/s, alerts/s, alert fraud-rate (~52% expected),
      end-to-end latency; kill-and-restart the job to demo checkpoint resume
5. [ ] **Dashboard live-monitor adder**: Fraud Watch reads the alerts stream instead of
      the CSV replay (~20 lines in `src/dashboard/app.py`)
6. [ ] **Evidence**: `37_streaming_alerts.png` (stream scoreboard) ·
      `38_dashboard_live_monitor.png` (live console) — `36` stays reserved/optional
7. [ ] **Docs**: limitations section gains the ingest honesty note; report cites the
      Kafka/Spark 2025 paper as the transfer-backed transport citation

# 🧩 PHASE 7 — Deliverables & Presentation (aligned to course instructions 1–8)

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


### Conclusion section checklist
- Key findings (RF & GBT-d5 tie on ranking prAUC ≈ 0.486 = ~12.5x lift; LR floors at 0.177; engineered velocity features rank in the winner's top-10)
- Limitations (single-laptop scale, anonymous/V-features, no true cluster)
- Future improvements (real-time streaming — now implemented in Phase 6, graph-based detection per IJCAI/AAAI 2024, deep learning, model drift monitoring)

### Evidence folder (`reports/screenshots/`)
Spark UI, notebook outputs, Parquet listings in Docker, curves/matrices — everything shown on slides needs a screenshot + explanation.

---

## ⚠️ Risks
- **Laptop RAM** → cap driver memory (3 GB), Parquet pushdown, sample for tuning
- **400+ feature volume** → simple preprocessing first, iterate later
- **Streaming scope creep** → batch-first at heart; Phase 6 streaming is bounded to the
  checkpointed demo items (broker + producer + notebook + monitor adder) — the batch
  GBT-d5 remains the scoring authority
- **C: drive space (only ~41 GB)** → all large files on D:; Docker already relocated

## Demo day checklist
- [ ] Live dashboard or recorded demo ready
- [ ] Streaming demo (kill-restart + latency numbers)
- [ ] Docker services start with one command
- [ ] Demo rehearsed start to finish
- [ ] References slide cites ≥5 recent (2024–2026) sources