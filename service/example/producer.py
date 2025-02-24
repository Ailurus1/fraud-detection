import json
import time
import random
from pathlib import Path
import polars as pl
import kagglehub
from confluent_kafka import Producer

path = Path(kagglehub.dataset_download("jainilcoder/online-payment-fraud-detection"))
df = pl.read_csv(path / "onlinefraud.csv")

class TransactionProducer:
    def __init__(self, bootstrap_servers=['localhost:9095', 'localhost:9096'], frequency=1.0):
        self.producer = Producer({
            'bootstrap.servers': ','.join(bootstrap_servers)
        })
        self.frequency = frequency
        self.load_data()

    def load_data(self):
        self.data = df.drop(['isFraud', 'isFlaggedFraud']).to_dicts()

    def delivery_report(self, err, msg):
        if err is not None:
            print(f'Message delivery failed: {err}')
        else:
            print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    def start_producing(self):
        while True:
            transaction = random.choice(self.data)
            
            self.producer.produce(
                'raw_transactions',
                json.dumps(transaction).encode('utf-8'),
                callback=self.delivery_report
            )
            self.producer.poll(0)
            
            time.sleep(1 / self.frequency)

def create_producer(bootstrap_servers=['localhost:9095', 'localhost:9096'], frequency=1.0):
    return TransactionProducer(bootstrap_servers, frequency)
