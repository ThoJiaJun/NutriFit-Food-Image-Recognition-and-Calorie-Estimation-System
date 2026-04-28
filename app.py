from flask import Flask, render_template, request, jsonify
from datetime import datetime
import calendar
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
            SELECT id, food_name, calories, carbs, protein, fats, servings
            FROM meal_history
            WHERE date = ?
        """, (date,))

        rows = cursor.fetchall()

        data = []
        for r in rows:
            data.append({
                "id": r["id"],
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

        cursor.execute("""
            SELECT date, id, food_name, calories, carbs, protein, fats, servings
            FROM meal_history
            WHERE strftime('%Y', date) = ?
            AND strftime('%W', date) = ?
            ORDER BY date
        """, (str(year), f"{week - 1:02d}"))

        rows = cursor.fetchall()

        grouped = {}
        total_week_kcal = 0
        total_carbs = 0
        total_protein = 0
        total_fats = 0

        for r in rows:
            d = r["date"]

            if d not in grouped:
                grouped[d] = {
                    "meals": [],
                    "total": 0
                }

            grouped[d]["meals"].append({
                "food_name": r["food_name"],
                "calories": r["calories"]
            })

            grouped[d]["total"] += r["calories"]

            total_week_kcal += r["calories"]
            total_carbs += r["carbs"]
            total_protein += r["protein"]
            total_fats += r["fats"]

        connection.close()
        return jsonify({
            "year": year,
            "week": week,
            "total_kcal": total_week_kcal,
            "total_carbs": round(total_carbs, 2),
            "total_protein": round(total_protein, 2),
            "total_fats": round(total_fats, 2),
            "days": grouped
        })
    elif history_tab == "monthly":
        year, month = date.split("-")

        cursor.execute("""
            SELECT date, calories, carbs, protein, fats
            FROM meal_history
            WHERE strftime('%Y', date) = ?
            AND strftime('%m', date) = ?
        """, (year, month))

        rows = cursor.fetchall()

        weekly = {}
        total_month_kcal = 0
        total_carbs = 0
        total_protein = 0
        total_fats = 0

        month_start = datetime(int(year), int(month), 1)
        month_end = datetime(int(year), int(month), calendar.monthrange(int(year), int(month))[1])

        for r in rows:
            date_obj = datetime.strptime(r["date"], "%Y-%m-%d")
            year = date_obj.isocalendar()[0]
            week = date_obj.isocalendar()[1]

            week_start = datetime.fromisocalendar(year, week, 1)
            week_end = datetime.fromisocalendar(year, week, 7)

            range_start = max(week_start, month_start)
            range_end = min(week_end, month_end)

            if week not in weekly:
                weekly[week] = {
                    "calories": 0,
                    "carbs": 0,
                    "protein": 0,
                    "fats": 0,
                    "start_date": range_start.strftime("%Y-%m-%d"),
                    "end_date": range_end.strftime("%Y-%m-%d")
                }

            weekly[week]["calories"] += r["calories"]
            weekly[week]["carbs"] += r["carbs"]
            weekly[week]["protein"] += r["protein"]
            weekly[week]["fats"] += r["fats"]

            total_month_kcal += r["calories"]
            total_carbs += r["carbs"]
            total_protein += r["protein"]
            total_fats += r["fats"]

        connection.close()
        return jsonify({
            "total_kcal": total_month_kcal,
            "total_carbs": round(total_carbs, 2),
            "total_protein": round(total_protein, 2),
            "total_fats": round(total_fats, 2),
            "weeks": weekly
        })
    
    connection.close()
    return jsonify([])

@app.route("/delete_meal", methods = ["POST"])
def delete_meal():
    data = request.get_json()

    connection = sqlite3.connect("database/meal_history.db")
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM meal_history
        WHERE id = ?
    """, (data["id"],))

    connection.commit()
    connection.close()

    return jsonify({"message": "Meal deleted successfully!"})

if __name__ == '__main__':
    app.run(debug = True)