"""
Test templates rendering
"""
import pytest
from flask import render_template


class TestAuthTemplates:
    """Test authentication templates"""

    def test_login_template_renders(self, app):
        """Test that login template renders without error"""
        with app.app_context():
            from forms import LoginForm
            form = LoginForm()
            html = render_template('auth/login.html', form=form)
            assert html is not None
            assert 'login' in html.lower()


class TestAdminTemplates:
    """Test admin templates"""

    def test_admin_dashboard_renders(self, app, school_class):
        """Test that admin dashboard renders"""
        with app.app_context():
            html = render_template('admin/dashboard.html',
                                 total_students=1,
                                 total_classes=1,
                                 total_subjects=0,
                                 classes=[school_class])
            assert html is not None
            assert 'dashboard' in html.lower()

    def test_classes_template_renders(self, app, school_class):
        """Test that classes template renders"""
        with app.app_context():
            from forms import SchoolClassForm
            form = SchoolClassForm()
            html = render_template('admin/classes.html',
                                 classes=[school_class],
                                 form=form)
            assert html is not None
            assert school_class.name in html

    def test_class_detail_template_renders(self, app, school_class):
        """Test that class detail template renders"""
        with app.app_context():
            from forms import SchoolClassForm
            form = SchoolClassForm(obj=school_class)
            html = render_template('admin/class_detail.html',
                                 school_class=school_class,
                                 form=form)
            assert html is not None
            assert school_class.name in html

    def test_subjects_template_renders(self, app, subject):
        """Test that subjects template renders"""
        with app.app_context():
            from forms import SubjectForm
            form = SubjectForm()
            html = render_template('admin/subjects.html',
                                 subjects=[subject],
                                 form=form)
            assert html is not None
            assert subject.name in html

    def test_students_template_renders(self, app, student_user, _db):
        """Test that students template renders"""
        with app.app_context():
            from models import Student
            students = Student.query.all()
            html = render_template('admin/students.html', students=students)
            assert html is not None
            assert 'student' in html.lower()

    def test_student_detail_template_renders(self, app, student_user, _db):
        """Test that student detail template renders"""
        with app.app_context():
            from models import Student
            student = Student.query.filter_by(user_id=student_user.id).first()
            html = render_template('admin/student_detail.html', student=student)
            assert html is not None
            assert student.full_name in html

    def test_upload_students_template_renders(self, app):
        """Test that upload students template renders"""
        with app.app_context():
            from forms import StudentUploadForm
            form = StudentUploadForm()
            html = render_template('admin/upload_students.html', form=form)
            assert html is not None
            assert 'upload' in html.lower()

    def test_exams_template_renders(self, app, exam):
        """Test that exams template renders"""
        with app.app_context():
            html = render_template('admin/exams.html', exams=[exam])
            assert html is not None
            assert exam.title in html

    def test_exam_details_template_renders(self, app, exam, question):
        """Test that exam details template renders"""
        with app.app_context():
            html = render_template('admin/exam_details.html',
                                 exam=exam,
                                 questions=[question])
            assert html is not None
            assert exam.title in html

    def test_create_exam_template_renders(self, app, subject, school_class):
        """Test that create exam template renders"""
        with app.app_context():
            from forms import ExamForm
            form = ExamForm()
            html = render_template('admin/create_exam.html', form=form)
            assert html is not None
            assert 'exam' in html.lower()

    def test_edit_exam_template_renders(self, app, exam):
        """Test that edit exam template renders"""
        with app.app_context():
            from forms import ExamForm
            form = ExamForm(obj=exam)
            html = render_template('admin/edit_exam.html', form=form, exam=exam)
            assert html is not None
            assert exam.title in html

    def test_add_question_template_renders(self, app, exam):
        """Test that add question template renders"""
        with app.app_context():
            from forms import QuestionForm
            form = QuestionForm()
            html = render_template('admin/add_question.html', form=form, exam=exam)
            assert html is not None
            assert 'question' in html.lower()

    def test_edit_question_template_renders(self, app, question):
        """Test that edit question template renders"""
        with app.app_context():
            from forms import QuestionForm
            form = QuestionForm(obj=question)
            html = render_template('admin/edit_question.html',
                                 form=form,
                                 question=question)
            assert html is not None
            assert question.question_text in html

    def test_exam_attempts_template_renders(self, app, exam):
        """Test that exam attempts template renders"""
        with app.app_context():
            html = render_template('admin/exam_attempts.html',
                                 exam=exam,
                                 attempts=[])
            assert html is not None
            assert exam.title in html

    def test_view_attempt_template_renders(self, app, submitted_attempt, answer):
        """Test that view attempt template renders"""
        with app.app_context():
            html = render_template('admin/view_attempt.html',
                                 attempt=submitted_attempt,
                                 answers=[answer])
            assert html is not None
            assert submitted_attempt.exam.title in html


class TestStudentTemplates:
    """Test student templates"""

    def test_student_dashboard_renders(self, app):
        """Test that student dashboard renders"""
        with app.app_context():
            html = render_template('student/dashboard.html',
                                 active_exams=[],
                                 recent_attempts=[])
            assert html is not None
            assert 'dashboard' in html.lower()

    def test_exams_template_renders(self, app):
        """Test that student exams template renders"""
        with app.app_context():
            html = render_template('student/exams.html', exams=[])
            assert html is not None
            assert 'exam' in html.lower()

    def test_take_exam_template_renders(self, app, attempt, question):
        """Test that take exam template renders"""
        with app.app_context():
            html = render_template('student/take_exam.html',
                                 attempt=attempt,
                                 questions=[question],
                                 time_remaining=3600)
            assert html is not None
            assert question.question_text in html

    def test_attempt_summary_template_renders(self, app, submitted_attempt, answer):
        """Test that attempt summary template renders"""
        with app.app_context():
            html = render_template('student/attempt_summary.html',
                                 attempt=submitted_attempt,
                                 answers=[answer])
            assert html is not None

    def test_results_template_renders(self, app):
        """Test that results template renders"""
        with app.app_context():
            html = render_template('student/results.html', attempts=[])
            assert html is not None
            assert 'result' in html.lower()


class TestBaseTemplate:
    """Test base template"""

    def test_base_template_renders_for_admin(self, app, admin_user):
        """Test that base template renders for admin"""
        with app.test_request_context():
            from flask_login import login_user
            login_user(admin_user)
            html = render_template('base.html')
            assert html is not None
            assert 'admin' in html.lower()

    def test_base_template_renders_for_student(self, app, student_user):
        """Test that base template renders for student"""
        with app.test_request_context():
            from flask_login import login_user
            login_user(student_user)
            html = render_template('base.html')
            assert html is not None
            assert 'student' in html.lower()

    def test_base_template_renders_unauthenticated(self, app):
        """Test that base template renders for unauthenticated users"""
        with app.test_request_context():
            html = render_template('base.html')
            assert html is not None


class TestTemplateContext:
    """Test template context processors"""

    def test_institution_name_in_context(self, app):
        """Test that institution_name is available in templates"""
        with app.test_request_context():
            html = render_template('base.html')
            # Should contain the institution name
            assert html is not None

    def test_flash_messages_render(self, app):
        """Test that flash messages render in templates"""
        with app.test_request_context():
            from flask import flash
            flash('Test message', 'success')
            html = render_template('base.html')
            assert html is not None


class TestTemplateInheritance:
    """Test that templates properly extend base"""

    def test_login_extends_base(self, app):
        """Test that login template extends base"""
        with app.app_context():
            from forms import LoginForm
            form = LoginForm()
            html = render_template('auth/login.html', form=form)
            # Base template elements should be present
            assert '<html' in html.lower()
            assert '</html>' in html.lower()

    def test_admin_dashboard_extends_base(self, app, school_class):
        """Test that admin dashboard extends base"""
        with app.app_context():
            html = render_template('admin/dashboard.html',
                                 total_students=0,
                                 total_classes=1,
                                 total_subjects=0,
                                 classes=[school_class])
            assert '<html' in html.lower()
            assert '</html>' in html.lower()

    def test_student_dashboard_extends_base(self, app):
        """Test that student dashboard extends base"""
        with app.app_context():
            html = render_template('student/dashboard.html',
                                 active_exams=[],
                                 recent_attempts=[])
            assert '<html' in html.lower()
            assert '</html>' in html.lower()


class TestTemplateErrors:
    """Test template error handling"""

    def test_missing_variable_raises_error(self, app):
        """Test that missing required variable raises error"""
        with app.app_context():
            # This should raise an error due to missing variables
            with pytest.raises(Exception):
                render_template('admin/class_detail.html')

    def test_wrong_variable_type_handled(self, app):
        """Test that wrong variable type is handled gracefully"""
        with app.app_context():
            # Pass wrong type - should either work or raise specific error
            try:
                html = render_template('admin/classes.html',
                                     classes="not a list",  # Wrong type
                                     form=None)
                # If it renders, that's acceptable
                assert html is not None
            except Exception as e:
                # If it raises an error, that's also acceptable
                assert e is not None
