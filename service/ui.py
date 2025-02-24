import json
import gradio as gr
from confluent_kafka import Consumer
from threading import Thread

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
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue

            try:
                result = json.loads(msg.value().decode('utf-8'))
                self.update_transactions(result)
            except Exception as e:
                print(f"Processing error: {e}")

    def start(self, open_browser: bool = True):
        Thread(target=self._consume_messages, daemon=True).start()
        
        interface = self.create_interface()
        interface.launch(inbrowser=open_browser)
