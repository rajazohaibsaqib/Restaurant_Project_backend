# import numpy as np
# import pandas as pd
# import faiss
# from sentence_transformers import SentenceTransformer
#
# # Load your dataset
# df = pd.read_csv(r"C:\Users\lenovo\Projects\CourseAdvisorChat\Model\Dataset.csv",encoding='latin-1')  # Change this to your actual file
#
# # Load pre-trained BERT model
# model = SentenceTransformer('all-MiniLM-L6-v2')
#
# # Convert all questions to embeddings
# question_texts = df['Question'].tolist()
# question_embeddings = model.encode(question_texts, convert_to_numpy=True)
#
# # Store embeddings in FAISS index
# dimension = question_embeddings.shape[1]
# index = faiss.IndexFlatL2(dimension)
# index.add(question_embeddings)
#
# # Save the FAISS index and questions
# faiss.write_index(index, "Question_embeddings.index")
# np.save("Question_texts.npy", np.array(question_texts))
#
# print("Model training completed! Saved embeddings for fast retrieval.")


import re
import  os
import html
import faiss
import random

import pyodbc
import pyttsx3
import whisper
import subprocess
import numpy as np
import pandas as pd
from datetime import datetime
from Model.Configure import Session
from Model.ChatHistory import ChatHistory
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from sentence_transformers import SentenceTransformer
from Model.ErrorHistory import ErrorHistory
from Controller.KnowledgeBaseController import get_all_knowledgebase
from Model.KnowledgeBaseValue import KnowledgeBase

# -----------------------------------------------------------------------------------------------------

# Load the dataset
df = pd.read_csv(r"C:\Users\lenovo\Projects\CourseAdvisorChat\Model\Dataset.csv", encoding='latin-1')
# Load the pre-trained model
model = SentenceTransformer('all-MiniLM-L6-v2')
# Load stored FAISS index and question texts
question_texts = np.load(r"C:\Users\lenovo\Projects\CourseAdvisorChat\Model\Question_texts.npy", allow_pickle=True)
index = faiss.read_index(r"C:\Users\lenovo\Projects\CourseAdvisorChat\Model\Question_embeddings.index")
app = Flask(__name__)
UPLOAD_QUERIES_FOLDER = r"C:\Users\lenovo\Projects\CourseAdvisorChat\Uploads\UserQuery"
UPLOAD_ANSWERS_FOLDER = r"C:\Users\lenovo\Projects\CourseAdvisorChat\Uploads\ModelAnswer"
#model whisper that is used to concert speech into text
whisper_model = whisper.load_model("tiny")

# -----------------------------------------------------------------------------------------------------

db = Session()

def get_answer():
    data = request.json
    question = data.get("question")
    reg_no = data.get("reg_no")  # Updated: consistent naming
    currentsemesterno = data.get("currentsemesterno")
    print('DATA :', data)

    if not question or not reg_no:
        return jsonify({"error": "Both question and regNo are required!"}), 400

    if not question:
        return jsonify({"answer": "Error: Question is required!"}), 400
    if not reg_no:
        return jsonify({"answer": "Error: Registration number is required!"}), 400


    # Step 1: Semantic Search
    # Convert question to embedding
    query_embedding = model.encode([question], convert_to_numpy=True)


    # Semantic Search top-k similar questions
    k = 5
    _, indices = index.search(query_embedding, k)

    # Collect all possible answers from the top-k matched questions
    unique_answers = set()
    matched_questions = []
    for idx in indices[0]:
        matched_question = question_texts[idx]
        matched_questions.append(matched_question)
        answers = df[df['Question'] == matched_question]['Answer'].tolist()
        unique_answers.update(answers)

    if not unique_answers:
        return jsonify({"answer": "No answer found in the dataset."}), 404

    # Randomly pick one answer and corresponding question
    answer = random.choice(list(unique_answers))
    best_match = random.choice(matched_questions)

    # Step 2: Check if tags exist in the response
    # Find tags in the answer text (e.g., <CGPA>, <SEMESTER_NO>)
    tags = re.findall(r'<(.*?)>', answer)

    if not tags:
        return jsonify({
            "query": question,
            "best_matched_question": best_match,
            "answer": answer
        })


    try:
        rules = db.query(KnowledgeBase).all()
        print(rules)
        kb_dict = {rule.Key_Name: {"type": rule.Type, "value": rule.Value, "status": rule.Status} for rule in rules}
    except Exception as e:
        return jsonify({"error": "Failed to fetch knowledge base.", "details": str(e)}), 500
    finally:
        db.close()

    # Step 4: Process tags
    for tag in tags:
        if tag not in kb_dict:
            answer = "No Rule is added or declared for this Category in database"
            continue

        rule = kb_dict[tag]
        rule_type = rule["type"]
        rule_value = rule["value"]
        rule_status = rule["status"]

        if rule_status == 1:
            answer = "The Rule is disabled for this Scheme of Study, No data found against this query"
        elif rule_type == 1 and rule_status == 0:
            answer = answer.replace(f"<{tag}>", rule_value)
        elif rule_type == 2 and rule_status == 0:
            try:
                result_value = run_user_specific_query(rule_value, reg_no, currentsemesterno)
                answer = answer.replace(f"<{tag}>", result_value)

            except ValueError as ve:
                # Agar koi data na mila
                answer = str(ve)
            except Exception as e:
                # Agar koi aur error hua (DB connection, syntax error, etc.)
                answer = answer.replace(f"<{tag}>", f"[Query Error: {e}]")

    db_session = Session()
    try:
        history = ChatHistory(
            REG_NO=reg_no,
            Question=question,
            Answer=answer,
            DateTime=datetime.now()
        )
        db_session.add(history)
        db_session.commit()
        print(f"Chat history saved with ID: {history.ChatId}")
    except Exception as e:
        db_session.rollback()
        print("Error saving chat history:", e)
    finally:
        db_session.close()

   # agr koi tag unresolve ho to
    if "<" in answer and ">" in answer:
        missingTags = re.findall(r'<(.*?)>', answer)
        print("Missing Tags:", missingTags)
        answer = "Sorry, can't answer your query this time."

    # Step 5: Return final answer
    return jsonify({
        "query": question,
        "best_matched_question": best_match,
        "answer": answer
    })

def run_user_specific_query(query, reg_no, currentsemesterno=None):
    query = query.replace("?", f"'{reg_no}'")
    final_query = query.replace("#", f"{currentsemesterno}")
    # print('asfasfafasfasdsfsafafafa1111111111111111111 : ',final_query)
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-8TUN3M3\\SQLEXPRESS;'
        'DATABASE=Course_Advisor_Chatbot_Updated_Database;'
        'UID=sa;PWD=habibfarooq12345;'
    )
    cursor = conn.cursor()
    cursor.execute(final_query)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        raise ValueError(f"Not a single row was found in the database against this query and this Reg No: {reg_no}.")

    # Multiple rows → join all column[0] values
    results = [str(row[0]) for row in rows if row[0] is not None]
    return ", ".join(results)  # Or use '\n'.join() if line-by-line preferred


# ----------------------------   Voice Implementation             ------------------------------------------------------
def save_user_query(file):
    print("Saving user .aac file...")

    try:
        timestamp = datetime.now().strftime("%d%m%H%M%S%f")
        filename = secure_filename(f"{timestamp}.aac")

        if not os.path.exists(UPLOAD_QUERIES_FOLDER):
            os.makedirs(UPLOAD_QUERIES_FOLDER)

        save_path = os.path.join(UPLOAD_QUERIES_FOLDER, filename)
        file.save(save_path)
        print(f"File saved: {save_path}")
        return save_path, timestamp

    except Exception as e:
        print(f"Error saving file: {e}")
        raise



# Function to use Whisper for transcription (no need for opus-to-wav conversion)
def transcribe_by_whisper(aac_file_path):
    """
    Transcribes a .aac audio file to text using Whisper.
    """
    try:
        print(f"🔊 Transcribing: {aac_file_path}")
        result = whisper_model.transcribe(aac_file_path)

        return result["text"]
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return None


def get_answer_from_query(query):
    print(f"Getting best match for: {query}")
    query_embedding = model.encode([query], convert_to_numpy=True)

    k = 5  # You can change this to more or fewer results
    _, indices = index.search(query_embedding, k)

    # Collect unique answers from the top-k matched questions
    unique_answers = set()
    for idx in indices[0]:
        matched_question = question_texts[idx]
        answer_list = df[df['Question'] == matched_question]['Answer'].tolist()
        unique_answers.update(answer_list)

    if not unique_answers:
        return "No answer found in the dataset.", "No label"

    # Randomly select one unique answer
    selected_answer = random.choice(list(unique_answers))
    return selected_answer

def process_tags(answer, chat_id):
    tags = re.findall(r'<(.*?)>', answer)

    # Get knowledge base
    kb_response, status_code = get_all_knowledgebase()
    kb_json = kb_response.get_json()
    kb_data = kb_json.get("data", [])

    # Replace all known tags
    for tag in tags:
        for kb in kb_data:
            if kb["Status"] == 0 and kb["Key_name"] == tag and kb["Type"] == 1:
                answer = answer.replace(f"<{tag}>", kb["Value"])

    # If any tags remain, log them in ErrorHistory
    if "<" in answer and ">" in answer:
        missingTags = re.findall(r'<(.*?)>', answer)
        print("Missing Tags:", missingTags)
        db = Session()
        try:
            for tag in missingTags:
                error = ErrorHistory(ChatId=chat_id, tagName=tag)
                db.add(error)
            db.commit()
        except Exception as e:
            db.rollback()
            print("Error saving to ErrorHistory:", e)
        finally:
            db.close()

        answer = "Sorry, can't answer your query this time."

    return answer


# def process_tags(answer):
#     tags = re.findall(r'<(.*?)>', answer)
#
#     # Get the knowledge base data from the controller response.
#     kb_response, status_code = get_all_knowledgebase()
#     kb_json = kb_response.get_json()  # Extract the JSON payload
#     kb_data = kb_json.get("data", [])
#
#     # Replace each tag with the corresponding value from the knowledge base.
#     for tag in tags:
#         for kb in kb_data:
#             if kb["Status"] == 0 and kb["Key_name"] == tag and kb["Type"] == 1:
#                 answer = answer.replace("<" + tag + ">", kb["Value"])
#     # add to chat history
#    # history = ChatHistory(REG_NO=regNo, Question=query, Answer=best_match, DateTime=datetime.now())
#     #history_id = add_history(history)
#
#     # Now check that all the tags are replaced by the values?
#     if "<" in answer:
#         if ">" in answer:
#             # now log this issue in database for admin to resolve.
#             missingTags = re.findall(r'<(.*?)>', answer)
#             print("Missing Tags:", missingTags)
#             # query logic
#             # for tag in missingTags:
#             for tag in missingTags:
#                 error = ErrorHistory(ChatId=chat_id, tagName=tag)
#                 add_error_history(error)
#
#             answer = "Sorry, can't answer your query this time."
#             return  answer

def generate_tts_and_convert_to_aac(text, timestamp):
    print("Generating TTS and saving as .aac...")
    text = text.replace("%", " percent ")
    text = re.sub(r"[{}<>]", "", text)
    text = html.unescape(text)

    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    engine.setProperty("volume", 1.0)

    for voice in engine.getProperty("voices"):
        if "female" in voice.name.lower() or "zira" in voice.name.lower():
            engine.setProperty("voice", voice.id)
            break

    wav_path = os.path.join(UPLOAD_ANSWERS_FOLDER, f"{timestamp}.wav")
    aac_path = os.path.join(UPLOAD_ANSWERS_FOLDER, f"{timestamp}.aac")

    try:
        engine.save_to_file(text, wav_path)
        engine.runAndWait()
        print("Saved TTS as .wav")

        subprocess.run(["ffmpeg", "-y", "-i", wav_path, "-c:a", "aac", aac_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Converted .wav to .aac")

        os.remove(wav_path)
        return aac_path

    except Exception as e:
        print("TTS generation error:", e)
        raise




def ask_by_voice():
    try:
        # Get the file from the request
        file = request.files.get("file")

        # Validate that it is a .aac file
        if not file or not file.filename.endswith(".aac"):
            return jsonify({"error": "Invalid or missing .aac file"}), 400

        # Save the .aac file
        aac_path, timestamp = save_user_query(file)

        # Transcribe the audio using Whisper
        query = transcribe_by_whisper(aac_path)

        if not query or not query.strip():
            return jsonify({"error": "Empty transcription"}), 400

        # Get the answer
        answer = get_answer_from_query(query)
        #processed_answer = process_tags(answer)

        # Generate TTS and convert to .aac
        answer_audio_path = generate_tts_and_convert_to_aac(answer, timestamp)

        # return jsonify({
        #
        #     "answer_audio": answer_audio_path
        # })


        relative_path = os.path.relpath(answer_audio_path, start='Uploads')
        url = f"http://192.168.18.96:5000/uploads/{relative_path.replace(os.sep, '/')}"
        return jsonify({'answer_audio': url})

    except Exception as e:
        print("Exception occurred:", e)
        return jsonify({"error": str(e)}), 500