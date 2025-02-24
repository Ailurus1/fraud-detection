import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from service.anonimizer import TransactionAnonymizer
from service.preprocessor import TransactionPreprocessor
from service.inference import TransactionInference
from service.ui import TransactionUI

def main(producer_module, n_producers, frequency, model_path, metadata_path):
    try:
        if producer_module == 'example':
            from example.producer import create_producer # type: ignore
        else:
            raise NotImplementedError("Only 'example' producer module is supported right now")
        
        print("Starting producers...")
        executor = ThreadPoolExecutor(max_workers=n_producers)
        futures = []
        for _ in range(n_producers):
            producer = create_producer(frequency=frequency)
            futures.append(executor.submit(producer.start_producing))
        
        services_threads = []
        print("Starting anonymizer...")
        anonymizer = TransactionAnonymizer()
        services_threads.append(Thread(target=anonymizer.start, daemon=True).start())

        print("Starting preprocessor...")
        preprocessor = TransactionPreprocessor(metadata_path=metadata_path)
        services_threads.append(Thread(target=preprocessor.start, daemon=True).start())

        print("Starting inference engine...")
        engine = TransactionInference(model_path=model_path)
        services_threads.append(Thread(target=engine.start, daemon=True).start())

        print("Starting UI...")
        ui = TransactionUI()
        services_threads.append(ui.start())

        while True:
            continue

    except KeyboardInterrupt:
        print("Shutting down...")
        executor.shutdown(wait=False)
        for thread in services_threads:
            thread.join()
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--producer", default="example")
    parser.add_argument("--n-producers", type=int, default=1)
    parser.add_argument("--frequency", type=float, default=0.25)
    parser.add_argument("--model-path", type=str, default="artifacts/00_boosting/fraud_detection_model.cbm")
    parser.add_argument("--metadata-path", type=str, default="artifacts/00_boosting/metadata.pkl")
    
    args = parser.parse_args()
    main(args.producer, args.n_producers, args.frequency, args.model_path, args.metadata_path)
