import sys
from datetime import datetime
import json
import numpy as np
from kafka import KafkaProducer, KafkaConsumer
import pandas as pd
from pymongo import MongoClient
from tqdm import tqdm

# Read parquet file


def read_parquet_data(file_path="./data/measurements.parquet"):
    try:
        df = pd.read_parquet(file_path)
        num_records = df.shape[0]
        return df.head(num_records)
    except Exception as e:
        print(f"Error reading parquet file: {str(e)}")
        return None

# for encoding int64 in JSON serializer


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def kafka_stream():
    data = read_parquet_data()
    if data is None:
        print("Failed to read parquet data", flush=True)
        return

    total_records = len(data)
    print(
        f"Starting to process {total_records} records at {datetime.now()}", flush=True)

    producer = None
    consumer = None
    mongo_client = None

    try:
        # Initialize consumer FIRST with "earliest" offset
        print("Initializing Kafka consumer...", flush=True)
        consumer = KafkaConsumer(
            'sensor-data-topic',
            bootstrap_servers=["kafka:29092"],
            auto_offset_reset="earliest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            consumer_timeout_ms=5000,
            fetch_min_bytes=1024 * 1024,  # 1MB minimum fetch
            max_poll_records=5000,  # Increase records per poll
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000
        )

        print("Initializing Kafka producer...", flush=True)
        producer = KafkaProducer(
            bootstrap_servers=["kafka:29092"],
            value_serializer=lambda v: json.dumps(
                v, cls=NpEncoder).encode("utf-8")
        )

        print("Connecting to MongoDB...", flush=True)
        mongo_client = MongoClient("mongodb://mongodb:27017/")
        db = mongo_client['sensor_data']
        collection = db["sensor_data"]

        # Producer phase with tqdm
        print(f"\nProducer Phase - Starting at {datetime.now()}", flush=True)
        with tqdm(total=total_records, desc="Producing messages") as pbar:
            for i in range(len(data)):
                producer.send("sensor-data-topic", {
                    "temp": data.iloc[i]['temp'],
                    "humidity": data.iloc[i]['humidity'],
                    "date_time": data.iloc[i]["date_time"]
                })
                pbar.update(1)

        producer.flush()
        print(f"\nAll messages sent to Kafka at {datetime.now()}", flush=True)

        # Consumer phase with tqdm
        print(f"\nConsumer Phase - Starting at {datetime.now()}", flush=True)
        batch_size = 1000
        batch = []
        with tqdm(total=total_records, desc="Consuming messages") as pbar:
            for message in consumer:
                batch.append(message.value)
                if len(batch) >= batch_size:
                    collection.insert_many(batch, ordered=False)
                    pbar.update(len(batch))
                    batch = []

            # Insert remaining documents
            if batch:
                collection.insert_many(batch, ordered=False)
                pbar.update(len(batch))

        print(f"\nProcessing completed at {datetime.now()}", flush=True)

    except Exception as e:
        print(f"\nAn error occurred at {datetime.now()}: {str(e)}", flush=True)
    finally:
        print("\nClosing connections...", flush=True)
        if producer:
            producer.close()
        if consumer:
            consumer.close()
        if mongo_client:
            mongo_client.close()
        print("All connections closed", flush=True)
