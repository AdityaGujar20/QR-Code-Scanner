import qrcode
import psycopg2
from psycopg2 import sql
import os

# Database configuration
DB_NAME = "qr_data"
DB_USER = "qr_data_user"
DB_PASSWORD = "XLR4DyJQ44o7k5GctdUmWMcjAzjmZysW"
DB_HOST = "dpg-cum7dfhu0jms73bl29c0-a.singapore-postgres.render.com"
DB_PORT = "5432"

# Directory to save QR codes
QR_DIR = "../data/qr_codes"
os.makedirs(QR_DIR, exist_ok=True)

# Connect to PostgreSQL
def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )

# Create table if not exists
def create_table():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (
            qr_id SERIAL PRIMARY KEY,
            qr_code TEXT UNIQUE,
            status TEXT DEFAULT 'Not Scanned'
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# Generate QR codes and save them
def generate_qr_codes(n=10):
    conn = connect_db()
    cur = conn.cursor()
    
    for i in range(1, n + 1):
        qr_data = f"QR{i}"
        qr = qrcode.make(qr_data)
        file_path = os.path.join(QR_DIR, f"{qr_data}.png")
        qr.save(file_path)
        
        # Insert QR code data into database
        cur.execute("INSERT INTO qr_codes (qr_code) VALUES (%s) ON CONFLICT (qr_code) DO NOTHING", (qr_data,))
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"Generated {n} QR codes and stored them in the database.")

if __name__ == "__main__":
    create_table()
    generate_qr_codes()
