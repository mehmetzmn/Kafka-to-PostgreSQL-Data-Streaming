from kafka_stream import kafka_stream
from etl import etl_process
import time


def main():
    # First run the Kafka stream to collect data
    kafka_stream()

    # Wait a bit to ensure data is in MongoDB
    time.sleep(5)

    # Then run the ETL process
    etl_process()


if __name__ == "__main__":
    main()
