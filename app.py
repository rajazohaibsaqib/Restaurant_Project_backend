import datetime
from flask import Flask, request, jsonify
from sqlalchemy import func
from Resturant_Project.config import SessionLocal
from database.model import User, MenuItem, Order, OrderItem, ChatHistory, RestaurantInfo
from sqlalchemy.exc import SQLAlchemyError
from tag_model_handler import get_final_chat_response

app = Flask(__name__)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------- CHAT API --------
@app.route("/chat", methods=["POST"])
def handle_chat():
    data = request.get_json()
    user_id = data.get("user_id")
    question = data.get("message")

    if not user_id or not question:
        return jsonify({"error": "user_id and message are required"}), 400

    db = SessionLocal()
    try:
        # Generate answer using the tag-based model
        answer = get_final_chat_response(question, user_id, db)

        # Store in database (without session ID)
        chat_entry = ChatHistory(
            user_id=user_id,
            question=question,
            answer=answer,
            timestamp=datetime.datetime.now()
        )
        db.add(chat_entry)
        db.commit()

        return jsonify({
            "response": answer
        })

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ------------------------------
# Basic Routes
# ------------------------------
@app.route("/")
def root():
    return {"message": "🍽️ Restaurant Chatbot API is running."}

# ------------------------------
# Create a new user
# ------------------------------
@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    db = next(get_db())
    try:
        existing_user = db.query(User).filter(
            (User.contact == data["contact"]) | (User.email == data["email"])
        ).first()

        if existing_user:
            return jsonify({
                "message": "User already exists",
                "user_id": existing_user.id
            }), 200

        user = User(name=data["name"], contact=data["contact"], email=data["email"])
        db.add(user)
        db.commit()
        db.refresh(user)
        return jsonify({
            "message": "User created",
            "user_id": user.id
        }), 201

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

# ------------------------------
# Get All Menu Items
# ------------------------------
@app.route("/menu", methods=["GET"])
def get_menu():
    db = next(get_db())
    items = db.query(MenuItem).all()
    result = [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "category": item.category,
            "price": item.price,
        }
        for item in items
    ]
    return jsonify(result)

# ------------------------------
# Place Order
# ------------------------------
@app.route("/order", methods=["POST"])
def place_order():
    data = request.get_json()
    db = next(get_db())
    try:
        order = Order(
            user_id=data["user_id"],
            total_amount=data["total_amount"],
            payment_method=data.get("payment_method"),
            delivery_address=data.get("delivery_address"),
            special_instructions=data.get("special_instructions", ""),
        )
        db.add(order)
        db.flush()

        for item in data["items"]:
            db.add(OrderItem(
                order_id=order.id,
                menu_item_id=item["menu_item_id"],
                quantity=item["quantity"],
                price_per_unit=item["price_per_unit"],
                customization=item.get("customization", "")
            ))

        db.commit()
        return jsonify({"message": "Order placed", "order_id": order.id}), 201
    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

# ------------------------------
# Get Full Chat History (no session)
# ------------------------------
@app.route("/chat_history/<int:user_id>", methods=["GET"])
def get_full_chat_history(user_id):
    db = SessionLocal()
    try:
        history = db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id
        ).order_by(ChatHistory.timestamp.asc()).all()

        response = []
        for chat in history:
            response.append({
                "sender": "user",
                "text": chat.question,
                "timestamp": chat.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
            response.append({
                "sender": "bot",
                "text": chat.answer,
                "timestamp": chat.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ------------------------------
# Get Restaurant Info
# ------------------------------
@app.route("/restaurant/info", methods=["GET"])
def get_restaurant_info():
    db = next(get_db())
    info = db.query(RestaurantInfo).first()
    if info:
        return jsonify({
            "name": info.name,
            "address": info.address,
            "contact": info.contact,
            "email": info.email,
            "wifi": info.wifi,
            "parking": info.parking,
            "opening_hours": info.opening_hours,
            "closing_time": info.closing_time,
            "weekend_hours": info.weekend_hours,
            "delivery_time": info.delivery_time,
            "capacity": info.capacity,
        })
    return jsonify({"message": "No restaurant info found"}), 404
@app.route("/order_history/<int:user_id>", methods=["GET"])
def get_order_history(user_id):
    db = SessionLocal()
    try:
        orders = db.query(Order).filter(Order.user_id == user_id).order_by(Order.id.desc()).all()

        history = []
        for order in orders:
            items = []
            for item in order.items:
                items.append({
                    "item_name": item.menu_item.name if item.menu_item else "Unknown",
                    "quantity": item.quantity,
                    "price_per_unit": item.price_per_unit,
                    "customization": item.customization
                })

            history.append({
                "order_id": order.id,
                "total_amount": order.total_amount,
                "payment_method": order.payment_method,
                "delivery_address": order.delivery_address,
                "special_instructions": order.special_instructions,
                "timestamp": order.order_time.strftime("%Y-%m-%d %H:%M:%S"),
                "items": items
            })

        return jsonify(history), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ------------------------------
# Run the app
# ------------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=True)
