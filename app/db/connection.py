import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URI = os.getenv("DATABASE_URI")
test = os.getenv("test")

print(DATABASE_URI)

def get_db():
    try:
        conn = psycopg2.connect(DATABASE_URI)
        return conn
    except Exception as e:
        print("Database connection error:", e)
        raise
