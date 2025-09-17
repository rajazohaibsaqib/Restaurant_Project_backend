from transformers import T5Tokenizer, T5ForConditionalGeneration
import torch

# Load the fine-tuned model and tokenizer
model_path = "t5_restaurant_bot"
tokenizer = T5Tokenizer.from_pretrained(model_path)
model = T5ForConditionalGeneration.from_pretrained(model_path)

# Move model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

def chat_debug(question, max_length=64):
    print(f"\n🟢 User Question: {question}")

    # Tokenize the input
    input_encoding = tokenizer(question, return_tensors="pt", truncation=True, max_length=max_length, padding="max_length")
    input_ids = input_encoding["input_ids"].to(device)

    print("🔹 Tokenized Input IDs:", input_ids[0].tolist())
    print("🔹 Decoded Input:", tokenizer.decode(input_ids[0], skip_special_tokens=False))

    # Generate output
    with torch.no_grad():
        output_ids = model.generate(input_ids, max_length=max_length, num_beams=4, early_stopping=True)

    print("🔸 Output Token IDs:", output_ids[0].tolist())
    print("🔸 Decoded Output:", tokenizer.decode(output_ids[0], skip_special_tokens=False))

    response = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    print("✅ Final Clean Response:", response)
    print("-" * 60)
    return response

# Example test cases
test_questions = [
    "tell me about menu items?",
    "Where is your restaurant located?",
    "can you offer wifi services?",
    "i want 1 Greek salad",
    "I donot like your restaurant.",
    "Tell me when pakistan win the match"
]

# Run test with debug
for question in test_questions:
    chat_debug(question)
