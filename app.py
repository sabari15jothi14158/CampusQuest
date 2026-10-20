
import os
from datetime import datetime, date

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)

app = Flask(__name__)

app.config["SECRET_KEY"] = "campusquest-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///campusquest.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# -------------------- DATABASE MODELS --------------------

class Student(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    xp = db.Column(db.Integer, default=0)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False
    )
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default="Medium")


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False
    )
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False
    )
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default="Medium")


class QuestCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False
    )
    quest_id = db.Column(db.Integer, nullable=False)
    quest_date = db.Column(db.String(10), nullable=False)
    xp = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "student_id", "quest_id", "quest_date",
            name="unique_student_quest_day"
        ),
    )


class FocusSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False
    )
    session_key = db.Column(db.String(100), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    xp = db.Column(db.Integer, nullable=False, default=10)
    completed_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_id", "session_key",
            name="unique_student_focus_session"
        ),
    )


# -------------------- DAILY QUESTS --------------------

QUESTS = {
    0: {
        "title": "Walk 5,000 steps",
        "description": "Stay active and reach your daily step goal.",
        "emoji": "🚶",
        "xp": 10
    },
    1: {
        "title": "Drink enough water",
        "description": "Keep yourself hydrated throughout the day.",
        "emoji": "💧",
        "xp": 10
    },
    2: {
        "title": "Study for 30 minutes",
        "description": "Focus on your studies for 30 minutes.",
        "emoji": "📚",
        "xp": 15
    },
    3: {
        "title": "Sleep on time",
        "description": "Maintain a healthy sleep routine.",
        "emoji": "😴",
        "xp": 10
    },
}


# -------------------- LOGIN MANAGEMENT --------------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Student, int(user_id))


# -------------------- CREATE DATABASE TABLES --------------------

with app.app_context():
    db.create_all()


# -------------------- HOME / DASHBOARD --------------------


# -------------------- HOME / DASHBOARD --------------------

@app.route("/")
@login_required
def home():
    today_date = date.today()
    today = today_date.isoformat()

    students = Student.query.order_by(
        Student.xp.desc(), Student.username.asc()
    ).all()

    # Show only pending tasks in the Daily Tasks list
    tasks = Task.query.filter_by(
        student_id=current_user.id,
        completed=False
    ).all()

    # Calculate completed and pending task counts
    completed_task_count = Task.query.filter_by(
        student_id=current_user.id,
        completed=True
    ).count()

    pending_task_count = Task.query.filter_by(
        student_id=current_user.id,
        completed=False
    ).count()

    total_task_count = (
        completed_task_count + pending_task_count
    )

    task_progress = (
        round(
            completed_task_count / total_task_count * 100
        )
        if total_task_count > 0 else 0
    )

    notes = Note.query.filter_by(
        student_id=current_user.id
    ).all()

    assignments = Assignment.query.filter_by(
        student_id=current_user.id
    ).order_by(
        Assignment.due_date.asc()
    ).all()

    completed_quests = QuestCompletion.query.filter_by(
        student_id=current_user.id,
        quest_date=today
    ).all()

    completed_quest_ids = [
        quest.quest_id for quest in completed_quests
    ]

    today_xp = sum(
        quest.xp for quest in completed_quests
    )

    quest_list = [
        {"id": quest_id, **quest}
        for quest_id, quest in QUESTS.items()
    ]

    pending_assignments = [
        assignment for assignment in assignments
        if not assignment.completed
    ]

    overdue_count = sum(
        1 for assignment in pending_assignments
        if assignment.due_date < today_date
    )

    due_today_count = sum(
        1 for assignment in pending_assignments
        if assignment.due_date == today_date
    )

    upcoming_count = sum(
        1 for assignment in pending_assignments
        if assignment.due_date > today_date
    )

    focus_sessions = FocusSession.query.filter_by(
        student_id=current_user.id
    ).all()

    focus_session_count = len(focus_sessions)

    focus_minutes = sum(
        session.duration_minutes
        for session in focus_sessions
    )

    focus_xp = sum(
        session.xp for session in focus_sessions
    )

    return render_template(
        "index.html",
        students=students,
        tasks=tasks,
        completed_task_count=completed_task_count,
        pending_task_count=pending_task_count,
        total_task_count=total_task_count,
        task_progress=task_progress,
        notes=notes,
        assignments=assignments,
        quests=quest_list,
        completed_quest_ids=completed_quest_ids,
        today_xp=today_xp,
        today_date=today_date,
        overdue_count=overdue_count,
        due_today_count=due_today_count,
        upcoming_count=upcoming_count,
        focus_session_count=focus_session_count,
        focus_minutes=focus_minutes,
        focus_xp=focus_xp
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please fill in all fields.")

        elif Student.query.filter_by(username=username).first():
            flash(
                "Username already exists. Please log in or use another username."
            )

        else:
            student = Student(
                username=username,
                password=generate_password_hash(password)
            )

            db.session.add(student)
            db.session.commit()

            flash("Registration successful! Please log in.")
            return redirect(url_for("login"))

    return render_template("register.html")


# -------------------- LOGIN --------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        student = Student.query.filter_by(
            username=username
        ).first()

        if student and check_password_hash(student.password, password):
            login_user(student)
            return redirect(url_for("home"))

        flash("Invalid username or password.")

    return render_template("login.html")


# -------------------- LOGOUT --------------------

@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# -------------------- DAILY QUEST XP --------------------

@app.route("/complete_quest", methods=["POST"])
@login_required
def complete_quest():
    data = request.get_json(silent=True) or {}

    quest_id = data.get("quest_id")
    completed = data.get("completed")

    if quest_id is None:
        quest_id = request.form.get("quest_id", type=int)

    if isinstance(quest_id, str) and quest_id.isdigit():
        quest_id = int(quest_id)

    if not isinstance(quest_id, int) or quest_id not in QUESTS:
        if request.is_json:
            return jsonify({"error": "Invalid quest."}), 400

        flash("Invalid quest.")
        return redirect(url_for("home"))

    if completed is None:
        completed_text = request.form.get("completed")

        if completed_text is not None:
            completed = completed_text.lower() == "true"
        elif not request.is_json:
            completed = True

    if not isinstance(completed, bool):
        return jsonify({"error": "Invalid completion status."}), 400

    today = date.today().isoformat()

    existing = QuestCompletion.query.filter_by(
        student_id=current_user.id,
        quest_id=quest_id,
        quest_date=today
    ).first()

    if completed and existing is None:
        quest = QUESTS[quest_id]

        record = QuestCompletion(
            student_id=current_user.id,
            quest_id=quest_id,
            quest_date=today,
            xp=quest["xp"]
        )

        current_user.xp = (current_user.xp or 0) + quest["xp"]
        db.session.add(record)
        db.session.commit()

        flash("Daily quest completed! XP earned.")

    elif not completed and existing is not None:
        current_user.xp = max(
            0, (current_user.xp or 0) - existing.xp
        )
        db.session.delete(existing)
        db.session.commit()

        flash("Daily quest marked as incomplete.")

    today_records = QuestCompletion.query.filter_by(
        student_id=current_user.id,
        quest_date=today
    ).all()

    response_data = {
        "success": True,
        "today_xp": sum(record.xp for record in today_records),
        "total_xp": current_user.xp,
        "completed_quest_ids": [
            record.quest_id for record in today_records
        ]
    }

    if request.is_json:
        return jsonify(response_data)

    return redirect(url_for("home"))


# -------------------- FOCUS TIMER XP --------------------

@app.route("/complete_focus_session", methods=["POST"])
@login_required
def complete_focus_session():
    data = request.get_json(silent=True) or {}

    session_key = data.get("session_key", "")
    duration = data.get("duration_minutes", data.get("duration"))

    if isinstance(duration, str) and duration.isdigit():
        duration = int(duration)

    if (
        not isinstance(session_key, str)
        or not session_key.strip()
        or len(session_key) > 100
    ):
        return jsonify({"error": "Invalid focus session."}), 400

    if duration not in (15, 25, 30, 50):
        return jsonify({"error": "Invalid focus duration."}), 400

    existing = FocusSession.query.filter_by(
        student_id=current_user.id,
        session_key=session_key
    ).first()

    if existing:
        return jsonify({
            "success": True,
            "already_awarded": True,
            "xp_awarded": 0,
            "total_xp": current_user.xp
        })

    session_record = FocusSession(
        student_id=current_user.id,
        session_key=session_key,
        duration_minutes=duration,
        xp=10
    )

    current_user.xp = (current_user.xp or 0) + 10
    db.session.add(session_record)
    db.session.commit()

    student_sessions = FocusSession.query.filter_by(
        student_id=current_user.id
    ).all()

    return jsonify({
        "success": True,
        "already_awarded": False,
        "xp_awarded": 10,
        "total_xp": current_user.xp,
        "focus_session_count": len(student_sessions),
        "focus_minutes": sum(
            item.duration_minutes for item in student_sessions
        ),
        "focus_xp": sum(item.xp for item in student_sessions)
    })


# -------------------- DAILY TASKS --------------------

@app.route("/add_task", methods=["POST"])
@login_required
def add_task():
    title = request.form.get("title", "").strip()
    priority = request.form.get("priority", "Medium")

    if title:
        task = Task(
            student_id=current_user.id,
            title=title,
            priority=priority
        )

        db.session.add(task)
        db.session.commit()
        flash("Task added successfully!")
    else:
        flash("Please enter a task title.")

    return redirect(url_for("home"))


# -------------------- COMPLETE / UNDO DAILY TASK --------------------

@app.route("/complete_task/<int:task_id>", methods=["POST"])
@login_required
def complete_task(task_id):
    task = Task.query.filter_by(
        id=task_id,
        student_id=current_user.id
    ).first_or_404()

    task.completed = not task.completed
    db.session.commit()

    flash(
        "Task marked as completed!"
        if task.completed else "Task marked as incomplete!"
    )

    return redirect(url_for("home"))


# -------------------- IMPORTANT NOTES --------------------

@app.route("/add_note", methods=["POST"])
@login_required
def add_note():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if title and content:
        note = Note(
            student_id=current_user.id,
            title=title,
            content=content
        )

        db.session.add(note)
        db.session.commit()
        flash("Note saved successfully!")
    else:
        flash("Please enter both the note title and content.")

    return redirect(url_for("home"))


# -------------------- ASSIGNMENTS & DEADLINES --------------------

@app.route("/add_assignment", methods=["POST"])
@login_required
def add_assignment():
    title = request.form.get("title", "").strip()

    due_date_text = (
        request.form.get("due_date", "").strip()
        or request.form.get("deadline", "").strip()
    )

    priority = request.form.get("priority", "Medium")

    if not title or not due_date_text:
        flash("Please enter the assignment title and deadline.")
        return redirect(url_for("home"))

    try:
        due_date = datetime.strptime(
            due_date_text, "%Y-%m-%d"
        ).date()

        assignment = Assignment(
            student_id=current_user.id,
            title=title,
            due_date=due_date,
            priority=priority
        )

        db.session.add(assignment)
        db.session.commit()
        flash("Assignment added successfully!")

    except ValueError:
        flash("Please enter a valid deadline.")

    return redirect(url_for("home"))


# -------------------- COMPLETE / UNDO ASSIGNMENT --------------------

@app.route("/complete_assignment/<int:assignment_id>", methods=["POST"])
@login_required
def complete_assignment(assignment_id):
    assignment = Assignment.query.filter_by(
        id=assignment_id,
        student_id=current_user.id
    ).first_or_404()

    assignment.completed = not assignment.completed
    db.session.commit()

    flash(
        "Assignment marked as completed!"
        if assignment.completed
        else "Assignment marked as incomplete!"
    )

    return redirect(url_for("home"))


# -------------------- ADD XP --------------------

@app.route("/add_xp", methods=["POST"])
@login_required
def add_xp():
    amount = request.form.get("xp", type=int)

    if amount is not None and 0 < amount <= 100:
        current_user.xp = (current_user.xp or 0) + amount
        db.session.commit()
        flash("XP added successfully!")
    else:
        flash("Invalid XP amount.")

    return redirect(url_for("home"))


# -------------------- RUN APP --------------------

if __name__ == "__main__":
    app.run(debug=True)
