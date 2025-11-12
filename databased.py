print("[DEBUG] Script started...")

import sqlite3
import json
from datetime import datetime

def create_users_db():
    print("[DEBUG] Creating users.db...")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL CHECK(
            LENGTH(password) >= 8 
            AND password GLOB '*[A-Z]*' 
            AND password GLOB '*[a-z]*' 
            AND password GLOB '*[0-9]*' 
            AND password GLOB '*[!@#$%^&*(),.?":{}|<>]*'
        ),
        role TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()
    print("[INFO] users.db created successfully.")

def create_flights_db():
    print("[DEBUG] Creating flights.db...")
    conn = sqlite3.connect("flights.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        notes TEXT NULL,
        route_points TEXT NOT NULL,
        distance REAL NOT NULL,
        duration TEXT NOT NULL,
        video_path TEXT NULL
    )
    """)
    
    conn.commit()
    conn.close()
    print("[INFO] flights.db created successfully.")

if __name__ == "__main__":
    print("[DEBUG] Running main script...")
    create_users_db()
    create_flights_db()
    print("[DEBUG] Script completed successfully.")

'''# Function to insert a user
def insert_user(username, email, password, role):
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)", 
                       (username, email, password, role))
        conn.commit()
        conn.close()
        print(f"[INFO] User '{username}' added successfully.")
    except sqlite3.IntegrityError:
        print("[ERROR] Username or Email already exists!")

# Function to insert a flight
def insert_flight(email, notes, route_points, distance, speed=50):
    conn = sqlite3.connect("flights.db")
    cursor = conn.cursor()

    # Generate a flight name
    timestamp = datetime.now().strftime("%d-%m-%Y-%H.%M.%S")
    flight_name = f"{email}-{timestamp}CET"

    # Convert route points to JSON
    route_points_json = json.dumps(route_points)

    # Calculate duration (HH:MM format)
    duration = f"{int(distance // speed):02}:{int((distance % speed) / speed * 60):02}"

    cursor.execute("INSERT INTO flights (name, notes, route_points, distance, duration) VALUES (?, ?, ?, ?, ?)", 
                   (flight_name, notes, route_points_json, distance, duration))

    conn.commit()
    conn.close()
    print(f"[INFO] Flight '{flight_name}' added successfully.")

# Function to get all users
def get_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

# Function to get all flights
def get_flights():
    conn = sqlite3.connect("flights.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flights")
    flights = cursor.fetchall()
    conn.close()
    return flights

# Main execution
if __name__ == "__main__":
    create_users_db()
    create_flights_db()

    # Insert sample user
    insert_user("john_doe", "john@example.com", "SecureP@ss1!", "admin")

    # Insert sample flight
    sample_route = [
        {"lat": 37.7749, "lon": -122.4194},
        {"lat": 38.5758, "lon": -121.4789},
        {"lat": 39.9042, "lon": 116.4074},
        {"lat": 40.7128, "lon": -74.0060},
        {"lat": 34.0522, "lon": -118.2437}
    ]
    insert_flight("john@example.com", "Test flight", sample_route, 500.0)

    # Retrieve and print users
    print("\n[INFO] Users in database:")
    for user in get_users():
        print(user)

    # Retrieve and print flights
    print("\n[INFO] Flights in database:")
    for flight in get_flights():
        print(flight)
'''