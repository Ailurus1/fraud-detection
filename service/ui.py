import os
import json
import gradio as gr
import logging
from confluent_kafka import Consumer
from threading import Thread
import argparse
from collections import Counter
import pandas as pd

logger = logging.getLogger(__name__)

class TransactionUI:
    def __init__(self, bootstrap_servers=['localhost:9095', 'localhost:9096'], max_rows=15):
        self.consumer = Consumer({
            'bootstrap.servers': ','.join(bootstrap_servers),
            'group.id': 'ui_group',
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(['fraud_results'])
        self.max_rows = max_rows
        self.transactions = []
        self.total_transactions = 0
        self.total_fraud_detected = 0
        self.counts_by_type = {}

    def update_transactions(self, result):
        transaction = result['transaction']
        transaction['is_fraud'] = result['is_fraud']
        
        self.transactions.insert(0, transaction)
        if len(self.transactions) > self.max_rows:
            self.transactions.pop()

        self.total_transactions += 1
        
        self.total_fraud_detected += int(transaction['is_fraud'])
        
        if transaction["type"] not in self.counts_by_type:
            self.counts_by_type[transaction["type"]] = 0

        self.counts_by_type[transaction["type"]] += 1
        
        logger.info("UI transactions list updated")

    def create_interface(self):
        with gr.Blocks() as interface:
            gr.Markdown("# Fraud Detection System")

            with gr.Row():
                def get_transactions():
                    if not self.transactions:
                        return "<table border='1'><tr><th>Waiting for transactions...</th></tr></table>"
                    
                    headers = list(self.transactions[0].keys())
                    headers.remove("type_encoded")
                    header_row = "<tr>" + "".join([f"<th style='padding: 8px; background-color: silver'><b>{h}</b></th>" for h in headers]) + "</tr>"
                    
                    rows = []
                    for t in self.transactions:
                        color = "#f45f5f" if t['is_fraud'] else "#86aa88"
                        row = [f"<tr style='background-color: {color}'>"]
                        for k in headers:
                            row.append(f"<td style='padding: 8px'>{t[k]}</td>")
                        row.append("</tr>")
                        rows.append("".join(row))
                    
                    return f"<table border='1' style='border-collapse: collapse; width: 100%'>{header_row}{''.join(rows)}</table>"

                html = gr.HTML(value=get_transactions, every=1)
            
            with gr.Row():
                with gr.Column():
                    def get_transaction_counts():
                        data = pd.DataFrame(
                            list(self.counts_by_type.items()), 
                            columns=["Transaction Type", "Count"]
                        )
                        return data

                    barplot = gr.BarPlot(
                        value=get_transaction_counts,
                        x="Transaction Type",
                        y="Count",
                        every=8
                    )
                
                with gr.Column():
                    with gr.Row():
                        def get_fraud_counts():
                            return self.total_fraud_detected

                        total_fraud_detected = gr.Textbox(value=get_fraud_counts, label="Total Fraud Transactions Detected", every=4)

                    with gr.Row():
                        def get_total_transactions():
                            return self.total_transactions

                        total_transactions = gr.Textbox(value=get_total_transactions, label="Total Transactions Processed", every=4)

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
    parser.add_argument('--max-rows', type=int, default=15,
                       help='Maximum number of transactions to display')
    parser.add_argument('--no-browser', action='store_true',
                       help='Do not open browser automatically')
    args = parser.parse_args()
    main(args.bootstrap_servers, args.max_rows, not args.no_browser)
