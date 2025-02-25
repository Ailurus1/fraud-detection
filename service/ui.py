import os
import json
import gradio as gr
import logging
from confluent_kafka import Consumer
from threading import Thread
import argparse

logger = logging.getLogger(__name__)

class TransactionUI:
    def __init__(self, bootstrap_servers=['localhost:9095', 'localhost:9096'], max_rows=10):
        self.consumer = Consumer({
            'bootstrap.servers': ','.join(bootstrap_servers),
            'group.id': 'ui_group',
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(['fraud_results'])
        self.max_rows = max_rows
        self.transactions = []

    def update_transactions(self, result):
        transaction = result['transaction']
        transaction['is_fraud'] = result['is_fraud']
        
        self.transactions.insert(0, transaction)
        if len(self.transactions) > self.max_rows:
            self.transactions.pop()
        logger.info("UI transactions list updated")

    def create_interface(self):
        with gr.Blocks() as interface:
            gr.Markdown("# Fraud Detection System")
            
            def get_transactions():
                rows = []
                for t in self.transactions:
                    color = "red" if t['is_fraud'] else "green"
                    rows.append(f"<tr style='background-color: {color}'>")
                    for k, v in t.items():
                        rows.append(f"<td>{v}</td>")
                    rows.append("</tr>")
                return "<table>" + "".join(rows) + "</table>"

            html = gr.HTML(value=get_transactions, every=1)

        return interface

    def _consume_messages(self):
        logger.info("Starting message consumption...")
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error(f"Consumer error: {msg.error()}")
                continue

            try:
                result = json.loads(msg.value().decode('utf-8'))
                self.update_transactions(result)
            except Exception as e:
                logger.error(f"Processing error: {e}")

    def start(self, open_browser: bool = True):
        logger.info("Starting UI service...")
        Thread(target=self._consume_messages, daemon=True).start()
        
        interface = self.create_interface()
        interface.launch(
            inbrowser=open_browser,
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )

def main(bootstrap_servers, max_rows, open_browser):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    ui = TransactionUI(
        bootstrap_servers=bootstrap_servers.split(','),
        max_rows=max_rows
    )
    ui.start(open_browser=open_browser)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transaction UI Service')
    parser.add_argument('--bootstrap-servers', 
                       default=os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9095,localhost:9096'),
                       help='Comma-separated list of bootstrap servers')
    parser.add_argument('--max-rows', type=int, default=10,
                       help='Maximum number of transactions to display')
    parser.add_argument('--no-browser', action='store_true',
                       help='Do not open browser automatically')
    args = parser.parse_args()
    main(args.bootstrap_servers, args.max_rows, not args.no_browser)
