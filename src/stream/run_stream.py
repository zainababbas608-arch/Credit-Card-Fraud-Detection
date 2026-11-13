"""Phase-6 streaming job: Kafka -> fraud model alerts (notebook-07 cells 0+1+2 condensed, headless)."""
import os, json, time
os.environ["PYSPARK_SUBMIT_ARGS"] = "--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 --driver-memory 4g pyspark-shell"
from pyspark.sql import SparkSession, functions as F
from pyspark.ml.functions import vector_to_array
from pyspark.ml.classification import GBTClassificationModel
from pyspark.ml.feature import VectorAssembler

W = "/home/jovyan/work"
spark = SparkSession.builder.appName("phase6-streaming").getOrCreate()
print("phase6-streaming up", flush=True)

FEATURES = json.load(open(f"{W}/data/stream/prep/cols.json"))
test_pp = spark.read.parquet(f"{W}/data/stream/source_test.parquet")
model = GBTClassificationModel.load(f"{W}/models/gbt_winner")
assembler = VectorAssembler(inputCols=FEATURES, outputCol="features", handleInvalid="keep")
schema = test_pp.schema

n = (model.transform(assembler.transform(test_pp)).filter(F.col("prediction") == 1).count())
print(f"serving contract check: {n:,} alerts at 0.5  (Phase 4 locked: 1,618 -- must match)", flush=True)

raw = (spark.readStream.format("kafka").option("kafka.bootstrap.servers", "kafka:9092")
       .option("subscribe", "transactions").option("startingOffsets", "latest").load())
parsed = raw.select(F.from_json(F.col("value").cast("string"), schema).alias("r")).select("r.*")
alerts = (model.transform(assembler.transform(parsed)).filter(F.col("prediction") == 1)
          .select("TransactionID", "TransactionAmt", "day", "isFraud",
                  vector_to_array("probability")[1].alias("p_fraud")))
q = (alerts.writeStream.format("parquet").option("path", f"{W}/data/stream/alerts")
     .option("checkpointLocation", f"{W}/data/stream/ckpt_alerts")
     .outputMode("append").trigger(processingTime="2 seconds").start())
qk = (alerts.select(F.to_json(F.struct("TransactionID", "TransactionAmt", "day", "isFraud", "p_fraud")).alias("value"))
      .writeStream.format("kafka").option("kafka.bootstrap.servers", "kafka:9092")
      .option("topic", "alerts").option("checkpointLocation", f"{W}/data/stream/ckpt_alerts_kafka").start())

print("streaming queries live:", q.id, "|", qk.id, "- ctrl-I (or pkill) stops cleanly", flush=True)
try:
    while True:
        time.sleep(60)
        pr = q.lastProgress or {}
        print(f"alive - last batch: {pr.get('numInputRows', 0)} input rows", flush=True)
except KeyboardInterrupt:
    pass
finally:
    q.stop(); qk.stop()
    print("stopped cleanly; checkpoints kept for resume", flush=True)
