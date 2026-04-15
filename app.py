from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

def get_food_info(food_name):
    connection = sqlite3.connect("database/food.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name, calories, carbs, protein, fats
        FROM foods
        WHERE name = ?
    """, (food_name,))

    food = cursor.fetchone()
    connection.close()

    return food

@app.route('/')
def result():
    food = get_food_info("Banana (1 unit)")     # parameter will be replaced later with model output

    return render_template("result_page.html", food = food)

if __name__ == '__main__':
    app.run(debug = True)