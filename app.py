from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone
import time
import calendar
import sqlite3
import os
import cv2
from ultralytics import YOLO

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

# PATH SETUP #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
MODEL_PATH = os.path.join(BASE_DIR, "model", "yolo11s_best.pt")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# LOAD MODEL (LOCAL ONLY) #
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError("Model not found in /model folder!")

model = YOLO(MODEL_PATH)

# TEMP STORAGE #
latest_image = None
latest_detections = []

####################
# Login Page Logic #
####################
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
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
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get_or_404(session['user_id'])
    return render_template('dashboard.html', user = user)

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
@app.route("/upload", methods=['GET', 'POST'])
def upload_img():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        file = request.files["file"]

        if file.filename == "":
            return "No file selected"

        # Save image
        filename = str(int(time.time())) + "_" + file.filename
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(image_path)

        # Run YOLO
        results = model(image_path)[0]
        img = cv2.imread(image_path)
        detections = []

        # DETECTION LOOP
        for box in results.boxes:
            confidence = float(box.conf[0])

            # Ignore weak detections
            if confidence < 0.25:
                continue

            cls_id = int(box.cls[0])

            label = model.names[cls_id]

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # DRAW BOX
            cv2.rectangle(
                img,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            # LABEL TEXT
            text = f"{label}"

            cv2.putText(
                img,
                text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

            detections.append({
                "food": label
            })

        # If nothing detected
        if not detections:
            session["detections"] = []
            session["boxed_image"] = filename
            return redirect(url_for("edit_page"))
        
        # SAVE OUTPUT IMAGE ONLY IF THERE ARE DETECTIONS
        output_filename = "boxed_" + filename

        output_path = os.path.join(
            UPLOAD_FOLDER,
            output_filename
        )

        cv2.imwrite(output_path, img)
            
        # GROUP SAME FOOD + COUNT
        grouped = {}

        for item in detections:

            label = item["food"]

            if label not in grouped:

                grouped[label] = {
                    "food": label,
                    "quantity": 1
                }
            else:
                grouped[label]["quantity"] += 1

        latest_detections = list(grouped.values())

        session["food_name"] = detections[0]["food"]
        session["detections"] = latest_detections
        session["boxed_image"] = output_filename

        return redirect(url_for("edit_page"))
    
    return render_template("upload_page.html", user = user)

###################
# Edit Page Logic #
###################
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