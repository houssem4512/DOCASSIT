"""finetune package — embedding model fine-tuning + comparison.

Pipeline:
    1. (optional) python finetune/build_triples.py  → auto-generate triples
    2. python finetune/train.py                     → fine-tune the model
    3. EMBEDDING_MODEL=./models/docassist-ft bash bench/run_all.sh finetuned
                                                   → re-benchmark with the new model
    4. Compare bench/results_*_baseline.json vs bench/results_*_finetuned.json
"""
