import json
import hashlib
from confluent_kafka import Consumer, Producer

class TransactionAnonymizer:
    def __init__(self, bootstrap_servers=['localhost:9095', 'localhost:9096']):
        self.consumer = Consumer({
            'bootstrap.servers': ','.join(bootstrap_servers),
            'group.id': 'anonymizer_group',
            'auto.offset.reset': 'earliest'
        })
        self.producer = Producer({
            'bootstrap.servers': ','.join(bootstrap_servers)
        })
        self.consumer.subscribe(['raw_transactions'])

    def anonymize_id(self, id_str):
        return hashlib.sha256(id_str.encode()).hexdigest()[:16]

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
                transaction = json.loads(msg.value().decode('utf-8'))
                
                transaction['nameOrig'] = self.anonymize_id(transaction['nameOrig'])
                transaction['nameDest'] = self.anonymize_id(transaction['nameDest'])
                
                self.producer.produce(
                    'anonymized_transactions',
                    json.dumps(transaction).encode('utf-8'),
                    callback=self.delivery_report
                )
                self.producer.poll(0)
            except Exception as e:
                print(f"Processing error: {e}")
