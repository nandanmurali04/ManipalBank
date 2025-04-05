from app import app, db
from sqlalchemy import text

def check_tables():
    with app.app_context():
        with db.engine.connect() as connection:
            tables = ['payees', 'scheduled_payments', 'international_transfers']
            existing_tables = []
            missing_tables = []
            
            print("Checking for tables...")
            for table in tables:
                result = connection.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    );
                """))
                if result.fetchone()[0]:
                    existing_tables.append(table)
                else:
                    missing_tables.append(table)
            
            if existing_tables:
                print(f"Existing tables: {', '.join(existing_tables)}")
            if missing_tables:
                print(f"Missing tables: {', '.join(missing_tables)}")

if __name__ == "__main__":
    check_tables()
