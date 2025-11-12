import sqlite3

def select_all_flights(db_file='flights.db'):
    """
    Query all rows in the flights table
    :param db_file: database file path
    :return: list of tuples representing all flight records
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_file)
        
        # Create a cursor object
        cur = conn.cursor()
        
        # Execute the query to select all records
        cur.execute("SELECT * FROM flights")
        
        # Fetch all rows
        rows = cur.fetchall()
        
        # Print column names (optional)
        column_names = [description[0] for description in cur.description]
        print("Column names:", column_names)
        
        # Print all rows
        for row in rows:
            print(row)
            
        return rows
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Exception in _query: {e}")
    finally:
        # Close the connection
        if conn:
            conn.close()

# Call the function
all_flights = select_all_flights()

# If you want to work with the data, it's now in the all_flights variable
print(f"\nTotal records retrieved: {len(all_flights)}")