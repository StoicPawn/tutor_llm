"""Optional LoRA/SFT training path. Requires a CUDA-capable machine and requirements-train.txt.

This script trains teaching style, not book facts. Book knowledge remains in the RAG index.
"""
from __future__ import annotations
import argparse, json
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig
from trl import SFTTrainer

p = argparse.ArgumentParser()
p.add_argument("--model", default="Qwen/Qwen3-4B")
p.add_argument("--data", default="training/feedback_sft.jsonl")
p.add_argument("--output", default="training/output/studyforge-lora")
a = p.parse_args()

rows = [json.loads(x) for x in open(a.data, encoding="utf-8") if x.strip()]
if not rows:
    raise SystemExit("Dataset vuoto. Raccogli feedback e lancia prima export_dataset.py")

tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(a.model, device_map="auto", torch_dtype="auto", trust_remote_code=True)

def render(row):
    return {"text": tok.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=False)}
ds = Dataset.from_list([render(r) for r in rows])
peft = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
args = TrainingArguments(output_dir=a.output, per_device_train_batch_size=1, gradient_accumulation_steps=8, learning_rate=2e-4, num_train_epochs=2, logging_steps=5, save_strategy="epoch", bf16=True)
trainer = SFTTrainer(model=model, args=args, train_dataset=ds, peft_config=peft, processing_class=tok)
trainer.train()
trainer.save_model(a.output)
print(a.output)
