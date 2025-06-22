import psycopg2
import os

# Environment-safe way (if .env is loaded), or use actual string values
DB_NAME = "taxwazobia_db"
DB_USER = "taxwazobia_db_user"
DB_PASSWORD = "Aecev0c6mWOhxrSqwISXqpRWmhi26ZLX"
DB_HOST = "dpg-d1blorre5dus73eoe5eg-a.frankfurt-postgres.render.com"
DB_PORT = "5432"

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        sslmode="require"
    )
    cursor = conn.cursor()

    print("✅ Connected to DB.")

    # Check if table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'usage_metrics'
        );
    """)
    exists = cursor.fetchone()[0]
    print(f"🗃 Table 'usage_metrics' exists: {exists}")

    if exists:
        cursor.execute("SELECT user_count, error_count FROM usage_metrics LIMIT 1;")
        row = cursor.fetchone()
        if row:
            print(f"👥 User Count: {row[0]}")
            print(f"⚠️ Error Count: {row[1]}")
        else:
            print("⚠️ Table exists but has no data.")
    else:
        print("❌ Table 'usage_metrics' does not exist.")

    cursor.close()
    conn.close()

except Exception as e:
    print("❌ Database error:", e)
