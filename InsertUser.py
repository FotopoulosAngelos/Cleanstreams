import sqlite3

def insert_new_user(username, email, password, role):
    # Connect to the users database
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO users (username, email, password, role)
        VALUES (?, ?, ?, ?)
        """, (username, email, password, role))

        # Commit the transaction
        conn.commit()
        print("[INFO] User added successfully!")

    except sqlite3.IntegrityError:
        print("[ERROR] Username or email already exists.")
    
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

    finally:
        # Close the connection
        conn.close()

# Insert 'angelostest1' user
insert_new_user('angelostest1', 'angelostest1@gmail.com', 'aq12!@AQ', 'operator')
