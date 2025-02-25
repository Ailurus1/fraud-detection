import os
import json
import hashlib
import logging
import argparse
from confluent_kafka import Consumer, Producer

logger = logging.getLogger(__name__)

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
            logger.error(f'Message delivery failed: {err}')

    def start(self):
        logger.info("Starting anonymizer service...")
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error(f"Consumer error: {msg.error()}")
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
                logger.info("Transaction anonymized successfully")

            except Exception as e:
                logger.error(f"Processing error: {e}")

def main(bootstrap_servers):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    anonymizer = TransactionAnonymizer(bootstrap_servers=bootstrap_servers.split(','))
    anonymizer.start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transaction Anonymizer Service')
    parser.add_argument('--bootstrap-servers', 
                       default=os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9095,localhost:9096'),
                       help='Comma-separated list of bootstrap servers')
    args = parser.parse_args()
    main(args.bootstrap_servers)

