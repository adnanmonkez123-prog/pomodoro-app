import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, instance_path='/tmp')
app.config['SECRET_KEY'] = 'pomodoro-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/pomodoro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- نموذج قاعدة البيانات ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='student')
    is_banned = db.Column(db.Boolean, default=False)

    work_time = db.Column(db.Integer, default=25)
    short_break = db.Column(db.Integer, default=5)
    long_break = db.Column(db.Integer, default=15)

class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- التصميم والواجهات ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تطبيق Pomodoro الدراسي</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #f4f6f8; margin: 0; padding: 20px; text-align: center; }
        nav { margin-bottom: 20px; }
        a { color: #3498db; text-decoration: none; margin: 0 10px; font-weight: bold; }
        .card { background: white; max-width: 500px; margin: 20px auto; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .timer { font-size: 50px; font-weight: bold; color: #2c3e50; margin: 20px 0; }
        button { background: #3498db; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 6px; cursor: pointer; margin: 5px; }
        button:hover { background: #2980b9; }
        .danger { background: #e74c3c; }
    </style>
</head>
<body>
    <nav>
        {% if current_user.is_authenticated %}
            مرحباً، {{ current_user.username }} | <a href="{{ url_for('logout') }}">تسجيل الخروج</a>
        {% else %}
            <a href="{{ url_for('login') }}">تسجيل الدخول</a> | <a href="{{ url_for('register') }}">إنشاء حساب</a>
        {% endif %}
    </nav>
    <div class="card">
        <h1>تطبيق Pomodoro</h1>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <p style="color: red;">{{ message }}</p>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% if current_user.is_authenticated %}
            <div class="timer" id="timer">25:00</div>
            <button onclick="startTimer()">بدء</button>
            <button class="danger" onclick="resetTimer()">إعادة ضبط</button>
            <script>
                let time = {{ current_user.work_time }} * 60;
                let timerInterval;
                function updateTimer() {
                    let minutes = Math.floor(time / 60);
                    let seconds = time % 60;
                    document.getElementById('timer').innerText = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
                }
                function startTimer() {
                    clearInterval(timerInterval);
                    timerInterval = setInterval(() => {
                        if (time > 0) {
                            time--;
                            updateTimer();
                        } else {
                            clearInterval(timerInterval);
                            alert("انتهى وقت الجلسة!");
                        }
                    }, 1000);
                }
                function resetTimer() {
                    clearInterval(timerInterval);
                    time = {{ current_user.work_time }} * 60;
                    updateTimer();
                }
            </script>
        {% else %}
            <p>سجل الدخول لبدء تنظيم وقت دراستك!</p>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم مستخدم بالفعل')
            return redirect(url_for('register'))
        new_user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template_string('''
        <div style="text-align:center; margin-top:50px;">
            <h2>إنشاء حساب جديد</h2>
            <form method="POST">
                <input type="text" name="username" placeholder="اسم المستخدم" required><br><br>
                <input type="password" name="password" placeholder="كلمة المرور" required><br><br>
                <button type="submit">تسجيل</button>
            </form>
        </div>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('بيانات الدخول غير صحيحة')
    return render_template_string('''
        <div style="text-align:center; margin-top:50px;">
            <h2>تسجيل الدخول</h2>
            <form method="POST">
                <input type="text" name="username" placeholder="اسم المستخدم" required><br><br>
                <input type="password" name="password" placeholder="كلمة المرور" required><br><br>
                <button type="submit">دخول</button>
            </form>
        </div>
    ''')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))
