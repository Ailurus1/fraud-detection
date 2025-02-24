import json
import pickle
from pathlib import Path
from confluent_kafka import Consumer, Producer

class TransactionPreprocessor:
    def __init__(self, bootstrap_servers=['localhost:9095', 'localhost:9096']):
        self.consumer = Consumer({
            'bootstrap.servers': ','.join(bootstrap_servers),
            'group.id': 'preprocessor_group',
            'auto.offset.reset': 'earliest'
        })
        self.producer = Producer({
            'bootstrap.servers': ','.join(bootstrap_servers)
        })
        self.consumer.subscribe(['anonymized_transactions'])
        self.load_metadata()

    def load_metadata(self):
        path = Path('../artifacts/00_boosting/metadata.pkl')
        with open(path, 'rb') as f:
            metadata = pickle.load(f)
            self.features = metadata['features']
            self.label_encoder = metadata['label_encoder']

    def delivery_report(self, err, msg):
        if err is not None:
            print(f'Message delivery failed: {err}')

    def preprocess_transaction(self, transaction):
        transaction['type_encoded'] = int(self.label_encoder.transform([transaction['type']])[0])
        processed = {feature: transaction.get(feature, 0) for feature in self.features}
        return processed

    def start(self):
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue

            try:
                transaction = json.loads(msg.value().decode('utf-8'))
                processed = self.preprocess_transaction(transaction)
                
                self.producer.produce(
                    'preprocessed_transactions',
                    json.dumps({
                        'original': transaction,
                        'processed': processed
                    }).encode('utf-8'),
                    callback=self.delivery_report
                )
                self.producer.poll(0)
            except Exception as e:
                print(f"Processing error: {e}")
