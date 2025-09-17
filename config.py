from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Replace with your actual credentials
USERNAME = "root"
PASSWORD = "abc%40123"
HOST = "localhost"
PORT = "3306"
DATABASE = "restaurant_db"

SQLALCHEMY_DATABASE_URL = f"mysql+mysqlconnector://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
