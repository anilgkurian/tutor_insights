
from src.database import engine
from src.models import Base
from sqlalchemy import text

def drop_table():
    with engine.connect() as conn:
        print("Dropping questions_asked_weekly table...")
        conn.execute(text("DROP TABLE IF EXISTS questions_asked_weekly"))
        conn.commit()
        print("Table dropped.")

if __name__ == "__main__":
    drop_table()
