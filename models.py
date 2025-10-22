from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model - supports only admin and student roles"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin or student
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} - {self.role}>'


class Student(db.Model):
    """Student profile model"""
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)

    # Relationships
    attempts = db.relationship('Attempt', backref='student', lazy=True, cascade='all, delete-orphan')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __repr__(self):
        return f'<Student {self.student_id} - {self.full_name}>'


class SchoolClass(db.Model):
    """School class/form model"""
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # e.g., "JSS 1A"
    level = db.Column(db.String(20))  # JSS1, JSS2, SS1, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    students = db.relationship('Student', backref='school_class', lazy=True)
    subjects = db.relationship('Subject', backref='school_class', lazy=True)
    exams = db.relationship('Exam', backref='school_class', lazy=True)

    def __repr__(self):
        return f'<SchoolClass {self.name}>'


class Subject(db.Model):
    """Subject model - simplified without teacher assignment"""
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    exams = db.relationship('Exam', backref='subject', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Subject {self.name} - {self.school_class.name}>'


class Exam(db.Model):
    """Exam model - simplified for MVP"""
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)

    duration_minutes = db.Column(db.Integer, nullable=False)  # Exam duration
    total_marks = db.Column(db.Integer, default=0)
    pass_mark = db.Column(db.Integer, default=40)

    status = db.Column(db.String(20), default='draft')  # draft, published, closed

    # Optional scheduling
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan', order_by='Question.order')
    attempts = db.relationship('Attempt', backref='exam', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Exam {self.title}>'


class Question(db.Model):
    """Question model - only MCQ and True/False types"""
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # mcq or true_false
    marks = db.Column(db.Integer, default=1)
    order = db.Column(db.Integer, default=0)

    # For MCQ
    option_a = db.Column(db.Text)
    option_b = db.Column(db.Text)
    option_c = db.Column(db.Text)
    option_d = db.Column(db.Text)

    # Correct answer: For MCQ: 'A', 'B', 'C', 'D'; For True/False: 'True' or 'False'
    correct_answer = db.Column(db.String(10), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True)

    def __repr__(self):
        return f'<Question {self.id} - {self.question_type}>'


class Attempt(db.Model):
    """Attempt model - one attempt per student per exam"""
    __tablename__ = 'attempts'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)

    status = db.Column(db.String(20), default='in_progress')  # in_progress or submitted

    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)

    total_score = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    grade = db.Column(db.String(5))  # A, B, C, D, F

    # Relationships
    answers = db.relationship('Answer', backref='attempt', lazy=True, cascade='all, delete-orphan')

    # Unique constraint - one attempt per student per exam
    __table_args__ = (
        db.UniqueConstraint('student_id', 'exam_id', name='unique_student_exam_attempt'),
    )

    def calculate_grade(self):
        """Calculate grade based on percentage"""
        if self.percentage >= 75:
            self.grade = 'A'
        elif self.percentage >= 60:
            self.grade = 'B'
        elif self.percentage >= 50:
            self.grade = 'C'
        elif self.percentage >= 40:
            self.grade = 'D'
        else:
            self.grade = 'F'

    def __repr__(self):
        return f'<Attempt {self.id} - Student {self.student_id} - Exam {self.exam_id}>'


class Answer(db.Model):
    """Answer model - automatically graded"""
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)

    answer_text = db.Column(db.String(10))  # 'A', 'B', 'C', 'D', 'True', or 'False'
    is_correct = db.Column(db.Boolean, default=False)
    marks_obtained = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Answer {self.id} - Question {self.question_id}>'
