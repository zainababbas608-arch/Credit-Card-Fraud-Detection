# Fraud Watch launcher:  .\run_dashboard.ps1         -> replay dashboard only
#                        .\run_dashboard.ps1 -Live   -> + kafka, streaming job, producer
#                        .\run_dashboard.ps1 -Stop   -> stop app + stream + producer
param([switch]$Live, [switch]$Stop)
$ErrorActionPreference = "Continue"

docker inspect -f "{{.State.Running}}" fraud-datascience *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "container fraud-datascience is NOT running" -ForegroundColor Red; exit 1 }

if ($Stop) {
    docker exec fraud-datascience /bin/bash -lc "pkill -f 'streamlit run|run_stream.py|producer.py' || true"
    Write-Host "stopped - kafka left running" -ForegroundColor Green; exit
}

docker network connect creditcardfrauddetection_default fraud-datascience 2>$null   # safe if already attached
if ($Live) {
    docker inspect -f "{{.State.Running}}" fraud-kafka *> $null
    if ($LASTEXITCODE -ne 0) { docker compose up -d kafka | Out-Null; Start-Sleep 20 }
    docker exec fraud-datascience /bin/bash -lc "pkill -f 'run_stream.py|producer.py' || true"   # restart = resume via checkpoints
}

docker exec fraud-datascience /bin/bash -lc "pkill -f 'streamlit run' || true"
docker exec -w /home/jovyan/work -d fraud-datascience /opt/venv/fraudui/bin/streamlit run src/dashboard/app.py --server.port 8501

if ($Live) {
    docker exec -d -w /home/jovyan/work fraud-datascience /bin/bash -lc "/opt/conda/bin/python -u src/stream/run_stream.py > data/stream/job.log 2>&1"
    docker exec -w /home/jovyan/work -d fraud-datascience /opt/venv/fraudui/bin/python -u src/stream/producer.py kafka:9092 100
    Write-Host "live tier starting - Spark boots ~1 min; job log: data/stream/job.log" -ForegroundColor Yellow
}
Start-Sleep 3
Start-Process "http://localhost:8501"