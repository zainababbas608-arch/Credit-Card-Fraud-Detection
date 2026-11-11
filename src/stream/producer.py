"""Phase-6 streaming tier - producer.
Replays the preprocessed test window (notebook 07 cell 1's artifact) as a live Kafka feed:
shuffled row order (fixed seed), one JSON row per message, rate-limited. The streaming job
(nx 07) is the consumer; `data/stream/source_test.parquet` must exist before this runs."""
import json, random, sys, time
import pyarrow.parquet as pq
from kafka import KafkaProducer

SRC, TOPIC = "/home/jovyan/work/data/stream/source_test.parquet", "transactions"
broker = sys.argv[1] if len(sys.argv) > 1 else "kafka:9092"
rps    = int(sys.argv[2]) if len(sys.argv) > 2 else 250

tb = pq.read_table(SRC)
rows = tb.to_pylist()                          # ~46k dicts, one shot: few hundred MB RAM, fine
random.Random(7).shuffle(rows)
print(f"producer: {len(rows):,} rows -> {broker}/{TOPIC} @ {rps}/s")
p = KafkaProducer(bootstrap_servers=broker, linger_ms=10,
                  value_serializer=lambda v: json.dumps(v).encode())
t0 = time.time()
for i, r in enumerate(rows):
    dt = t0 + (i + 1) / rps - time.time()
    if dt > 0:
        time.sleep(dt)
    p.send(TOPIC, r)
    if i % 250 == 0:                              # the dashboard's Live header reads this progress file
        open("/home/jovyan/work/data/stream/sent.txt", "w").write(str(i + 1))
open("/home/jovyan/work/data/stream/sent.txt", "w").write(str(len(rows)))
p.flush()
print(f"done: {sent if (sent := i + 1) else 0:,} rows in {time.time() - t0:.1f}s")