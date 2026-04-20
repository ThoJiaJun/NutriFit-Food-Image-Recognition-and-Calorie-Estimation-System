from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()
    print("Database tables created successfully.")

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
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            return redirect(url_for('profile', user_id=user.id))
        else:
            flash('Invalid email or password!', 'danger')
    
    return render_template('login.html')

@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    user = User.query.get_or_404(user_id)

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
        return redirect(url_for('profile', user_id=user.id))
    return render_template('profile.html', user=user)

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

@app.route('/')
def index():
    return redirect(url_for('login'))

if __name__ == '__main__':  
    app.run(debug=True)