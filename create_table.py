import psycopg2

# PostgreSQL connection credentials from Render
DB_NAME = "taxwazobia_db"
DB_USER = "taxwazobia_db_user"
DB_PASSWORD = "Aecev0c6mWOhxrSqwISXqpRWmhi26ZLX"
DB_HOST = "dpg-d1blorre5dus73eoe5eg-a.frankfurt-postgres.render.com"
DB_PORT = "5432"

# SQL command to create the usage_metrics table
create_table_sql = """
CREATE TABLE IF NOT EXISTS usage_metrics (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT UNIQUE,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_count INT DEFAULT 0
);
"""

try:
    connection = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        sslmode="require"
    )
    cursor = connection.cursor()
    cursor.execute(create_table_sql)
    connection.commit()

    print("✅ Table 'usage_metrics' created successfully.")
    cursor.close()
    connection.close()

except Exception as e:
    print("❌ Failed to create table:", e)
