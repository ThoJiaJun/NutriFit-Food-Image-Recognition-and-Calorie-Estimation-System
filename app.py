from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3

app = Flask(__name__)

# Result Page Logic
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

@app.route("/result")
def result():
    food = get_food_info("Banana (1 unit)")     # parameter will be replaced later with model output

    return render_template("result_page.html", food = food)

# History Page Logic
@app.route("/history")
def history():
    return render_template("history_page.html")

@app.route("/save_meal", methods = ["POST"])
def save_meal():
    data = request.get_json()
    today = datetime.now().strftime("%Y-%m-%d")
    
    connection = sqlite3.connect("database/meal_history.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO meal_history(user_id, food_name, calories, carbs, protein, fats, servings, date)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)""", 
        (1, data["food_name"], data["calories"], data["carbs"], data["protein"], data["fats"], data["servings"], today))

    connection.commit()

    connection.close()

    return jsonify({"message": "Meal saved successfully!"})

@app.route("/get_meals")
def get_meals():
    history_tab = request.args.get("type")
    date = request.args.get("date")

    connection = sqlite3.connect("database/meal_history.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    if history_tab == "daily":
        cursor.execute("""
            SELECT food_name, calories, carbs, protein, fats, servings
            FROM meal_history
            WHERE date = ?
        """, (date,))

        rows = cursor.fetchall()

        data = []
        for r in rows:
            data.append({
                "food_name": r["food_name"],
                "calories": r["calories"],
                "carbs": r["carbs"],
                "protein": r["protein"],
                "fats": r["fats"],
                "servings": r["servings"]
            })

        connection.close()
        return jsonify(data)
    elif history_tab == "weekly":
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.isocalendar()[0]
        week = date_obj.isocalendar()[1]

        return jsonify({
            "year": year,
            "week": week,
        })
    
    connection.close()
    return jsonify([])

if __name__ == '__main__':
    app.run(debug = True)