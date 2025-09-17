import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import os

df = pd.read_csv("model/restaurant_qa.csv")
model = SentenceTransformer('all-MiniLM-L6-v2')

question_texts = df['Question'].tolist()
question_embeddings = model.encode(question_texts, convert_to_numpy=True)

dimension = question_embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(question_embeddings)

os.makedirs("model", exist_ok=True)
faiss.write_index(index, "model/model.index")
np.save("model/question_texts.npy", np.array(question_texts))
print("✅ Model trained and saved.")
