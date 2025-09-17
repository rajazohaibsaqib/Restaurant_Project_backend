from transformers import T5Tokenizer, T5ForConditionalGeneration, Trainer, TrainingArguments
import pandas as pd
import torch
from datasets import Dataset

# Load and prepare your dataset
df = pd.read_csv("restaurant_qa.csv")
df = df.rename(columns={"Question": "input_text", "Answer": "target_text"})

df["input_text"] = df["input_text"].astype(str)
df["target_text"] = df["target_text"].astype(str)
# Convert to HuggingFace Dataset
dataset = Dataset.from_pandas(df)

# Load tokenizer and model
tokenizer = T5Tokenizer.from_pretrained("t5-small")
model = T5ForConditionalGeneration.from_pretrained("t5-small")

# Tokenize dataset
def preprocess(batch):
    inputs = [str(x) for x in batch["input_text"]]
    targets = [str(x) for x in batch["target_text"]]

    model_inputs = tokenizer(
        inputs,
        padding="max_length",
        truncation=True,
        max_length=64
    )

    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            targets,
            padding="max_length",
            truncation=True,
            max_length=64
        )

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_ds = dataset.map(preprocess, batched=True)



# Define training arguments
training_args = TrainingArguments(
    output_dir="./t5_finetuned",
    per_device_train_batch_size=8,
    num_train_epochs=10,
    logging_steps=10,
    save_strategy="epoch"
)


# Define trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_ds,
    tokenizer=tokenizer
)

# Start training
trainer.train()

# Save model
model.save_pretrained("t5_restaurant_bot")
tokenizer.save_pretrained("t5_restaurant_bot")
