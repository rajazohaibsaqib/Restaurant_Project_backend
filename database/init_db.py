from model import Base
from Resturant_Project.config import engine

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created.")

if __name__ == "__main__":
    create_tables()
