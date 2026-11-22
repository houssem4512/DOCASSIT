"""Update bench/eval.jsonl with actual document IDs from the DB.
Run this once before benchmarking, after uploading your sample docs.

Usage:
    python bench/update_eval_ids.py
"""
import json
import os
import sys
import re
from pathlib import Path

# Bootstrap Django so we can query the Document model
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.documents.models import Document

# Map each eval query to its topic number.
# Topics: 1=internet, 2=climate, 3=renewable energy, 4=AI, 5=education
# (matches the _NN_ pattern in sample doc titles like en_03_renewable_energy)
QUERY_TOPICS = {
    "q_ar_01": 3, "q_ar_02": 4, "q_ar_03": 2, "q_ar_04": 1, "q_ar_05": 5,
    "q_fr_01": 3, "q_fr_02": 4, "q_fr_03": 2, "q_fr_04": 1, "q_fr_05": 5,
    "q_en_01": 3, "q_en_02": 4, "q_en_03": 2, "q_en_04": 1, "q_en_05": 5,
}

# Group all docs in the DB by their topic number (parsed from the title).
# Works for sample docs named like: en_01_internet_history, fr_02_changement_climatique, etc.
docs_by_topic = {}
for d in Document.objects.all():
    m = re.search(r"_(\d{2})_", d.title)
    if m:
        topic = int(m.group(1))
        docs_by_topic.setdefault(topic, []).append(d.id)

print("Documents by topic:")
for topic in sorted(docs_by_topic.keys()):
    print(f"  Topic {topic}: {docs_by_topic[topic]}")

# Load the current eval.jsonl
eval_path = Path(__file__).resolve().parent / "eval.jsonl"
rows = []
with open(eval_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            r = json.loads(line)
            topic = QUERY_TOPICS.get(r["id"])
            if topic and topic in docs_by_topic:
                r["expected_doc_ids"] = docs_by_topic[topic]
            rows.append(r)

# Rewrite eval.jsonl with the actual document IDs
with open(eval_path, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"\nUpdated {len(rows)} queries in {eval_path}")
print("\nNow re-run: python bench/retrieval_eval.py --top-k 5")
