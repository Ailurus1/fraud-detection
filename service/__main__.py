import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from service.anonimizer import TransactionAnonymizer
from service.preprocessor import TransactionPreprocessor
from service.inference import TransactionInference
from service.ui import TransactionUI

def main(producer_module, n_producers, frequency, model_path):
    try:
        if producer_module == 'example':
            from example.producer import create_producer
        else:
            raise NotImplementedError("Only 'example' producer module is supported")
        
        with ThreadPoolExecutor(max_workers=n_producers) as executor:
            for _ in range(n_producers):
                producer = create_producer(frequency=frequency)
                executor.submit(producer.start_producing)
        
        anonymizer = TransactionAnonymizer()
        anonymizer.start()

        preprocessor = TransactionPreprocessor()
        preprocessor.start()

        engine = TransactionInference(model_path)
        engine.start()

        ui = TransactionUI()
        ui.start()

    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--producer", default="example")
    parser.add_argument("--n-producers", type=int, default=1)
    parser.add_argument("--frequency", type=float, default=1.0)
    parser.add_argument("--model-path", type=str, default="../artifacts/00_boosting/fraud_detection_model.cbm")
    
    args = parser.parse_args()
    main(args.producer, args.n_producers, args.frequency, args.model_path)
