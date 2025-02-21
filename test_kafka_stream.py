import unittest
import pandas as pd
import numpy as np
from kafka_stream import read_parquet_data, NpEncoder
from etl import transform_data, write_to_postgresql
import json
import os
from unittest.mock import Mock, patch
import mongomock


class TestKafkaStream(unittest.TestCase):
    def setUp(self):
        # Create a small test parquet file
        self.test_data = pd.DataFrame({
            'temp': [20.5, 21.0, 22.0],
            'humidity': [45.0, 46.0, 47.0],
            'date_time': pd.date_range(start='2024-01-01', periods=3, freq='H')
        })
        self.test_data.to_parquet('test_measurements.parquet')

    def tearDown(self):
        # Clean up test file
        if os.path.exists('test_measurements.parquet'):
            os.remove('test_measurements.parquet')

    def test_read_parquet_data(self):
        df = read_parquet_data('test_measurements.parquet')
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 3)
        self.assertTrue(all(col in df.columns for col in [
                        'temp', 'humidity', 'date_time']))

    def test_read_parquet_data_nonexistent_file(self):
        df = read_parquet_data('nonexistent.parquet')
        self.assertIsNone(df)

    def test_np_encoder(self):
        test_data = {
            'int64': np.int64(42),
            'float64': np.float64(3.14),
            'array': np.array([1, 2, 3])
        }
        encoded = json.dumps(test_data, cls=NpEncoder)
        self.assertIsInstance(encoded, str)
        decoded = json.loads(encoded)
        self.assertEqual(decoded['int64'], 42)
        self.assertEqual(decoded['float64'], 3.14)
        self.assertEqual(decoded['array'], [1, 2, 3])


class TestETL(unittest.TestCase):
    def setUp(self):
        # Create a mock MongoDB client
        self.mongo_client = mongomock.MongoClient()
        self.db = self.mongo_client.sensor_data
        self.collection = self.db.sensor_data

        # Test data
        self.test_data = [
            {'temp': 20.5, 'humidity': 45.0, 'date_time': '2024-01-01 00:00:00'},
            {'temp': 21.0, 'humidity': 46.0, 'date_time': '2024-01-01 00:05:00'},
            {'temp': 22.0, 'humidity': 47.0, 'date_time': '2024-01-01 00:10:00'}
        ]

        # Insert test data into mock MongoDB
        self.collection.insert_many(self.test_data)

    def tearDown(self):
        # Clean up the mock database
        self.mongo_client.drop_database('sensor_data')

    def test_transform_data(self):
        # Transform data
        df = transform_data(self.test_data)

        self.assertIsNotNone(df)
        self.assertTrue('temp' in df.columns)
        self.assertTrue('humidity' in df.columns)
        self.assertTrue('date_time' in df.columns)

        # Test resampling
        self.assertTrue(isinstance(df['date_time'].iloc[0], pd.Timestamp))

    def test_transform_data_empty(self):
        df = transform_data([])
        self.assertIsNone(df)

    @patch('etl.create_engine')
    def test_write_to_postgresql(self, mock_create_engine):
        # Create test DataFrame
        df = pd.DataFrame({
            'temp': [20.5, 21.0],
            'humidity': [45.0, 46.0],
            'date_time': ['2024-01-01 00:00:00', '2024-01-01 00:10:00']
        })

        # Mock SQLAlchemy engine
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Test the function
        write_to_postgresql(df)

        # Verify that create_engine was called with correct parameters
        mock_create_engine.assert_called_once_with(
            'postgresql://postgres:postgres@postgres:5432/sensordata'
        )


if __name__ == '__main__':
    unittest.main()
