"""Long-running, configured Spark Structured Streaming job for domain events.

Run with spark-submit after installing the Kafka and Parquet connectors. Set
STREAMING_* variables from the deployment platform; defaults are lab-safe.
"""
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, window
from pyspark.sql.types import StringType, StructType, TimestampType

schema = StructType().add("event_id", StringType()).add("event_type", StringType()) \
    .add("occurred_at", TimestampType()).add("request_id", StringType())

spark = SparkSession.builder.appName(os.getenv("STREAMING_APP_NAME", "rag-domain-events")).getOrCreate()
events = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")) \
    .option("subscribe", os.getenv(
        "STREAMING_TOPICS",
        "telemetry.ingested,transaction.processed,payments.transaction.ingested.v1,"
        "payments.risk.scored.v1,audit.record.logged,ingestion.compensated,"
        "transaction.compensated,payments.compensated.v1,state.transition.logged",
    )) \
    .option("startingOffsets", os.getenv("STREAMING_STARTING_OFFSETS", "latest")).load()
parsed = events.select(from_json(col("value").cast("string"), schema).alias("event")).select("event.*")
aggregated = parsed.withWatermark("occurred_at", "10 minutes").groupBy(
    window("occurred_at", "1 minute"), "event_type"
).count()
query = aggregated.writeStream.format("parquet") \
    .option("path", os.getenv("STREAMING_OUTPUT_PATH", "s3a://streaming/events")) \
    .option("checkpointLocation", os.getenv("STREAMING_CHECKPOINT_PATH", "s3a://streaming/checkpoints/domain-events")) \
    .outputMode("append") \
    .trigger(processingTime=os.getenv("STREAMING_TRIGGER_INTERVAL", "30 seconds")) \
    .start()
query.awaitTermination()
