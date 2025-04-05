from app import app, db
from sqlalchemy import text

def update_database_schema():
    with app.app_context():
        print("Checking for and adding missing columns...")
        
        # Check if phone_number column exists in users table
        with db.engine.connect() as connection:
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='phone_number';
            """))
            if result.fetchone() is None:
                print("Adding phone_number column to users table...")
                connection.execute(text("""
                    ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);
                """))
                print("phone_number column added successfully!")
            else:
                print("phone_number column already exists.")
            
            # Commit the transaction
            connection.commit()
        
        print("Database schema update completed!")

if __name__ == "__main__":
    update_database_schema()