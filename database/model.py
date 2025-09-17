from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# --- USER MANAGEMENT ---
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    contact = Column(String(20), unique=True)  # Phone number
    email = Column(String(100), unique=True)
    join_date = Column(DateTime, default=func.now())

    # Relationship to orders
    orders = relationship("Order", back_populates="user")


# --- CORE INFO ---
class RestaurantInfo(Base):
    __tablename__ = 'restaurant_info'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    address = Column(String(200))
    contact = Column(String(100))
    email = Column(String(100))
    wifi = Column(Boolean)
    parking = Column(Boolean)
    opening_hours = Column(String(100))
    closing_time = Column(String(100))
    weekend_hours = Column(String(100))
    delivery_time = Column(String(100))
    capacity = Column(Integer)


# --- MENU ---
class MenuItem(Base):
    __tablename__ = 'menu_item'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(Text)
    category = Column(String(100))  # e.g., drinks, desserts, etc.
    price = Column(Float)
    is_vegan = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    is_vegetarian = Column(Boolean, default=False)
    is_chef_special = Column(Boolean, default=False)


# --- ORDERING SYSTEM ---
class Order(Base):
    __tablename__ = 'order'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))  # Linked to user
    status = Column(String(50), default="Pending")  # Paid, Unpaid, Cancelled
    order_time = Column(DateTime, default=func.now())
    total_amount = Column(Float)
    payment_method = Column(String(50))  # credit_card, cash, etc.
    delivery_address = Column(Text)  # For delivery orders
    special_instructions = Column(Text)

    # Relationships
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = 'order_item'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('order.id'))
    menu_item_id = Column(Integer, ForeignKey('menu_item.id'))
    quantity = Column(Integer, default=1)
    price_per_unit = Column(Float)
    customization = Column(Text)  # For special requests

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")


# --- PAYMENT SYSTEM ---
class Payment(Base):
    __tablename__ = 'payment'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('order.id'))
    amount = Column(Float)
    payment_date = Column(DateTime, default=func.now())
    transaction_id = Column(String(100))
    status = Column(String(50))  # Success, Failed, Refunded

    order = relationship("Order")


# --- SUPPORTING TABLES ---
class Facility(Base):
    __tablename__ = 'facility'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)  # e.g., wheelchair_access
    available = Column(Boolean)


class Policy(Base):
    __tablename__ = 'policy'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)  # e.g., halal_certified, dress_code
    value = Column(String(200))  # e.g., Yes / No / Formal Only


class Service(Base):
    __tablename__ = 'service'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)  # e.g., delivery, dine-in
    enabled = Column(Boolean)


class Platform(Base):
    __tablename__ = 'platform'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)  # e.g., foodpanda, ubereats
    available = Column(Boolean)


class Staff(Base):
    __tablename__ = 'staff'
    id = Column(Integer, primary_key=True)
    role = Column(String(100))  # e.g., manager, receptionist
    name = Column(String(100))


# --- CHAT HISTORY ---
class ChatHistory(Base):
    __tablename__ = 'chat_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    question = Column(Text)
    answer = Column(Text)
    timestamp = Column(DateTime, default=func.now())

    user = relationship("User")