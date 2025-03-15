import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv("PGDATABASE", "love_alarm_db"),  
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "3e0o7432a46b"),
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        cursor_factory=RealDictCursor
    )
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Создание таблицы users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            name VARCHAR(50) NOT NULL,
            surname VARCHAR(50) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            profile_photo VARCHAR(255),
            latitude FLOAT,  -- Широта
            longitude FLOAT, -- Долгота
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Создание таблицы interactions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            target_id INT NOT NULL,
            interaction_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (target_id) REFERENCES users(id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id SERIAL PRIMARY KEY,
            from_user_id INT REFERENCES users(id),
            to_user_id INT REFERENCES users(id),
            UNIQUE (from_user_id, to_user_id)
        );
    """)

    # Добавим поле signal_active, если его нет
    cur.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS signal_active BOOLEAN DEFAULT FALSE;
    """)

    conn.commit()
    cur.close()
    conn.close()

