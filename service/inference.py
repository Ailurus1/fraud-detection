import json
from pathlib import Path
from confluent_kafka import Consumer, Producer
from catboost import CatBoostClassifier

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
                features = list(data['processed'].values())
                
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
                self.producer.poll(0)

            except Exception as e:
                print(f"Processing error: {e}")
