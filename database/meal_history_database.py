import sqlite3

connection = sqlite3.connect("meal_history.db")

connection.execute("PRAGMA foreign_keys = ON")

cursor = connection.cursor()

create_table_query = """CREATE TABLE IF NOT EXISTS meal_history(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        food_name TEXT,
                        calories REAL,
                        carbs REAL,
                        protein REAL,
                        fats REAL,
                        servings INTEGER,
                        date TEXT)"""

cursor.execute(create_table_query)

connection.commit()

connection.close()