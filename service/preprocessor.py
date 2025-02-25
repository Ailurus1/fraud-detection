import os
import json
import pickle
from pathlib import Path
from confluent_kafka import Consumer, Producer
import argparse

class TransactionPreprocessor:
    def __init__(self, metadata_path, bootstrap_servers=['localhost:9095', 'localhost:9096']):
        self.consumer = Consumer({
            'bootstrap.servers': ','.join(bootstrap_servers),
            'group.id': 'preprocessor_group',
            'auto.offset.reset': 'earliest'
        })
        self.producer = Producer({
            'bootstrap.servers': ','.join(bootstrap_servers)
        })
        self.consumer.subscribe(['anonymized_transactions'])
        self.load_metadata(metadata_path)

    def load_metadata(self, metadata_path):
        path = Path(metadata_path)
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
                print(f"Received: msg={msg}\ndata={transaction}")
                processed = self.preprocess_transaction(transaction)
                
                self.producer.produce(
                    'preprocessed_transactions',
                    json.dumps({
                        'original': transaction,
                        'processed': processed
                    }).encode('utf-8'),
                    callback=self.delivery_report
                )

            except Exception as e:
                print(f"Processing error: {e}")

def main(metadata_path, bootstrap_servers):
    print("Starting preprocessor...")
    preprocessor = TransactionPreprocessor(
        metadata_path=metadata_path,
        bootstrap_servers=bootstrap_servers.split(',')
    )
    preprocessor.start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transaction Preprocessor Service')
    parser.add_argument('--metadata-path', 
                       default='artifacts/00_boosting/metadata.pkl',
                       help='Path to metadata pickle file')
    parser.add_argument('--bootstrap-servers', 
                       default=os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9095,localhost:9096'),
                       help='Comma-separated list of bootstrap servers')
    args = parser.parse_args()
    main(args.metadata_path, args.bootstrap_servers)
