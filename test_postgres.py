import psycopg2
import os

# Replace with your actual Render PostgreSQL credentials
DB_NAME = "taxwazobia_db"
DB_USER = "taxwazobia_db_user"
DB_PASSWORD = "Aecev0c6mWOhxrSqwISXqpRWmhi26ZLX"
DB_HOST = "dpg-d1blorre5dus73eoe5eg-a.frankfurt-postgres.render.com"
DB_PORT = "5432"  # Always 5432 for Render

try:
    connection = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        sslmode="require"  # SSL is required by Render
    )

    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print("✅ Connected to PostgreSQL! Version:", db_version)

    cursor.close()
    connection.close()

except Exception as e:
    print("❌ Connection failed:", e)