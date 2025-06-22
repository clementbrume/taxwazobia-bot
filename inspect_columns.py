import psycopg2

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

    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'usage_metrics';
    """)
    columns = cursor.fetchall()
    print("📋 Columns in 'usage_metrics':")
    for col in columns:
        print(f" - {col[0]} ({col[1]})")

    cursor.close()
    conn.close()

except Exception as e:
    print("❌ Error inspecting table:", e)
