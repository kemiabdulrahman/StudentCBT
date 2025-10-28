"""
Test models
"""
import pytest
from datetime import datetime
from models import User, Student, SchoolClass, Subject, Exam, Question, Attempt, Answer
from werkzeug.security import check_password_hash


class TestUser:
    """Test User model"""

    def test_create_user(self, app, _db):
        """Test creating a user"""
        user = User(
            email='test@example.com',
            role='admin'
        )
        user.set_password('password123')
        _db.session.add(user)
        _db.session.commit()

        assert user.id is not None
        assert user.email == 'test@example.com'
        assert user.role == 'admin'
        assert user.is_active is True
        assert user.password_hash is not None

    def test_set_password(self, app, _db):
        """Test password hashing"""
        user = User(email='test@example.com', role='admin')
        user.set_password('mypassword')

        assert user.password_hash is not None
        assert user.password_hash != 'mypassword'
        assert check_password_hash(user.password_hash, 'mypassword')

    def test_check_password(self, app, _db, admin_user):
        """Test password checking"""
        assert admin_user.check_password('password123') is True
        assert admin_user.check_password('wrongpassword') is False

    def test_user_repr(self, app, _db, admin_user):
        """Test user representation"""
        assert repr(admin_user) == '<User admin@test.com>'


class TestStudent:
    """Test Student model"""

    def test_create_student(self, app, _db, student_user, school_class):
        """Test creating a student"""
        student = Student.query.filter_by(user_id=student_user.id).first()

        assert student is not None
        assert student.student_id == 'STU001'
        assert student.first_name == 'John'
        assert student.last_name == 'Doe'
        assert student.class_id == school_class.id

    def test_student_full_name(self, app, _db, student_user):
        """Test student full name property"""
        student = Student.query.filter_by(user_id=student_user.id).first()
        assert student.full_name == 'John Doe'

    def test_student_relationships(self, app, _db, student_user, school_class):
        """Test student relationships"""
        student = Student.query.filter_by(user_id=student_user.id).first()

        assert student.user.email == 'student@test.com'
        assert student.school_class.name == 'JSS 1A'


class TestSchoolClass:
    """Test SchoolClass model"""

    def test_create_class(self, app, _db):
        """Test creating a class"""
        school_class = SchoolClass(name='JSS 2B', level='JSS2')
        _db.session.add(school_class)
        _db.session.commit()

        assert school_class.id is not None
        assert school_class.name == 'JSS 2B'
        assert school_class.level == 'JSS2'
        assert school_class.created_at is not None

    def test_class_students_relationship(self, app, _db, school_class, student_user):
        """Test class to students relationship"""
        assert len(school_class.students) == 1
        assert school_class.students[0].first_name == 'John'

    def test_class_subjects_relationship(self, app, _db, school_class, subject):
        """Test class to subjects relationship"""
        assert len(school_class.subjects) == 1
        assert school_class.subjects[0].name == 'Mathematics'


class TestSubject:
    """Test Subject model"""

    def test_create_subject(self, app, _db, school_class):
        """Test creating a subject"""
        subject = Subject(
            name='English',
            code='ENG101',
            class_id=school_class.id
        )
        _db.session.add(subject)
        _db.session.commit()

        assert subject.id is not None
        assert subject.name == 'English'
        assert subject.code == 'ENG101'

    def test_subject_class_relationship(self, app, _db, subject, school_class):
        """Test subject to class relationship"""
        assert subject.school_class.name == 'JSS 1A'

    def test_subject_exams_relationship(self, app, _db, subject, exam):
        """Test subject to exams relationship"""
        assert len(subject.exams) == 1
        assert subject.exams[0].title == 'Mid-Term Mathematics Exam'


class TestExam:
    """Test Exam model"""

    def test_create_exam(self, app, _db, subject, school_class):
        """Test creating an exam"""
        exam = Exam(
            title='Final Exam',
            description='End of term exam',
            subject_id=subject.id,
            class_id=school_class.id,
            duration_minutes=90,
            total_marks=100,
            pass_mark=50,
            status='draft'
        )
        _db.session.add(exam)
        _db.session.commit()

        assert exam.id is not None
        assert exam.title == 'Final Exam'
        assert exam.duration_minutes == 90
        assert exam.status == 'draft'
        assert exam.results_published is False

    def test_exam_results_published_default(self, app, _db, exam):
        """Test that results_published defaults to False"""
        assert exam.results_published is False

    def test_exam_relationships(self, app, _db, exam, subject, school_class):
        """Test exam relationships"""
        assert exam.subject.name == 'Mathematics'
        assert exam.school_class.name == 'JSS 1A'

    def test_exam_questions_relationship(self, app, _db, exam, question):
        """Test exam to questions relationship"""
        assert len(exam.questions) == 1
        assert exam.questions[0].question_text == 'What is 2 + 2?'


class TestQuestion:
    """Test Question model"""

    def test_create_mcq_question(self, app, _db, exam):
        """Test creating an MCQ question"""
        question = Question(
            exam_id=exam.id,
            question_text='What is the capital of France?',
            question_type='mcq',
            marks=1,
            order=1,
            option_a='London',
            option_b='Paris',
            option_c='Berlin',
            option_d='Madrid',
            correct_answer='B'
        )
        _db.session.add(question)
        _db.session.commit()

        assert question.id is not None
        assert question.question_type == 'mcq'
        assert question.option_b == 'Paris'
        assert question.correct_answer == 'B'

    def test_create_true_false_question(self, app, _db, exam):
        """Test creating a true/false question"""
        question = Question(
            exam_id=exam.id,
            question_text='Python is a programming language.',
            question_type='true_false',
            marks=1,
            order=1,
            correct_answer='True'
        )
        _db.session.add(question)
        _db.session.commit()

        assert question.id is not None
        assert question.question_type == 'true_false'
        assert question.correct_answer == 'True'

    def test_question_exam_relationship(self, app, _db, question, exam):
        """Test question to exam relationship"""
        assert question.exam.title == 'Mid-Term Mathematics Exam'


class TestAttempt:
    """Test Attempt model"""

    def test_create_attempt(self, app, _db, exam, student_user):
        """Test creating an attempt"""
        student = Student.query.filter_by(user_id=student_user.id).first()
        attempt = Attempt(
            student_id=student.id,
            exam_id=exam.id,
            status='in_progress'
        )
        _db.session.add(attempt)
        _db.session.commit()

        assert attempt.id is not None
        assert attempt.status == 'in_progress'
        assert attempt.total_score == 0.0
        assert attempt.percentage == 0.0
        assert attempt.started_at is not None

    def test_calculate_grade_a(self, app, _db, attempt):
        """Test grade calculation for A"""
        attempt.percentage = 80
        attempt.calculate_grade()
        assert attempt.grade == 'A'

    def test_calculate_grade_b(self, app, _db, attempt):
        """Test grade calculation for B"""
        attempt.percentage = 65
        attempt.calculate_grade()
        assert attempt.grade == 'B'

    def test_calculate_grade_c(self, app, _db, attempt):
        """Test grade calculation for C"""
        attempt.percentage = 55
        attempt.calculate_grade()
        assert attempt.grade == 'C'

    def test_calculate_grade_d(self, app, _db, attempt):
        """Test grade calculation for D"""
        attempt.percentage = 45
        attempt.calculate_grade()
        assert attempt.grade == 'D'

    def test_calculate_grade_f(self, app, _db, attempt):
        """Test grade calculation for F"""
        attempt.percentage = 30
        attempt.calculate_grade()
        assert attempt.grade == 'F'

    def test_attempt_relationships(self, app, _db, attempt, exam, student_user):
        """Test attempt relationships"""
        student = Student.query.filter_by(user_id=student_user.id).first()
        assert attempt.student.full_name == student.full_name
        assert attempt.exam.title == exam.title

    def test_unique_constraint(self, app, _db, exam, student_user):
        """Test unique constraint: one attempt per student per exam"""
        student = Student.query.filter_by(user_id=student_user.id).first()

        attempt1 = Attempt(student_id=student.id, exam_id=exam.id)
        _db.session.add(attempt1)
        _db.session.commit()

        # Try to create duplicate attempt
        attempt2 = Attempt(student_id=student.id, exam_id=exam.id)
        _db.session.add(attempt2)

        with pytest.raises(Exception):  # IntegrityError
            _db.session.commit()


class TestAnswer:
    """Test Answer model"""

    def test_create_answer(self, app, _db, attempt, question):
        """Test creating an answer"""
        answer = Answer(
            attempt_id=attempt.id,
            question_id=question.id,
            answer_text='B',
            is_correct=True
        )
        _db.session.add(answer)
        _db.session.commit()

        assert answer.id is not None
        assert answer.answer_text == 'B'
        assert answer.is_correct is True

    def test_answer_relationships(self, app, _db, answer, attempt, question):
        """Test answer relationships"""
        assert answer.attempt.id == attempt.id
        assert answer.question.question_text == 'What is 2 + 2?'
