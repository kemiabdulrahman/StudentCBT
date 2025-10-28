"""
Test forms
"""
import pytest
from forms import (
    LoginForm, SchoolClassForm, SubjectForm, StudentUploadForm,
    ExamForm, QuestionForm, QuestionUploadForm, EmptyForm
)
from models import SchoolClass, Subject


class TestLoginForm:
    """Test LoginForm"""

    def test_valid_login_form(self, app):
        """Test valid login form"""
        with app.test_request_context():
            form = LoginForm(data={
                'email': 'test@example.com',
                'password': 'password123'
            })
            assert form.validate() is True

    def test_missing_email(self, app):
        """Test login form with missing email"""
        with app.test_request_context():
            form = LoginForm(data={
                'password': 'password123'
            })
            assert form.validate() is False
            assert 'email' in form.errors

    def test_invalid_email(self, app):
        """Test login form with invalid email"""
        with app.test_request_context():
            form = LoginForm(data={
                'email': 'notanemail',
                'password': 'password123'
            })
            assert form.validate() is False
            assert 'email' in form.errors

    def test_missing_password(self, app):
        """Test login form with missing password"""
        with app.test_request_context():
            form = LoginForm(data={
                'email': 'test@example.com'
            })
            assert form.validate() is False
            assert 'password' in form.errors


class TestSchoolClassForm:
    """Test SchoolClassForm"""

    def test_valid_class_form(self, app):
        """Test valid class form"""
        with app.test_request_context():
            form = SchoolClassForm(data={
                'name': 'JSS 1A',
                'level': 'JSS1'
            })
            assert form.validate() is True

    def test_missing_name(self, app):
        """Test class form with missing name"""
        with app.test_request_context():
            form = SchoolClassForm(data={
                'level': 'JSS1'
            })
            assert form.validate() is False
            assert 'name' in form.errors

    def test_name_too_long(self, app):
        """Test class form with name too long"""
        with app.test_request_context():
            form = SchoolClassForm(data={
                'name': 'A' * 51,  # Max is 50
                'level': 'JSS1'
            })
            assert form.validate() is False

    def test_level_optional(self, app):
        """Test that level is optional"""
        with app.test_request_context():
            form = SchoolClassForm(data={
                'name': 'JSS 1A'
            })
            assert form.validate() is True


class TestSubjectForm:
    """Test SubjectForm"""

    def test_valid_subject_form(self, app, _db, school_class):
        """Test valid subject form"""
        with app.test_request_context():
            form = SubjectForm(data={
                'name': 'Mathematics',
                'code': 'MATH101',
                'class_id': school_class.id
            })
            assert form.validate() is True

    def test_missing_name(self, app, _db, school_class):
        """Test subject form with missing name"""
        with app.test_request_context():
            form = SubjectForm(data={
                'code': 'MATH101',
                'class_id': school_class.id
            })
            assert form.validate() is False
            assert 'name' in form.errors

    def test_missing_class_id(self, app, _db):
        """Test subject form with missing class_id"""
        with app.test_request_context():
            form = SubjectForm(data={
                'name': 'Mathematics',
                'code': 'MATH101'
            })
            assert form.validate() is False
            assert 'class_id' in form.errors

    def test_code_optional(self, app, _db, school_class):
        """Test that code is optional"""
        with app.test_request_context():
            form = SubjectForm(data={
                'name': 'Mathematics',
                'class_id': school_class.id
            })
            assert form.validate() is True


class TestExamForm:
    """Test ExamForm"""

    def test_valid_exam_form(self, app, _db, subject, school_class):
        """Test valid exam form"""
        with app.test_request_context():
            form = ExamForm(data={
                'title': 'Mid-Term Exam',
                'description': 'Test exam',
                'subject_id': subject.id,
                'class_id': school_class.id,
                'duration_minutes': 60,
                'pass_mark': 40
            })
            assert form.validate() is True

    def test_missing_title(self, app, _db, subject, school_class):
        """Test exam form with missing title"""
        with app.test_request_context():
            form = ExamForm(data={
                'subject_id': subject.id,
                'class_id': school_class.id,
                'duration_minutes': 60,
                'pass_mark': 40
            })
            assert form.validate() is False
            assert 'title' in form.errors

    def test_invalid_duration(self, app, _db, subject, school_class):
        """Test exam form with invalid duration"""
        with app.test_request_context():
            form = ExamForm(data={
                'title': 'Test Exam',
                'subject_id': subject.id,
                'class_id': school_class.id,
                'duration_minutes': 0,  # Must be >= 1
                'pass_mark': 40
            })
            assert form.validate() is False

    def test_invalid_pass_mark_too_high(self, app, _db, subject, school_class):
        """Test exam form with pass mark too high"""
        with app.test_request_context():
            form = ExamForm(data={
                'title': 'Test Exam',
                'subject_id': subject.id,
                'class_id': school_class.id,
                'duration_minutes': 60,
                'pass_mark': 101  # Max is 100
            })
            assert form.validate() is False

    def test_description_optional(self, app, _db, subject, school_class):
        """Test that description is optional"""
        with app.test_request_context():
            form = ExamForm(data={
                'title': 'Test Exam',
                'subject_id': subject.id,
                'class_id': school_class.id,
                'duration_minutes': 60,
                'pass_mark': 40
            })
            assert form.validate() is True


class TestQuestionForm:
    """Test QuestionForm"""

    def test_valid_mcq_question_form(self, app):
        """Test valid MCQ question form"""
        with app.test_request_context():
            form = QuestionForm(data={
                'question_text': 'What is 2 + 2?',
                'question_type': 'mcq',
                'marks': 2,
                'option_a': '3',
                'option_b': '4',
                'option_c': '5',
                'option_d': '6',
                'correct_answer': 'B'
            })
            assert form.validate() is True

    def test_valid_true_false_question_form(self, app):
        """Test valid True/False question form"""
        with app.test_request_context():
            form = QuestionForm(data={
                'question_text': 'The earth is round.',
                'question_type': 'true_false',
                'marks': 1,
                'correct_answer': 'True'
            })
            assert form.validate() is True

    def test_missing_question_text(self, app):
        """Test question form with missing text"""
        with app.test_request_context():
            form = QuestionForm(data={
                'question_type': 'mcq',
                'marks': 2,
                'correct_answer': 'A'
            })
            assert form.validate() is False
            assert 'question_text' in form.errors

    def test_invalid_marks(self, app):
        """Test question form with invalid marks"""
        with app.test_request_context():
            form = QuestionForm(data={
                'question_text': 'Test question?',
                'question_type': 'mcq',
                'marks': 0,  # Must be >= 1
                'correct_answer': 'A'
            })
            assert form.validate() is False


class TestQuestionUploadForm:
    """Test QuestionUploadForm"""

    def test_form_exists(self, app):
        """Test that QuestionUploadForm exists"""
        with app.test_request_context():
            form = QuestionUploadForm()
            assert form is not None


class TestEmptyForm:
    """Test EmptyForm"""

    def test_empty_form_validates(self, app):
        """Test that EmptyForm always validates"""
        with app.test_request_context():
            form = EmptyForm()
            assert form.validate() is True
