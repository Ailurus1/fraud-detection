# Example producer

This is an example implementation of a producer that can be used in this anti-fraud system. By default it samples transactions from the Kaggle dataset [jainilcoder/online-payment-fraud-detection](https://www.kaggle.com/datasets/jainilcoder/online-payment-fraud-detection) that was also used for training baseline boosting model.

You can specify the frequency (requests per second) of produced messages. To use multiple identical producers with different workload please use `services/producers.py`.
