from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone
import calendar
import sqlite3
import os
import requests

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-here-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    height = db.Column(db.Float, default=0)
    weight = db.Column(db.Float, default=0)
    age = db.Column(db.Integer, default=0)
    gender = db.Column(db.String(10), default='')
    activity_level = db.Column(db.String(20), default='moderate')
    goal = db.Column(db.String(20), default='maintain')
    favorite_color = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()
    print("Database tables created successfully.")

####################
# Login Page Logic #
####################
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id

            if not user.age or not user.gender or not user.activity_level or not user.goal:
                flash('Welcome to NutriFit! Please complete your profile to get started.', 'success')
                return redirect(url_for('profile'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'danger')
    
    return render_template('login_page.html')

#######################
# Register Page Logic #
#######################
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        favorite_color = request.form['favorite_color']

        if password != confirm:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))
        
        user = User(name=name, email=email, favorite_color=favorite_color)
        user.set_password(password) 
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register_page.html')

############################################
# Forgot Password and Reset Password Logic #
############################################
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        favorite_color = request.form['favorite_color']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.favorite_color == favorite_color:
            flash('Color verified! Please set your new password.', 'success')
            return redirect(url_for('reset_password', email=email))
        else:
            flash('Invalid email or color!', 'danger')
    
    return render_template('forgot_password.html')

@app.route('/reset_password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm = request.form['confirm_password']
        
        if new_password != confirm:
            flash('Passwords do not match!', 'danger')
        else:
            user = User.query.filter_by(email=email).first()
            user.set_password(new_password)
            db.session.commit()
            flash('Password reset successful! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('reset_password.html', email=email)

###################
# Dashboard Logic #
################### 
def get_daily_calorie_goal(user):
    
    # MAP Gender
    if user.gender == "male":
        gender = "male"
    elif user.gender == "female":
        gender = "female"

    # MAP Age Group
    if 13 <= user.age <= 17:
        age_group = "13-17"
    elif 18 <= user.age <= 30:
        age_group = "18-30"
    elif 31 <= user.age <= 50:
        age_group = "31-50"
    elif 51 <= user.age <= 70:
        age_group = "51-70"
    elif user.age > 70:
        age_group = ">70"
    
    # MAP Activity Level
    if user.activity_level == "sedentary":
        activity = "sedentary"
    elif user.activity_level == "light":
        activity = "lightly active"
    elif user.activity_level == "moderate":
        activity = "moderately active"
    elif user.activity_level == "active":
        activity = "very active"
    
    # MAP Goal
    if user.goal == "lose":
        goal = "lose weight"
    if user.goal == "maintain":
        goal = "maintain weight"
    if user.goal == "gain":
        goal = "gain muscle"
    
    # Recommended daily calorie intake for users in different situations
    calorie_matrix = {
        "male": {
            "13-17": {
                "sedentary": {"lose weight": 1900, "maintain weight": 2000, "gain muscle": 2300},
                "lightly active": {"lose weight": 1900, "maintain weight": 2200, "gain muscle": 2500},
                "moderately active": {"lose weight": 1900, "maintain weight": 2400, "gain muscle": 2700},
                "very active": {"lose weight": 2300, "maintain weight": 2800, "gain muscle": 3100}
            },
            "18-30": {
                "sedentary": {"lose weight": 1900, "maintain weight": 2400, "gain muscle": 2700},
                "lightly active": {"lose weight": 2000, "maintain weight": 2500, "gain muscle": 2800},
                "moderately active": {"lose weight": 2100, "maintain weight": 2600, "gain muscle": 2900},
                "very active": {"lose weight": 2500, "maintain weight": 3000, "gain muscle": 3300}
            },
            "31-50": {
                "sedentary": {"lose weight": 1700, "maintain weight": 2200, "gain muscle": 2500},
                "lightly active": {"lose weight": 1800, "maintain weight": 2300, "gain muscle": 2600},
                "moderately active": {"lose weight": 1900, "maintain weight": 2400, "gain muscle": 2700},
                "very active": {"lose weight": 2300, "maintain weight": 2800, "gain muscle": 3100}
            },
            "51-70": {
                "sedentary": {"lose weight": 1500, "maintain weight": 2000, "gain muscle": 2300},
                "lightly active": {"lose weight": 1600, "maintain weight": 2100, "gain muscle": 2400},
                "moderately active": {"lose weight": 1700, "maintain weight": 2200, "gain muscle": 2500},
                "very active": {"lose weight": 2100, "maintain weight": 2600, "gain muscle": 2900}
            },
            ">70": {
                "sedentary": {"lose weight": 1300, "maintain weight": 1800, "gain muscle": 2100},
                "lightly active": {"lose weight": 1400, "maintain weight": 1900, "gain muscle": 2200},
                "moderately active": {"lose weight": 1500, "maintain weight": 2000, "gain muscle": 2300},
                "very active": {"lose weight": 1700, "maintain weight": 2200, "gain muscle": 2500}
            }
        },
        "female": {
            "13-17": {
                "sedentary": {"lose weight": 1500, "maintain weight": 1600, "gain muscle": 2100},
                "lightly active": {"lose weight": 1500, "maintain weight": 1700, "gain muscle": 2200},
                "moderately active": {"lose weight": 1500, "maintain weight": 1800, "gain muscle": 2300},
                "very active": {"lose weight": 1900, "maintain weight": 2200, "gain muscle": 2700}
            },
            "18-30": {
                "sedentary": {"lose weight": 1300, "maintain weight": 1800, "gain muscle": 2100},
                "lightly active": {"lose weight": 1400, "maintain weight": 1900, "gain muscle": 2200},
                "moderately active": {"lose weight": 1500, "maintain weight": 2000, "gain muscle": 2300},
                "very active": {"lose weight": 1900, "maintain weight": 2400, "gain muscle": 2700}
            },
            "31-50": {
                "sedentary": {"lose weight": 1300, "maintain weight": 1800, "gain muscle": 2100},
                "lightly active": {"lose weight": 1400, "maintain weight": 1900, "gain muscle": 2200},
                "moderately active": {"lose weight": 1500, "maintain weight": 2000, "gain muscle": 2300},
                "very active": {"lose weight": 1700, "maintain weight": 2200, "gain muscle": 2500}
            },
            "51-70": {
                "sedentary": {"lose weight": 1100, "maintain weight": 1600, "gain muscle": 1900},
                "lightly active": {"lose weight": 1200, "maintain weight": 1700, "gain muscle": 2000},
                "moderately active": {"lose weight": 1300, "maintain weight": 1800, "gain muscle": 2100},
                "very active": {"lose weight": 1500, "maintain weight": 2000, "gain muscle": 2300}
            },
            ">70": {
                "sedentary": {"lose weight": 1100, "maintain weight": 1600, "gain muscle": 1900},
                "lightly active": {"lose weight": 1200, "maintain weight": 1600, "gain muscle": 1900},
                "moderately active": {"lose weight": 1300, "maintain weight": 1700, "gain muscle": 2000},
                "very active": {"lose weight": 1400, "maintain weight": 1800, "gain muscle": 2100}
            }
        }
    }

    return calorie_matrix[gender][age_group][activity][goal]

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get_or_404(session['user_id'])

    if not user.age or not user.gender or not user.activity_level or not user.goal:
        flash('Please fill out your personal info to view your dashboard.', 'danger')
        return redirect(url_for('profile'))
    
    daily_goal = get_daily_calorie_goal(user)
    
    today = datetime.now().strftime("%Y-%m-%d")
    current_calories = 0

    connection = sqlite3.connect("database/meal_history.db")
    cursor = connection.cursor()

    # SUM up all calories consumed by user today
    cursor.execute("""
        SELECT SUM(calories) 
        FROM meal_history 
        WHERE user_id = ? AND date = ?
    """, (session["user_id"], today))

    result = cursor.fetchone()
    if result and result[0] is not None:
        current_calories = int(result[0])
    
    connection.close()

    return render_template('dashboard.html', user = user, daily_goal = daily_goal, current_calories = current_calories)

################
# Logout Logic #
################
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

######################
# Profile Page Logic #
######################
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get_or_404(session['user_id'])

    if request.method == 'POST':
        user.name = request.form['name']
        user.height = float(request.form.get('height', 0))
        user.weight = float(request.form.get('weight', 0))
        user.age = int(request.form.get('age', 0))
        user.gender = request.form.get('gender', '')
        user.activity_level = request.form.get('activity_level')
        user.goal = request.form.get('goal')

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user = user)

#####################
# Upload Page Logic #
#####################

# PATH SETUP #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# TEMP STORAGE #
latest_image = None
latest_detections = []

@app.route("/upload", methods=['GET', 'POST'])
def upload_img():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        file = request.files["file"]

        if file.filename == "":
            return "No file selected"

        # HUGGING FACE API URL SETUP #
        hf_api_url = "https://nutrifit-model-nutrifit-yolo-api.hf.space/predict"

        # Forward the uploaded file over HTTP streams
        file.seek(0)
        files = {"file": (file.filename, file.read(), file.content_type)}
        
        try:
            response = requests.post(hf_api_url, files=files)
            response_data = response.json()
        except Exception as e:
            return f"AI Server Error: {str(e)}"

        # Extract labels returned from Hugging Face
        detected_labels = response_data.get("detections", [])
        boxed_image = response_data.get("boxed_image_base64", "")
        
        # GROUP SAME FOOD + COUNT
        grouped = {}
        for label in detected_labels:
            if label not in grouped:
                grouped[label] = {
                    "food": label,
                    "quantity": 1
                }
            else:
                grouped[label]["quantity"] += 1

        latest_detections = list(grouped.values())

        # Store data into the session cookie tracking
        if latest_detections:
            session["food_name"] = latest_detections[0]["food"]
        else:
            session["food_name"] = ""
            
        session["detections"] = latest_detections

        return render_template("edit_page.html", user = user, detections = latest_detections, boxed_image = boxed_image)
    
    return render_template("upload_page.html", user = user)

###################
# Edit Page Logic #
###################
def get_food_options(food_name):
    connection = sqlite3.connect("database/food.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM foods
        WHERE LOWER(name) LIKE ?
        ORDER BY name
        LIMIT 10
    """, (f"%{food_name.lower()}%",))

    foods = cursor.fetchall()

    connection.close()

    return foods

@app.route("/food_options")
def food_options():
    keyword = request.args.get("q", "").strip()

    if not keyword:
        return jsonify([])

    foods = get_food_options(keyword)

    return jsonify([food["name"] for food in foods])

@app.route("/edit")
def edit_page():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session['user_id'])

    detections = session.get("detections", [])

    image_file = session.get("boxed_image")

    return render_template("edit_page.html", user = user, detections = detections, image_file = image_file)

@app.route("/update_detections", methods=["POST"])
def update_detections():
    session["detections"] = request.get_json()

    return jsonify({"success": True})

#####################
# Result Page Logic #
#####################
def get_food_info(food_name):
    connection = sqlite3.connect("database/food.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name, calories, carbs, protein, fats
        FROM foods
        WHERE LOWER(name) LIKE ?
        LIMIT 1
    """, (f"%{food_name.lower()}%",))

    food = cursor.fetchone()

    connection.close()

    return food

@app.route("/result")
def result():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if 'food_name' not in session:
        return redirect(url_for('upload_img'))

    foods = []

    for item in session["detections"]:

        food_info = get_food_info(item["food"])

        if food_info:
            quantity = item["quantity"]

            foods.append({
                "name": food_info["name"],
                "quantity": quantity,
                "calories": food_info["calories"] * quantity,
                "carbs": food_info["carbs"] * quantity,
                "protein": food_info["protein"] * quantity,
                "fats": food_info["fats"] * quantity
            })

    return render_template("result_page.html", foods = foods, user = user)

######################
# History Page Logic #
######################
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])

    return render_template("history_page.html", user = user)

@app.route("/save_meal", methods = ["POST"])
def save_meal():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    meal_items = request.get_json()
    today = datetime.now().strftime("%Y-%m-%d")
    
    connection = sqlite3.connect("database/meal_history.db")
    cursor = connection.cursor()

    for data in meal_items:
        cursor.execute("""
            INSERT INTO meal_history(user_id, food_name, calories, carbs, protein, fats, servings, date)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)""", 
            (session["user_id"], data["food_name"], data["calories"], data["carbs"], data["protein"], data["fats"], data["servings"], today))

    connection.commit()

    connection.close()

    return jsonify({"message": "Meal saved successfully!"})

@app.route("/get_meals")
def get_meals():
    if 'user_id' not in session:
        return jsonify([])
    
    history_tab = request.args.get("type")
    date = request.args.get("date")

    connection = sqlite3.connect("database/meal_history.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    if history_tab == "daily":
        cursor.execute("""
            SELECT id, food_name, calories, carbs, protein, fats, servings
            FROM meal_history
            WHERE date = ? AND user_id = ?
        """, (date, session["user_id"]))

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
            AND user_id = ?
            ORDER BY date
        """, (str(year), f"{week - 1:02d}", session["user_id"]))

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
                "calories": r["calories"],
                "servings": r["servings"]
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
            "total_carbs": total_carbs,
            "total_protein": total_protein,
            "total_fats": total_fats,
            "days": grouped
        })
    elif history_tab == "monthly":
        year, month = date.split("-")

        cursor.execute("""
            SELECT date, calories, carbs, protein, fats
            FROM meal_history
            WHERE strftime('%Y', date) = ?
            AND strftime('%m', date) = ?
            AND user_id = ?
        """, (year, month, session["user_id"]))

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
            "total_carbs": total_carbs,
            "total_protein": total_protein,
            "total_fats": total_fats,
            "weeks": weekly
        })

    connection.close()
    return jsonify([])

@app.route("/delete_meal", methods = ["POST"])
def delete_meal():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()

    connection = sqlite3.connect("database/meal_history.db")
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM meal_history
        WHERE id = ?
        AND user_id = ?
    """, (data["id"], session["user_id"]))

    connection.commit()
    connection.close()

    return jsonify({"message": "Meal deleted successfully!"})

if __name__ == '__main__':
    app.run(debug = True)