"""Phase-6 streaming producer: replays preprocessed test window as live Kafka feed."""
import json, random, sys, time
import pyarrow.parquet as pq
from kafka import KafkaProducer

SRC, TOPIC = "/home/jovyan/work/data/stream/source_test.parquet", "transactions"
broker = sys.argv[1] if len(sys.argv) > 1 else "kafka:9092"
rps = int(sys.argv[2]) if len(sys.argv) > 2 else 250

tb = pq.read_table(SRC)
rows = tb.to_pylist()
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
    if i % 250 == 0:
        with open("/home/jovyan/work/data/stream/sent.txt", "w") as f:
            f.write(str(i + 1))

with open("/home/jovyan/work/data/stream/sent.txt", "w") as f:
    f.write(str(len(rows)))
p.flush()
print(f"done: {len(rows):,} rows in {time.time() - t0:.1f}s")