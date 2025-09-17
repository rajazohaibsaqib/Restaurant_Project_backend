import re
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from database.model import RestaurantInfo, MenuItem, Order, OrderItem, Service, Platform, Policy, Facility, Staff

model = SentenceTransformer('all-MiniLM-L6-v2')
question_texts = np.load("model/question_texts.npy", allow_pickle=True)
df = pd.read_csv("model/restaurant_qa.csv")
index = faiss.read_index("model/model.index")

def get_model_response(user_query: str) -> str:
    embedding = model.encode([user_query], convert_to_numpy=True)
    _, indices = index.search(embedding, k=1)
    best_idx = indices[0][0]
    question = question_texts[best_idx]
    answer = df[df['Question'] == question]['Answer'].values[0]
    return answer

def parse_order_query(query: str, db: Session):
    query = query.lower()
    menu_items = db.query(MenuItem).all()
    item_map = {item.name.lower(): item for item in menu_items}

    valid_items = []
    missing_items = []

    # All known menu item names
    all_item_names = list(item_map.keys())

    # Words that are not food items
    STOPWORDS = {
        'i', 'want', 'please', 'order', 'buy', 'can', 'could', 'me', 'to', 'give', 'get',
        'need', 'would', 'like', 'have', 'some', 'with', 'without', 'and', 'a', 'an', 'just'
    }

    # Extract phrases like "2 greek salad", "1 tea"
    order_phrases = re.findall(r"(\d+)?\s*([a-zA-Z ]+)", query)

    already_added = set()

    for quantity_str, raw_item_name in order_phrases:
        item_name = raw_item_name.strip().lower()

        # Remove stopwords from the phrase
        filtered_words = [word for word in item_name.split() if word not in STOPWORDS]
        if not filtered_words:
            continue

        cleaned_item_name = ' '.join(filtered_words)
        quantity = int(quantity_str) if quantity_str else 1

        matched = None
        for name in all_item_names:
            if name in cleaned_item_name and name not in already_added:
                matched = name
                break

        if matched:
            item = item_map[matched]
            valid_items.append({
                "menu_item_id": item.id,
                "name": item.name,
                "quantity": quantity,
                "price_per_unit": item.price,
            })
            already_added.add(matched)
        else:
            # Avoid phrases like "give me", "get 1"
            if cleaned_item_name not in already_added and len(cleaned_item_name) > 2:
                missing_items.append(cleaned_item_name)
                already_added.add(cleaned_item_name)

    return valid_items, missing_items

def create_order(user_id: int, items: list, db: Session) -> float:
    total = sum([item['quantity'] * item['price_per_unit'] for item in items])
    order = Order(user_id=user_id, total_amount=total, payment_method="cash", delivery_address="", special_instructions="")
    db.add(order)
    db.flush()

    for item in items:
        db.add(OrderItem(
            order_id=order.id,
            menu_item_id=item["menu_item_id"],
            quantity=item["quantity"],
            price_per_unit=item["price_per_unit"],
            customization=""
        ))
    db.commit()
    return total

def replace_tags_with_db_data(response: str, user_id: int, db: Session) -> str:
    def tag_replacer(tag: str) -> str:
        if tag == "menuitem":
            items = db.query(MenuItem).all()
            return "\n".join([f"🍽 {item.name} - Rs {item.price}" for item in items]) or "No menu items available."
        elif tag == "location":
            info = db.query(RestaurantInfo).first()
            return f"📍 {info.name}, {info.address}" if info else "Location not found."
        elif tag == "bill":
            order = db.query(Order).filter_by(user_id=user_id).order_by(Order.id.desc()).first()
            return f"🧾 Your total bill is Rs {order.total_amount}" if order else "No bill found."
        elif tag == "contact":
            info = db.query(RestaurantInfo).first()
            return f"📞 {info.contact}" if info else "Contact info not available."
        elif tag == "email":
            info = db.query(RestaurantInfo).first()
            return f"📧 {info.email}" if info else "Email not available."
        elif tag == "name":
            info = db.query(RestaurantInfo).first()
            return info.name if info else "Name not available."
        elif tag == "wifi":
            info = db.query(RestaurantInfo).first()
            return "✅ Available" if info and info.wifi else "❌ Not Available"
        elif tag == "parking":
            info = db.query(RestaurantInfo).first()
            return "✅ Available" if info and info.parking else "❌ Not Available"
        elif tag == "service":
            services = db.query(Service).filter_by(enabled=True).all()
            return ", ".join([s.name.capitalize() for s in services]) or "No active services."
        elif tag == "platform":
            platforms = db.query(Platform).filter_by(available=True).all()
            return ", ".join([p.name for p in platforms]) or "No available platforms."
        elif tag == "policy":
            policies = db.query(Policy).all()
            return "\n".join([f"{p.name.replace('_',' ').title()}: {p.value}" for p in policies]) or "No policies available."
        elif tag == "staff":
            staff = db.query(Staff).all()
            return "\n".join([f"{s.role.title()}: {s.name}" for s in staff]) or "No staff listed."
        elif tag == "amount":
            order = db.query(Order).filter_by(user_id=user_id).order_by(Order.id.desc()).first()
            return f"Rs {order.total_amount}" if order else "Amount not found."
        return f"<{tag}>"

    tags_found = re.findall(r"<(.*?)>", response)
    for tag in tags_found:
        value = tag_replacer(tag)
        response = response.replace(f"<{tag}>", value)
    return response

def is_order_query(text: str) -> bool:
    order_keywords = ["order", "want", "buy", "get", "give me", "need", "i'll take", "can i have", "send", "serve"]
    return any(keyword in text.lower() for keyword in order_keywords)

def get_final_chat_response(query: str, user_id: int, db: Session) -> str:
    if is_order_query(query):
        valid_items, missing_items = parse_order_query(query, db)

        if valid_items and not missing_items:
            total = create_order(user_id, valid_items, db)
            items_text = "\n".join([f"✅ {item['quantity']} x {item['name']} (Rs {item['price_per_unit']})" for item in valid_items])
            return f"🛒 Order placed successfully:\n{items_text}\n\n🧾 Total Bill: Rs {total:.2f}"

        elif valid_items and missing_items:
            total = create_order(user_id, valid_items, db)
            items_text = "\n".join([f"✅ {item['quantity']} x {item['name']} (Rs {item['price_per_unit']})" for item in valid_items])
            missing_text = ", ".join(missing_items)
            return (
                f"🛒 Partial order placed:\n{items_text}\n\n🧾 Total Bill: Rs {total:.2f}\n\n"
                f"❌ Sorry, we couldn't find: {missing_text} in our menu."
            )

        elif not valid_items and missing_items:
            missing_text = ", ".join(missing_items)
            return f"❌ Sorry, none of the items you requested are available in our menu.\nUnavailable items: {missing_text}."

        else:
            return "❓ Sorry, I couldn't understand your order. Could you please rephrase?"

    raw_response = get_model_response(query)
    return replace_tags_with_db_data(raw_response, user_id, db)


