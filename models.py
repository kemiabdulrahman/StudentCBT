from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, teacher, student
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    teacher_profile = db.relationship('Teacher', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email} - {self.role}>'
        
# Adding the parent email to the student data

class Student(db.Model):
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


class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    teacher_id = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    subjects = db.relationship('Subject', backref='teacher', lazy=True)
    exams = db.relationship('Exam', backref='teacher', lazy=True)
    
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'
    
    def __repr__(self):
        return f'<Teacher {self.teacher_id} - {self.full_name}>'


class AcademicSession(db.Model):
    __tablename__ = 'academic_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g., "2024/2025"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    terms = db.relationship('Term', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AcademicSession {self.name}>'


class Term(db.Model):
    __tablename__ = 'terms'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # First, Second, Third
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)
    
    # Relationships
    exams = db.relationship('Exam', backref='term', lazy=True)
    
    def __repr__(self):
        return f'<Term {self.name} - {self.session.name}>'


class SchoolClass(db.Model):
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
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    
    # Relationships
    exams = db.relationship('Exam', backref='subject', lazy=True)
    
    def __repr__(self):
        return f'<Subject {self.name} - {self.school_class.name}>'


class Exam(db.Model):
    __tablename__ = 'exams'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)
    
    duration_minutes = db.Column(db.Integer, nullable=False)  # Exam duration
    total_marks = db.Column(db.Integer, default=0)
    pass_mark = db.Column(db.Integer, default=40)
    
    status = db.Column(db.String(20), default='draft')  # draft, published, closed
    allow_multiple_attempts = db.Column(db.Boolean, default=False)
    max_attempts = db.Column(db.Integer, default=1)
    
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('Attempt', backref='exam', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Exam {self.title}>'


class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # mcq, true_false, short_answer, essay
    marks = db.Column(db.Integer, default=1)
    order = db.Column(db.Integer, default=0)
    
    # For MCQ
    option_a = db.Column(db.Text)
    option_b = db.Column(db.Text)
    option_c = db.Column(db.Text)
    option_d = db.Column(db.Text)
    correct_answer = db.Column(db.String(255))  # For MCQ: 'A', 'B', 'C', 'D'; For True/False: 'True' or 'False'
    
    # For short answer/essay - keywords for auto-grading
    keywords = db.Column(db.Text)  # JSON string of keywords
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Question {self.id} - {self.question_type}>'


class Attempt(db.Model):
    __tablename__ = 'attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    
    attempt_number = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, submitted, graded
    
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    
    total_score = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    
    # Relationships
    answers = db.relationship('Answer', backref='attempt', lazy=True, cascade='all, delete-orphan')
    result = db.relationship('Result', backref='attempt', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Attempt {self.id} - Student {self.student_id}>'


class Answer(db.Model):
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    
    answer_text = db.Column(db.Text)
    is_correct = db.Column(db.Boolean)
    marks_obtained = db.Column(db.Float, default=0.0)
    
    graded = db.Column(db.Boolean, default=False)
    graded_at = db.Column(db.DateTime)
    teacher_feedback = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    question = db.relationship('Question', backref='answers')
    
    def __repr__(self):
        return f'<Answer {self.id} - Question {self.question_id}>'


class Result(db.Model):
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempts.id'), nullable=False, unique=True)
    
    total_marks = db.Column(db.Float, nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(5))  # A, B, C, D, F
    remarks = db.Column(db.String(50))  # Excellent, Good, Pass, Fail
    
    published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime)
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_grade(self):
        """Calculate grade based on percentage"""
        if self.percentage >= 75:
            self.grade = 'A'
            self.remarks = 'Excellent'
        elif self.percentage >= 60:
            self.grade = 'B'
            self.remarks = 'Very Good'
        elif self.percentage >= 50:
            self.grade = 'C'
            self.remarks = 'Good'
        elif self.percentage >= 40:
            self.grade = 'D'
            self.remarks = 'Pass'
        else:
            self.grade = 'F'
            self.remarks = 'Fail'
    
    def __repr__(self):
        return f'<Result {self.id} - {self.percentage}%>'