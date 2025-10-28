"""
Test configuration and fixtures
"""
import pytest
import os
import tempfile
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, Student, SchoolClass, Subject, Exam, Question, Attempt, Answer
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()

    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'SERVER_NAME': 'localhost.localdomain'
    }

    app = create_app()
    app.config.update(test_config)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create a test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def _db(app):
    """Create database tables for each test"""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def admin_user(app, _db):
    """Create an admin user"""
    user = User(
        email='admin@test.com',
        password_hash=generate_password_hash('password123'),
        role='admin',
        is_active=True
    )
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def student_user(app, _db, school_class):
    """Create a student user"""
    user = User(
        email='student@test.com',
        password_hash=generate_password_hash('password123'),
        role='student',
        is_active=True
    )
    _db.session.add(user)
    _db.session.commit()

    student = Student(
        user_id=user.id,
        student_id='STU001',
        first_name='John',
        last_name='Doe',
        class_id=school_class.id
    )
    _db.session.add(student)
    _db.session.commit()

    return user


@pytest.fixture
def inactive_student_user(app, _db, school_class):
    """Create an inactive student user"""
    user = User(
        email='inactive@test.com',
        password_hash=generate_password_hash('password123'),
        role='student',
        is_active=False
    )
    _db.session.add(user)
    _db.session.commit()

    student = Student(
        user_id=user.id,
        student_id='STU002',
        first_name='Jane',
        last_name='Smith',
        class_id=school_class.id
    )
    _db.session.add(student)
    _db.session.commit()

    return user


@pytest.fixture
def school_class(app, _db):
    """Create a school class"""
    school_class = SchoolClass(
        name='JSS 1A',
        level='JSS1'
    )
    _db.session.add(school_class)
    _db.session.commit()
    return school_class


@pytest.fixture
def subject(app, _db, school_class):
    """Create a subject"""
    subject = Subject(
        name='Mathematics',
        code='MATH101',
        class_id=school_class.id
    )
    _db.session.add(subject)
    _db.session.commit()
    return subject


@pytest.fixture
def exam(app, _db, subject, school_class):
    """Create an exam"""
    exam = Exam(
        title='Mid-Term Mathematics Exam',
        description='First term mathematics exam',
        subject_id=subject.id,
        class_id=school_class.id,
        duration_minutes=60,
        total_marks=0,
        pass_mark=40,
        status='draft'
    )
    _db.session.add(exam)
    _db.session.commit()
    return exam


@pytest.fixture
def published_exam(app, _db, subject, school_class):
    """Create a published exam"""
    exam = Exam(
        title='Published Exam',
        description='Published exam for testing',
        subject_id=subject.id,
        class_id=school_class.id,
        duration_minutes=45,
        total_marks=10,
        pass_mark=50,
        status='published',
        results_published=False
    )
    _db.session.add(exam)
    _db.session.commit()
    return exam


@pytest.fixture
def exam_with_results_published(app, _db, subject, school_class):
    """Create an exam with results published"""
    exam = Exam(
        title='Exam with Published Results',
        description='Exam with results visible',
        subject_id=subject.id,
        class_id=school_class.id,
        duration_minutes=45,
        total_marks=10,
        pass_mark=50,
        status='published',
        results_published=True
    )
    _db.session.add(exam)
    _db.session.commit()
    return exam


@pytest.fixture
def question(app, _db, exam):
    """Create a question"""
    question = Question(
        exam_id=exam.id,
        question_text='What is 2 + 2?',
        question_type='mcq',
        marks=2,
        order=1,
        option_a='3',
        option_b='4',
        option_c='5',
        option_d='6',
        correct_answer='B'
    )
    _db.session.add(question)
    _db.session.commit()

    # Update exam total marks
    exam.total_marks = 2
    _db.session.commit()

    return question


@pytest.fixture
def true_false_question(app, _db, exam):
    """Create a true/false question"""
    question = Question(
        exam_id=exam.id,
        question_text='The earth is flat.',
        question_type='true_false',
        marks=1,
        order=2,
        correct_answer='False'
    )
    _db.session.add(question)
    _db.session.commit()

    # Update exam total marks
    exam.total_marks += 1
    _db.session.commit()

    return question


@pytest.fixture
def attempt(app, _db, exam, student_user):
    """Create an attempt"""
    student = Student.query.filter_by(user_id=student_user.id).first()
    attempt = Attempt(
        student_id=student.id,
        exam_id=exam.id,
        status='in_progress'
    )
    _db.session.add(attempt)
    _db.session.commit()
    return attempt


@pytest.fixture
def submitted_attempt(app, _db, published_exam, student_user, question):
    """Create a submitted attempt"""
    student = Student.query.filter_by(user_id=student_user.id).first()
    attempt = Attempt(
        student_id=student.id,
        exam_id=published_exam.id,
        status='submitted',
        submitted_at=datetime.utcnow(),
        total_score=2,
        percentage=100,
        grade='A'
    )
    _db.session.add(attempt)
    _db.session.commit()
    return attempt


@pytest.fixture
def answer(app, _db, attempt, question):
    """Create an answer"""
    answer = Answer(
        attempt_id=attempt.id,
        question_id=question.id,
        answer_text='B',
        is_correct=True
    )
    _db.session.add(answer)
    _db.session.commit()
    return answer


@pytest.fixture
def auth_client(client, admin_user):
    """Create an authenticated client with admin user"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    return client


@pytest.fixture
def student_auth_client(client, student_user):
    """Create an authenticated client with student user"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(student_user.id)
    return client


@pytest.fixture
def sample_excel_data():
    """Sample data for Excel upload testing"""
    return {
        'headers': ['student_id', 'first_name', 'last_name', 'email'],
        'rows': [
            ['STU001', 'John', 'Doe', 'john.doe@test.com'],
            ['STU002', 'Jane', 'Smith', 'jane.smith@test.com'],
            ['STU003', 'Bob', 'Johnson', 'bob.johnson@test.com']
        ]
    }
