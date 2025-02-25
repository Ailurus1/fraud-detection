import os
import json
from pathlib import Path
from confluent_kafka import Consumer, Producer
from catboost import CatBoostClassifier
import numpy as np
import argparse

class TransactionInference:
    def __init__(self, model_path, bootstrap_servers=['localhost:9095', 'localhost:9096']):
        self.consumer = Consumer({
            'bootstrap.servers': ','.join(bootstrap_servers),
            'group.id': 'inference_group',
            'auto.offset.reset': 'earliest'
        })
        self.producer = Producer({
            'bootstrap.servers': ','.join(bootstrap_servers)
        })
        self.consumer.subscribe(['preprocessed_transactions'])
        self.load_model(model_path)

    def load_model(self, model_path):
        path = Path(model_path)
        self.model = CatBoostClassifier()
        self.model.load_model(path)

    def delivery_report(self, err, msg):
        if err is not None:
            print(f'Message delivery failed: {err}')

    def start(self):
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue

            try:
                data = json.loads(msg.value().decode('utf-8'))
                print(f"Received: msg={msg}\ndata={data}")
                
                features = list(data['processed'].values())
                print(f"Features: {features}\nType: {type(features[0])}")
                features = np.array(features).reshape(1, -1)
                
                prediction = bool(self.model.predict(features)[0])
                
                result = {
                    'transaction': data['original'],
                    'is_fraud': prediction
                }
                
                self.producer.produce(
                    'fraud_results',
                    json.dumps(result).encode('utf-8'),
                    callback=self.delivery_report
                )

            except Exception as e:
                print(f"Processing error: {e}")
                print(f"Features shape: {np.array(features).shape}")  # Debug info

def main(model_path, bootstrap_servers):
    print("Starting inference engine...")
    engine = TransactionInference(
        model_path=model_path,
        bootstrap_servers=bootstrap_servers.split(',')
    )
    engine.start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transaction Inference Service')
    parser.add_argument('--model-path', 
                       default='artifacts/00_boosting/fraud_detection_model.cbm',
                       help='Path to the model file')
    parser.add_argument('--bootstrap-servers', 
                       default=os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9095,localhost:9096'),
                       help='Comma-separated list of bootstrap servers')
    args = parser.parse_args()
    main(args.model_path, args.bootstrap_servers)
