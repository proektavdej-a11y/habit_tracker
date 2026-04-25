from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habits.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модель привычки
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Другое')
    created_at = db.Column(db.DateTime, default=datetime.now)
    
class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)
    habit = db.relationship('Habit', backref='logs')

# Модель для питания
class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal_type = db.Column(db.String(50))  # завтрак, обед, ужин, перекус
    food_name = db.Column(db.String(200))
    calories = db.Column(db.Integer)
    protein = db.Column(db.Float)  # белки в граммах
    carbs = db.Column(db.Float)    # углеводы в граммах
    fats = db.Column(db.Float)     # жиры в граммах
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)
    time = db.Column(db.String(5))
    
# Модель для тренировок
class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(100))
    category = db.Column(db.String(50))  # кардио, сила, растяжка
    duration = db.Column(db.Integer)  # в минутах
    calories_burned = db.Column(db.Integer)
    sets = db.Column(db.Integer)  # подходы
    reps = db.Column(db.Integer)   # повторения
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)
    time = db.Column(db.String(5))

# Модель для дневной цели
class DailyGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)
    calorie_goal = db.Column(db.Integer, default=2000)
    water_goal = db.Column(db.Integer, default=2000)  # в мл
    workout_goal = db.Column(db.Integer, default=30)  # в минутах

# Главная страница
@app.route('/')
def index():
    today = datetime.now().date()
    habits = Habit.query.all()
    
    habits_with_status = []
    for habit in habits:
        log = HabitLog.query.filter_by(habit_id=habit.id, date=today).first()
        habits_with_status.append({
            'habit': habit,
            'completed': log is not None
        })
    
    # Получаем питание за сегодня
    meals = Meal.query.filter_by(date=today).order_by(Meal.time).all()
    total_calories = sum(meal.calories or 0 for meal in meals)
    total_protein = sum(meal.protein or 0 for meal in meals)
    total_carbs = sum(meal.carbs or 0 for meal in meals)
    total_fats = sum(meal.fats or 0 for meal in meals)
    
    # Получаем тренировки за сегодня
    workouts = Workout.query.filter_by(date=today).all()
    total_workout_time = sum(workout.duration or 0 for workout in workouts)
    total_calories_burned = sum(workout.calories_burned or 0 for workout in workouts)
    
    # Получаем или создаем цель на сегодня
    goal = DailyGoal.query.filter_by(date=today).first()
    if not goal:
        goal = DailyGoal(date=today)
        db.session.add(goal)
        db.session.commit()
    
    return render_template('index.html', 
                         habits=habits_with_status, 
                         today=today,
                         meals=meals,
                         total_calories=total_calories,
                         total_protein=total_protein,
                         total_carbs=total_carbs,
                         total_fats=total_fats,
                         workouts=workouts,
                         total_workout_time=total_workout_time,
                         total_calories_burned=total_calories_burned,
                         goal=goal)

# Страница питания
@app.route('/nutrition')
def nutrition():
    today = datetime.now().date()
    meals = Meal.query.filter_by(date=today).order_by(Meal.time).all()
    
    # Статистика за неделю
    week_stats = []
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        day_meals = Meal.query.filter_by(date=date).all()
        day_calories = sum(meal.calories or 0 for meal in day_meals)
        week_stats.append({
            'date': date,
            'calories': day_calories
        })
    
    return render_template('nutrition.html', meals=meals, week_stats=week_stats)

# Добавление приема пищи
@app.route('/add_meal', methods=['GET', 'POST'])
def add_meal():
    if request.method == 'POST':
        meal = Meal(
            meal_type=request.form.get('meal_type'),
            food_name=request.form.get('food_name'),
            calories=int(request.form.get('calories', 0)),
            protein=float(request.form.get('protein', 0)),
            carbs=float(request.form.get('carbs', 0)),
            fats=float(request.form.get('fats', 0)),
            time=request.form.get('time', datetime.now().strftime('%H:%M'))
        )
        db.session.add(meal)
        db.session.commit()
        flash('Прием пищи добавлен!', 'success')
        return redirect(url_for('nutrition'))
    
    return render_template('add_meal.html')

# Удаление приема пищи
@app.route('/delete_meal/<int:id>', methods=['POST'])
def delete_meal(id):
    meal = Meal.query.get_or_404(id)
    db.session.delete(meal)
    db.session.commit()
    flash('Прием пищи удален', 'info')
    return redirect(url_for('nutrition'))

# Страница тренировок
@app.route('/workouts')
def workouts():
    today = datetime.now().date()
    workouts_list = Workout.query.filter_by(date=today).order_by(Workout.time).all()
    
    # Статистика за неделю
    week_stats = []
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        day_workouts = Workout.query.filter_by(date=date).all()
        day_duration = sum(w.duration or 0 for w in day_workouts)
        week_stats.append({
            'date': date,
            'duration': day_duration
        })
    
    return render_template('workouts.html', workouts=workouts_list, week_stats=week_stats)

# Добавление тренировки
@app.route('/add_workout', methods=['GET', 'POST'])
def add_workout():
    if request.method == 'POST':
        workout = Workout(
            exercise_name=request.form.get('exercise_name'),
            category=request.form.get('category'),
            duration=int(request.form.get('duration', 0)),
            calories_burned=int(request.form.get('calories_burned', 0)),
            sets=int(request.form.get('sets', 0)),
            reps=int(request.form.get('reps', 0)),
            time=request.form.get('time', datetime.now().strftime('%H:%M'))
        )
        db.session.add(workout)
        db.session.commit()
        flash('Тренировка добавлена!', 'success')
        return redirect(url_for('workouts'))
    
    return render_template('add_workout.html')

# Удаление тренировки
@app.route('/delete_workout/<int:id>', methods=['POST'])
def delete_workout(id):
    workout = Workout.query.get_or_404(id)
    db.session.delete(workout)
    db.session.commit()
    flash('Тренировка удалена', 'info')
    return redirect(url_for('workouts'))

# Обновление целей
@app.route('/update_goals', methods=['POST'])
def update_goals():
    today = datetime.now().date()
    goal = DailyGoal.query.filter_by(date=today).first()
    if not goal:
        goal = DailyGoal(date=today)
    
    goal.calorie_goal = int(request.form.get('calorie_goal', 2000))
    goal.water_goal = int(request.form.get('water_goal', 2000))
    goal.workout_goal = int(request.form.get('workout_goal', 30))
    
    db.session.add(goal)
    db.session.commit()
    flash('Цели обновлены!', 'success')
    return redirect(url_for('index'))

# Остальные маршруты из предыдущей версии
@app.route('/habits')
def habits():
    all_habits = Habit.query.all()
    return render_template('habits.html', habits=all_habits)

@app.route('/add_habit', methods=['GET', 'POST'])
def add_habit():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        
        habit = Habit(name=name, description=description, category=category)
        db.session.add(habit)
        db.session.commit()
        flash('Привычка добавлена!', 'success')
        return redirect(url_for('habits'))
    
    return render_template('add_habit.html')

@app.route('/toggle_habit/<int:habit_id>', methods=['POST'])
def toggle_habit(habit_id):
    today = datetime.now().date()
    log = HabitLog.query.filter_by(habit_id=habit_id, date=today).first()
    
    if log: 
        db.session.delete(log)
        message = 'Отметка снята'
        completed = False
    else:
        log = HabitLog(habit_id=habit_id, date=today)
        db.session.add(log)
        message = 'Отлично! Привычка выполнена!'
        completed = True
    
    db.session.commit()
    return jsonify({'success': True, 'message': message, 'completed': completed})

@app.route('/delete_habit/<int:id>', methods=['POST'])
def delete_habit(id):
    habit = Habit.query.get_or_404(id)
    db.session.delete(habit)
    db.session.commit()
    flash('Привычка удалена', 'info')
    return redirect(url_for('habits'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 