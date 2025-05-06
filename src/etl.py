# TODO:
# 1. Read data from MongoDB
# 2. Transform in pandas
# 3. Write data to PostgreSQL

import pandas as pd
from pymongo import MongoClient
from sqlalchemy import create_engine
from datetime import datetime
from tqdm import tqdm


def read_data_from_mongodb():
    mongo_client = None
    try:
        print(f"Starting MongoDB read at {datetime.now()}", flush=True)
        mongo_client = MongoClient("mongodb://mongodb:27017/")
        db = mongo_client["sensor_data"]
        collection = db["sensor_data"]

        # Get total count for progress tracking
        total_count = collection.count_documents({})
        print(f"Total documents to process: {total_count}", flush=True)

        batch_size = 1000
        data = []
        cursor = collection.find({}, {'_id': 0}).batch_size(batch_size)

        # Use tqdm for progress tracking
        with tqdm(total=total_count, desc="Reading from MongoDB") as pbar:
            for document in cursor:
                data.append(document)
                pbar.update(1)

        print(f"\nMongoDB read completed at {datetime.now()}", flush=True)
        return data
    except Exception as e:
        print(f"Error reading data from MongoDB: {e}")
        return None
    finally:
        if mongo_client:
            mongo_client.close()
            print("MongoDB connection closed")


def transform_data(data):
    if not data:
        return None
    df = pd.DataFrame(data)

    # Convert timestamp to datetime
    df['date_time'] = pd.to_datetime(df['date_time'])

    # Add any additional transformations here
    df.set_index("date_time", inplace=True)

    avg_temp_10min_intervals = df["temp"].resample("10min").mean()
    avg_humidity_20min_intervals = df["humidity"].resample("20min").mean()

    df = pd.concat([avg_temp_10min_intervals,
                   avg_humidity_20min_intervals], axis=1)

    df = df.reset_index()
    return df


def write_to_postgresql(df):
    if df is None:
        return

    try:
        engine = create_engine(
            'postgresql://postgres:postgres@postgres:5432/sensordata')

        # Write in chunks with tqdm progress bar
        chunk_size = 1000
        total_chunks = (len(df) + chunk_size - 1) // chunk_size

        with tqdm(total=total_chunks, desc="Writing to PostgreSQL") as pbar:
            for i in range(0, len(df), chunk_size):
                chunk = df[i:i + chunk_size]
                if i == 0:
                    chunk.to_sql('sensor_measurements', engine,
                                 if_exists='replace', index=False)
                else:
                    chunk.to_sql('sensor_measurements', engine,
                                 if_exists='append', index=False)
                pbar.update(1)

        print("Data successfully written to PostgreSQL")
    except Exception as e:
        print(f"Error writing to PostgreSQL: {e}")


def etl_process():
    # Read
    data = read_data_from_mongodb()

    # Transform
    transformed_data = transform_data(data)

    # Load
    write_to_postgresql(transformed_data)
