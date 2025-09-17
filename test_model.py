import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

# Load
model = SentenceTransformer('all-MiniLM-L6-v2')
question_texts = np.load("model/question_texts.npy", allow_pickle=True)
df = pd.read_csv("model/restaurant_qa.csv")
index = faiss.read_index("model/model.index")

def get_answer(user_query):
    embedding = model.encode([user_query], convert_to_numpy=True)
    _, indices = index.search(embedding, k=3)

    for idx in indices[0]:
        question = question_texts[idx]
        answer = df[df['Question'] == question]['Answer'].values[0]
        return answer

# Test
while True:
    q = input("You: ")
    if q.lower() == "exit":
        break
    ans = get_answer(q)
    print("Bot:", ans)
