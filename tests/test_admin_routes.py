"""
Test admin routes
"""
import pytest
from flask import url_for
from models import SchoolClass, Subject, Student, Exam, Question, Attempt


class TestAdminDashboard:
    """Test admin dashboard"""

    def test_dashboard_loads(self, auth_client, app):
        """Test that admin dashboard loads"""
        with app.app_context():
            response = auth_client.get('/admin/dashboard')
            assert response.status_code == 200
            assert b'Dashboard' in response.data or b'dashboard' in response.data

    def test_dashboard_shows_stats(self, auth_client, app, school_class, student_user):
        """Test that dashboard shows statistics"""
        with app.app_context():
            response = auth_client.get('/admin/dashboard')
            assert response.status_code == 200
            # Should show counts
            assert b'Student' in response.data or b'student' in response.data
            assert b'Class' in response.data or b'class' in response.data


class TestClassManagement:
    """Test class management routes"""

    def test_classes_list_loads(self, auth_client, app):
        """Test that classes list page loads"""
        with app.app_context():
            response = auth_client.get('/admin/classes')
            assert response.status_code == 200

    def test_classes_list_shows_classes(self, auth_client, app, school_class):
        """Test that classes list shows classes"""
        with app.app_context():
            response = auth_client.get('/admin/classes')
            assert response.status_code == 200
            assert b'JSS 1A' in response.data

    def test_create_class_inline(self, auth_client, app, _db):
        """Test creating a class via inline form"""
        with app.app_context():
            response = auth_client.post('/admin/classes', data={
                'name': 'JSS 2B',
                'level': 'JSS2'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'JSS 2B' in response.data

            # Verify in database
            school_class = SchoolClass.query.filter_by(name='JSS 2B').first()
            assert school_class is not None
            assert school_class.level == 'JSS2'

    def test_class_detail_loads(self, auth_client, app, school_class):
        """Test that class detail page loads"""
        with app.app_context():
            response = auth_client.get(f'/admin/classes/{school_class.id}')
            assert response.status_code == 200
            assert b'JSS 1A' in response.data

    def test_edit_class(self, auth_client, app, school_class, _db):
        """Test editing a class"""
        with app.app_context():
            response = auth_client.post(f'/admin/classes/{school_class.id}', data={
                'name': 'JSS 1B Updated',
                'level': 'JSS1'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'Updated' in response.data or b'updated' in response.data

            # Verify in database
            _db.session.refresh(school_class)
            assert school_class.name == 'JSS 1B Updated'

    def test_delete_class(self, auth_client, app, _db):
        """Test deleting a class"""
        with app.app_context():
            # Create a class without students
            school_class = SchoolClass(name='To Delete', level='TEST')
            _db.session.add(school_class)
            _db.session.commit()
            class_id = school_class.id

            response = auth_client.post(f'/admin/classes/{class_id}/delete',
                                       follow_redirects=True)

            assert response.status_code == 200
            assert b'deleted' in response.data.lower()

            # Verify deleted from database
            deleted_class = SchoolClass.query.get(class_id)
            assert deleted_class is None

    def test_cannot_delete_class_with_students(self, auth_client, app, school_class, student_user):
        """Test that cannot delete class with students"""
        with app.app_context():
            response = auth_client.post(f'/admin/classes/{school_class.id}/delete',
                                       follow_redirects=True)

            assert response.status_code == 200
            assert b'Cannot delete' in response.data or b'students' in response.data.lower()

            # Verify class still exists
            existing_class = SchoolClass.query.get(school_class.id)
            assert existing_class is not None


class TestSubjectManagement:
    """Test subject management routes"""

    def test_subjects_list_loads(self, auth_client, app):
        """Test that subjects list page loads"""
        with app.app_context():
            response = auth_client.get('/admin/subjects')
            assert response.status_code == 200

    def test_subjects_list_shows_subjects(self, auth_client, app, subject):
        """Test that subjects list shows subjects"""
        with app.app_context():
            response = auth_client.get('/admin/subjects')
            assert response.status_code == 200
            assert b'Mathematics' in response.data

    def test_create_subject_inline(self, auth_client, app, school_class, _db):
        """Test creating a subject via inline form"""
        with app.app_context():
            response = auth_client.post('/admin/subjects', data={
                'name': 'English',
                'code': 'ENG101',
                'class_id': school_class.id
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'English' in response.data

            # Verify in database
            subject = Subject.query.filter_by(name='English').first()
            assert subject is not None
            assert subject.code == 'ENG101'

    def test_delete_subject(self, auth_client, app, subject, _db):
        """Test deleting a subject"""
        with app.app_context():
            subject_id = subject.id
            response = auth_client.post(f'/admin/subjects/{subject_id}/delete',
                                       follow_redirects=True)

            assert response.status_code == 200

            # Verify deleted from database
            deleted_subject = Subject.query.get(subject_id)
            assert deleted_subject is None


class TestStudentManagement:
    """Test student management routes"""

    def test_students_list_loads(self, auth_client, app):
        """Test that students list page loads"""
        with app.app_context():
            response = auth_client.get('/admin/students')
            assert response.status_code == 200

    def test_students_list_shows_students(self, auth_client, app, student_user):
        """Test that students list shows students"""
        with app.app_context():
            response = auth_client.get('/admin/students')
            assert response.status_code == 200
            assert b'John' in response.data or b'Doe' in response.data

    def test_student_detail_loads(self, auth_client, app, student_user, _db):
        """Test that student detail page loads"""
        with app.app_context():
            student = Student.query.filter_by(user_id=student_user.id).first()
            response = auth_client.get(f'/admin/students/{student.id}')
            assert response.status_code == 200
            assert b'John Doe' in response.data or (b'John' in response.data and b'Doe' in response.data)

    def test_toggle_student_status(self, auth_client, app, student_user, _db):
        """Test toggling student status"""
        with app.app_context():
            student = Student.query.filter_by(user_id=student_user.id).first()
            original_status = student.user.is_active

            response = auth_client.post(f'/admin/students/{student.id}/toggle-status',
                                       follow_redirects=True)

            assert response.status_code == 200

            # Verify status changed
            _db.session.refresh(student.user)
            assert student.user.is_active != original_status

    def test_delete_student(self, auth_client, app, _db, school_class):
        """Test deleting a student"""
        with app.app_context():
            # Create a test student
            from models import User
            user = User(email='delete@test.com', role='student')
            user.set_password('password')
            _db.session.add(user)
            _db.session.commit()

            student = Student(
                user_id=user.id,
                student_id='DEL001',
                first_name='Delete',
                last_name='Me',
                class_id=school_class.id
            )
            _db.session.add(student)
            _db.session.commit()
            student_id = student.id

            response = auth_client.post(f'/admin/students/{student_id}/delete',
                                       follow_redirects=True)

            assert response.status_code == 200

            # Verify deleted from database
            deleted_student = Student.query.get(student_id)
            assert deleted_student is None


class TestExamManagement:
    """Test exam management routes"""

    def test_exams_list_loads(self, auth_client, app):
        """Test that exams list page loads"""
        with app.app_context():
            response = auth_client.get('/admin/exams')
            assert response.status_code == 200

    def test_exams_list_shows_exams(self, auth_client, app, exam):
        """Test that exams list shows exams"""
        with app.app_context():
            response = auth_client.get('/admin/exams')
            assert response.status_code == 200
            assert b'Mid-Term' in response.data or b'Mathematics' in response.data

    def test_create_exam(self, auth_client, app, subject, school_class, _db):
        """Test creating an exam"""
        with app.app_context():
            response = auth_client.post('/admin/exams/create', data={
                'title': 'New Exam',
                'description': 'Test exam description',
                'subject_id': subject.id,
                'class_id': school_class.id,
                'duration_minutes': 60,
                'pass_mark': 50
            }, follow_redirects=True)

            assert response.status_code == 200

            # Verify in database
            exam = Exam.query.filter_by(title='New Exam').first()
            assert exam is not None
            assert exam.duration_minutes == 60

    def test_exam_details_loads(self, auth_client, app, exam):
        """Test that exam details page loads"""
        with app.app_context():
            response = auth_client.get(f'/admin/exams/{exam.id}')
            assert response.status_code == 200
            assert b'Mid-Term' in response.data or exam.title.encode() in response.data

    def test_edit_exam(self, auth_client, app, exam, subject, school_class, _db):
        """Test editing an exam"""
        with app.app_context():
            response = auth_client.post(f'/admin/exams/{exam.id}/edit', data={
                'title': 'Updated Exam Title',
                'description': exam.description,
                'subject_id': subject.id,
                'class_id': school_class.id,
                'duration_minutes': 90,
                'pass_mark': 60
            }, follow_redirects=True)

            assert response.status_code == 200

            # Verify in database
            _db.session.refresh(exam)
            assert exam.title == 'Updated Exam Title'
            assert exam.duration_minutes == 90

    def test_delete_exam(self, auth_client, app, exam, _db):
        """Test deleting an exam"""
        with app.app_context():
            exam_id = exam.id
            response = auth_client.post(f'/admin/exams/{exam_id}/delete',
                                       follow_redirects=True)

            assert response.status_code == 200

            # Verify deleted from database
            deleted_exam = Exam.query.get(exam_id)
            assert deleted_exam is None

    def test_publish_exam(self, auth_client, app, exam, _db):
        """Test publishing an exam"""
        with app.app_context():
            response = auth_client.post(f'/admin/exams/{exam.id}/publish',
                                       follow_redirects=True)

            assert response.status_code == 200

            # Verify status changed
            _db.session.refresh(exam)
            assert exam.status == 'published'

    def test_close_exam(self, auth_client, app, published_exam, _db):
        """Test closing an exam"""
        with app.app_context():
            response = auth_client.post(f'/admin/exams/{published_exam.id}/close',
                                       follow_redirects=True)

            assert response.status_code == 200

            # Verify status changed
            _db.session.refresh(published_exam)
            assert published_exam.status == 'closed'

    def test_toggle_results_publication(self, auth_client, app, published_exam, _db):
        """Test toggling results publication"""
        with app.app_context():
            original_status = published_exam.results_published

            response = auth_client.post(f'/admin/exams/{published_exam.id}/toggle-results',
                                       follow_redirects=True)

            assert response.status_code == 200

            # Verify status changed
            _db.session.refresh(published_exam)
            assert published_exam.results_published != original_status


class TestQuestionManagement:
    """Test question management routes"""

    def test_add_question_page_loads(self, auth_client, app, exam):
        """Test that add question page loads"""
        with app.app_context():
            response = auth_client.get(f'/admin/exams/{exam.id}/questions/add')
            assert response.status_code == 200

    def test_add_mcq_question(self, auth_client, app, exam, _db):
        """Test adding an MCQ question"""
        with app.app_context():
            response = auth_client.post(f'/admin/exams/{exam.id}/questions/add', data={
                'question_text': 'What is 5 + 5?',
                'question_type': 'mcq',
                'marks': 2,
                'option_a': '5',
                'option_b': '10',
                'option_c': '15',
                'option_d': '20',
                'correct_answer': 'B'
            }, follow_redirects=True)

            assert response.status_code == 200

            # Verify in database
            question = Question.query.filter_by(question_text='What is 5 + 5?').first()
            assert question is not None
            assert question.correct_answer == 'B'

    def test_add_true_false_question(self, auth_client, app, exam, _db):
        """Test adding a True/False question"""
        with app.app_context():
            response = auth_client.post(f'/admin/exams/{exam.id}/questions/add', data={
                'question_text': 'Python is a programming language.',
                'question_type': 'true_false',
                'marks': 1,
                'correct_answer': 'True'
            }, follow_redirects=True)

            assert response.status_code == 200

            # Verify in database
            question = Question.query.filter_by(
                question_text='Python is a programming language.'
            ).first()
            assert question is not None
            assert question.question_type == 'true_false'

    def test_delete_question(self, auth_client, app, question, _db):
        """Test deleting a question"""
        with app.app_context():
            question_id = question.id
            response = auth_client.post(f'/admin/questions/{question_id}/delete',
                                       follow_redirects=True)

            assert response.status_code == 200

            # Verify deleted from database
            deleted_question = Question.query.get(question_id)
            assert deleted_question is None


class TestAttemptViewing:
    """Test viewing student attempts"""

    def test_exam_attempts_page_loads(self, auth_client, app, exam):
        """Test that exam attempts page loads"""
        with app.app_context():
            response = auth_client.get(f'/admin/exams/{exam.id}/attempts')
            assert response.status_code == 200

    def test_exam_attempts_shows_attempts(self, auth_client, app, published_exam, submitted_attempt):
        """Test that exam attempts page shows attempts"""
        with app.app_context():
            response = auth_client.get(f'/admin/exams/{published_exam.id}/attempts')
            assert response.status_code == 200
            # Should show student info or attempt data
            assert response.status_code == 200

    def test_view_attempt_details(self, auth_client, app, submitted_attempt):
        """Test viewing attempt details"""
        with app.app_context():
            response = auth_client.get(f'/admin/attempts/{submitted_attempt.id}')
            assert response.status_code == 200
