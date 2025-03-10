import os
import argparse
from concurrent.futures import ThreadPoolExecutor
import sys
import random


def main(producer_module, n_producers, frequency, bootstrap_servers):
    try:
        if producer_module == "example":
            from services.example.producer import create_producer  # type: ignore
        else:
            raise NotImplementedError(
                "Only 'example' producer module is supported right now"
            )

        print("Starting producers...")
        executor = ThreadPoolExecutor(max_workers=n_producers)
        futures = []
        for _ in range(n_producers):
            current_frequency = frequency
            if current_frequency is None:
                current_frequency = random.uniform(0.5, 5)
            producer = create_producer(
                bootstrap_servers=bootstrap_servers.split(","),
                frequency=current_frequency,
            )
            futures.append(executor.submit(producer.start_producing))

        # Wait forever until KeyBoardInterrupt
        for future in futures:
            future.result()

    except KeyboardInterrupt:
        print("Shutting down...")
        executor.shutdown(wait=False)
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transaction Producer Service")
    parser.add_argument("--producer", default="example", help="Producer module to use")
    parser.add_argument(
        "--n-producers", type=int, default=2, help="Number of producer instances"
    )
    parser.add_argument(
        "--frequency", type=float, default=None, help="Production frequency in seconds"
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=os.environ.get("BOOTSTRAP_SERVERS", "localhost:9095,localhost:9096"),
        help="Comma-separated list of bootstrap servers",
    )
    args = parser.parse_args()
    main(args.producer, args.n_producers, args.frequency, args.bootstrap_servers)
