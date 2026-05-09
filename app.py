from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habits.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ========== ВСЕ МОДЕЛИ (ТАБЛИЦЫ) ==========

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # nullable=True - можно не указывать
    password_hash = db.Column(db.String(200), nullable=False)
    total_points = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Habit(db.Model):
    __tablename__ = 'habits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Другое')
    created_at = db.Column(db.DateTime, default=datetime.now)

class HabitLog(db.Model):
    __tablename__ = 'habit_logs'
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habits.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)

class Meal(db.Model):
    __tablename__ = 'meals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    meal_type = db.Column(db.String(50))
    food_name = db.Column(db.String(200))
    calories = db.Column(db.Integer)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)

class Workout(db.Model):
    __tablename__ = 'workouts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    duration = db.Column(db.Integer)
    calories_burned = db.Column(db.Integer)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)

class DailyGoal(db.Model):
    __tablename__ = 'daily_goals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)
    calorie_goal = db.Column(db.Integer, default=2000)
    workout_goal = db.Column(db.Integer, default=30)

class Friend(db.Model):
    __tablename__ = 'friends'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.now)

class Feed(db.Model):
    __tablename__ = 'feed'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(50))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_user():
    """Получает текущего пользователя"""
    from flask import session
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    # Если пользователь не залогинен, возвращаем None
    return None

def add_to_feed(user_id, action_type, content):
    feed = Feed(user_id=user_id, action_type=action_type, content=content)
    db.session.add(feed)
    db.session.commit()

def add_points(user_id, points):
    user = User.query.get(user_id)
    if user:
        user.total_points += points
        new_level = user.total_points // 500 + 1
        if new_level > user.level:
            user.level = new_level
            add_to_feed(user_id, 'level_up', f'Достигнут {new_level} уровень! 🎉')
        db.session.commit()
# ========== РАБОТА С СЕССИЯМИ И ПОЛЬЗОВАТЕЛЯМИ ==========

def get_current_user():
    """Получает текущего залогиненного пользователя из сессии"""
    from flask import session
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

def login_required(f):
    """Декоратор для проверки авторизации"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ========== ГЛАВНАЯ СТРАНИЦА ==========
# ========== РЕГИСТРАЦИЯ И ВХОД ==========

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        # Проверки
        if password != confirm:
            flash('Пароли не совпадают!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято!', 'danger')
            return redirect(url_for('register'))
        
        # Проверка email только если он был введен
        if email and User.query.filter_by(email=email).first():
            flash('Email уже используется!', 'danger')
            return redirect(url_for('register'))
        
        # Создаем пользователя
        user = User(username=username, email=email if email else None)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Создаем цели по умолчанию
        goal = DailyGoal(user_id=user.id, date=datetime.now().date())
        db.session.add(goal)
        db.session.commit()
        
        flash('Регистрация успешна! Войдите в систему.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))
@app.route('/')
@login_required 
def index():
    user = get_user()
    if not user:
        flash('Пожалуйста, войдите в систему', 'warning')
        return redirect(url_for('login'))
    today = datetime.now().date()
    habits = Habit.query.filter_by(user_id=user.id).all()
    
    habits_with_status = []
    for habit in habits:
        log = HabitLog.query.filter_by(habit_id=habit.id, date=today).first()
        habits_with_status.append({'habit': habit, 'completed': log is not None})
    
    meals = Meal.query.filter_by(user_id=user.id, date=today).all()
    total_calories = sum(m.calories or 0 for m in meals)
    
    workouts = Workout.query.filter_by(user_id=user.id, date=today).all()
    total_workout_time = sum(w.duration or 0 for w in workouts)
    total_calories_burned = sum(w.calories_burned or 0 for w in workouts)
    
    goal = DailyGoal.query.filter_by(user_id=user.id, date=today).first()
    if not goal:
        goal = DailyGoal(user_id=user.id, date=today)
        db.session.add(goal)
        db.session.commit()
    
    return render_template('index.html', 
                         habits=habits_with_status, today=today,
                         meals=meals, total_calories=total_calories,
                         workouts=workouts, total_workout_time=total_workout_time,
                         total_calories_burned=total_calories_burned, goal=goal, user=user)

# ========== ПРИВЫЧКИ ==========

@app.route('/habits')
def habits():
    user = get_user()
    all_habits = Habit.query.filter_by(user_id=user.id).all()
    return render_template('habits.html', habits=all_habits)

@app.route('/add_habit', methods=['GET', 'POST'])
def add_habit():
    if request.method == 'POST':
        user = get_user()
        habit = Habit(user_id=user.id, 
                     name=request.form.get('name'),
                     description=request.form.get('description'),
                     category=request.form.get('category'))
        db.session.add(habit)
        db.session.commit()
        flash('Привычка добавлена!', 'success')
        return redirect(url_for('habits'))
    return render_template('add_habit.html')

@app.route('/toggle_habit/<int:habit_id>', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    user = get_user()
    today = datetime.now().date()
    habit = Habit.query.get(habit_id)  # Добавьте эту строку
    log = HabitLog.query.filter_by(habit_id=habit_id, date=today).first()
    
    if log:
        db.session.delete(log)
        completed = False
    else:
        log = HabitLog(habit_id=habit_id, user_id=user.id, date=today)
        db.session.add(log)
        add_points(user.id, 10)
        add_to_feed(user.id, 'habit_completed', f'Выполнил привычку "{habit.name}" ✅')  # Добавьте эту строку
        completed = True
    
    db.session.commit()
    return jsonify({'success': True, 'completed': completed})

@app.route('/delete_habit/<int:id>', methods=['POST'])
def delete_habit(id):
    habit = Habit.query.get_or_404(id)
    db.session.delete(habit)
    db.session.commit()
    flash('Привычка удалена', 'info')
    return redirect(url_for('habits'))

# ========== ПИТАНИЕ ==========

@app.route('/nutrition')
def nutrition():
    user = get_user()
    today = datetime.now().date()
    meals = Meal.query.filter_by(user_id=user.id, date=today).all()
    return render_template('nutrition.html', meals=meals)

@app.route('/add_meal', methods=['GET', 'POST'])
@login_required
def add_meal():
    if request.method == 'POST':
        user = get_user()
        meal = Meal(user_id=user.id,
                   meal_type=request.form.get('meal_type'),
                   food_name=request.form.get('food_name'),
                   calories=int(request.form.get('calories', 0)))
        db.session.add(meal)
        db.session.commit()
        add_points(user.id, 5)
        add_to_feed(user.id, 'meal_added', f'Добавил запись о питании: {meal.food_name} 🍎')  # Добавьте эту строку
        flash('Прием пищи добавлен!', 'success')
        return redirect(url_for('nutrition'))
    return render_template('add_meal.html')

@app.route('/delete_meal/<int:id>', methods=['POST'])
def delete_meal(id):
    meal = Meal.query.get_or_404(id)
    db.session.delete(meal)
    db.session.commit()
    flash('Прием пищи удален', 'info')
    return redirect(url_for('nutrition'))

# ========== ТРЕНИРОВКИ ==========

@app.route('/workouts')
def workouts():
    user = get_user()
    today = datetime.now().date()
    workouts_list = Workout.query.filter_by(user_id=user.id, date=today).all()
    return render_template('workouts.html', workouts=workouts_list)

@app.route('/add_workout', methods=['GET', 'POST'])
@login_required
def add_workout():
    if request.method == 'POST':
        user = get_user()
        workout = Workout(user_id=user.id,
                         exercise_name=request.form.get('exercise_name'),
                         category=request.form.get('category'),
                         duration=int(request.form.get('duration', 0)),
                         calories_burned=int(request.form.get('calories_burned', 0)))
        db.session.add(workout)
        db.session.commit()
        add_points(user.id, 50)
        add_to_feed(user.id, 'workout', f'Выполнил тренировку: {workout.exercise_name} 🏋️')
        flash('Тренировка добавлена!', 'success')
        return redirect(url_for('workouts'))
    return render_template('add_workout.html')

@app.route('/delete_workout/<int:id>', methods=['POST'])
def delete_workout(id):
    workout = Workout.query.get_or_404(id)
    db.session.delete(workout)
    db.session.commit()
    flash('Тренировка удалена', 'info')
    return redirect(url_for('workouts'))

@app.route('/update_goals', methods=['POST'])
def update_goals():
    user = get_user()
    today = datetime.now().date()
    goal = DailyGoal.query.filter_by(user_id=user.id, date=today).first()
    if not goal:
        goal = DailyGoal(user_id=user.id, date=today)
    
    goal.calorie_goal = int(request.form.get('calorie_goal', 2000))
    goal.workout_goal = int(request.form.get('workout_goal', 30))
    
    db.session.add(goal)
    db.session.commit()
    flash('Цели обновлены!', 'success')
    return redirect(url_for('index'))

# ========== ДРУЗЬЯ ==========

@app.route('/friends')
def friends():
    user = get_user()
    sent_requests = Friend.query.filter_by(user_id=user.id, status='pending').all()
    received_requests = Friend.query.filter_by(friend_id=user.id, status='pending').all()
    
    accepted_friends = []
    friendships = Friend.query.filter(
        ((Friend.user_id == user.id) | (Friend.friend_id == user.id)),
        Friend.status == 'accepted'
    ).all()
    
    for friendship in friendships:
        if friendship.user_id == user.id:
            friend = User.query.get(friendship.friend_id)
        else:
            friend = User.query.get(friendship.user_id)
        if friend:
            accepted_friends.append(friend)
    
    return render_template('friends.html', 
                         sent_requests=sent_requests,
                         received_requests=received_requests,
                         friends=accepted_friends)

@app.route('/add_friend', methods=['GET', 'POST'])
def add_friend():
    if request.method == 'POST':
        username = request.form.get('username')
        current_user = get_user()
        friend = User.query.filter_by(username=username).first()
        
        if not friend:
            flash('Пользователь не найден!', 'danger')
        elif friend.id == current_user.id:
            flash('Нельзя добавить самого себя!', 'warning')
        else:
            existing = Friend.query.filter(
                ((Friend.user_id == current_user.id) & (Friend.friend_id == friend.id)) |
                ((Friend.user_id == friend.id) & (Friend.friend_id == current_user.id))
            ).first()
            
            if existing:
                flash('Заявка уже существует!', 'warning')
            else:
                new_request = Friend(user_id=current_user.id, friend_id=friend.id, status='pending')
                db.session.add(new_request)
                db.session.commit()
                flash(f'Заявка отправлена {username}!', 'success')
        return redirect(url_for('friends'))
    return render_template('add_friend.html')

@app.route('/accept_friend/<int:request_id>', methods=['POST'])
def accept_friend(request_id):
    friend_request = Friend.query.get_or_404(request_id)
    friend_request.status = 'accepted'
    db.session.commit()
    flash('Вы теперь друзья!', 'success')
    return redirect(url_for('friends'))

@app.route('/decline_friend/<int:request_id>', methods=['POST'])
def decline_friend(request_id):
    friend_request = Friend.query.get_or_404(request_id)
    db.session.delete(friend_request)
    db.session.commit()
    flash('Заявка отклонена', 'info')
    return redirect(url_for('friends'))

@app.route('/create_test_user')
def create_test_user():
    """Создает тестового пользователя (работает через браузер)"""
    test_user = User.query.filter_by(username='ТестовыйДруг').first()
    if not test_user:
        test_user = User(username='ТестовыйДруг')
        db.session.add(test_user)
        db.session.commit()
        flash('✅ Создан тестовый друг! Теперь вы можете отправить ему заявку', 'success')
    else:
        flash('ℹ️ Тестовый друг уже существует', 'info')
    return redirect(url_for('friends'))

# ========== ЛЕНТА ==========

@app.route('/feed')
@login_required
def feed():
    user = get_user()
    # Получаем все записи для пользователя, сортируем от новых к старым
    feed_posts = Feed.query.filter_by(user_id=user.id).order_by(Feed.created_at.desc()).all()
    return render_template('feed.html', feed_posts=feed_posts)

# ========== ЗАПУСК ==========
# ========== КОМАНДА ДЛЯ СОЗДАНИЯ ТЕСТОВОГО ДРУГА (без flash) ==========

def create_test_user_silent():
    """Создает тестового пользователя без использования flash"""
    test_user = User.query.filter_by(username='ТестовыйДруг').first()
    if not test_user:
        test_user = User(username='ТестовыйДруг')
        db.session.add(test_user)
        db.session.commit()
        print("✅ Тестовый друг создан: ТестовыйДруг")
    else:
        print("ℹ️ Тестовый друг уже существует")

# ========== ЗАПУСК ==========

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()  # Удаляем старые таблицы
        db.create_all()  # Создаем новые
    app.run(debug=True)