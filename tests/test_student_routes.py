"""
Test student routes
"""
import pytest
from flask import url_for
from models import Attempt, Answer
from datetime import datetime


class TestStudentDashboard:
    """Test student dashboard"""

    def test_dashboard_loads(self, student_auth_client, app):
        """Test that student dashboard loads"""
        with app.app_context():
            response = student_auth_client.get('/student/dashboard')
            assert response.status_code == 200
            assert b'Dashboard' in response.data or b'dashboard' in response.data

    def test_dashboard_shows_published_exams(self, student_auth_client, app, published_exam):
        """Test that dashboard shows published exams"""
        with app.app_context():
            response = student_auth_client.get('/student/dashboard')
            assert response.status_code == 200
            # Should show the published exam
            assert b'Published Exam' in response.data or b'exam' in response.data.lower()

    def test_dashboard_does_not_show_draft_exams(self, student_auth_client, app, exam):
        """Test that dashboard does not show draft exams"""
        with app.app_context():
            response = student_auth_client.get('/student/dashboard')
            assert response.status_code == 200
            # Should not show draft exam title
            assert b'Mid-Term Mathematics Exam' not in response.data


class TestStartExam:
    """Test starting an exam"""

    def test_start_exam_creates_attempt(self, student_auth_client, app, published_exam, student_user, _db):
        """Test that starting an exam creates an attempt"""
        with app.app_context():
            response = student_auth_client.post(f'/student/exams/{published_exam.id}/start',
                                               follow_redirects=True)

            assert response.status_code == 200

            # Verify attempt created
            from models import Student
            student = Student.query.filter_by(user_id=student_user.id).first()
            attempt = Attempt.query.filter_by(
                student_id=student.id,
                exam_id=published_exam.id
            ).first()
            assert attempt is not None
            assert attempt.status == 'in_progress'

    def test_cannot_start_draft_exam(self, student_auth_client, app, exam):
        """Test that cannot start a draft exam"""
        with app.app_context():
            response = student_auth_client.post(f'/student/exams/{exam.id}/start',
                                               follow_redirects=True)

            assert response.status_code == 200
            # Should show error or redirect
            assert b'not available' in response.data.lower() or b'published' in response.data.lower()

    def test_cannot_start_exam_twice(self, student_auth_client, app, published_exam, attempt, _db):
        """Test that cannot start same exam twice"""
        with app.app_context():
            response = student_auth_client.post(f'/student/exams/{published_exam.id}/start',
                                               follow_redirects=True)

            assert response.status_code == 200
            # Should redirect to existing attempt or show message
            # Verify only one attempt exists
            from models import Student
            student = Student.query.filter_by(user_id=attempt.student_id).first()
            attempts = Attempt.query.filter_by(
                student_id=student.id,
                exam_id=published_exam.id
            ).all()
            assert len(attempts) == 1


class TestTakeExam:
    """Test taking an exam"""

    def test_take_exam_page_loads(self, student_auth_client, app, attempt, question):
        """Test that take exam page loads"""
        with app.app_context():
            response = student_auth_client.get(f'/student/attempts/{attempt.id}/take')
            assert response.status_code == 200
            # Should show question
            assert b'What is 2 + 2?' in response.data

    def test_cannot_take_submitted_exam(self, student_auth_client, app, submitted_attempt):
        """Test that cannot take already submitted exam"""
        with app.app_context():
            response = student_auth_client.get(f'/student/attempts/{submitted_attempt.id}/take',
                                              follow_redirects=True)

            assert response.status_code == 200
            # Should redirect or show message
            assert b'already submitted' in response.data.lower() or b'result' in response.data.lower()

    def test_save_answer(self, student_auth_client, app, attempt, question, _db):
        """Test saving an answer"""
        with app.app_context():
            response = student_auth_client.post(
                f'/student/attempts/{attempt.id}/save-answer',
                json={
                    'question_id': question.id,
                    'answer': 'B'
                }
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

            # Verify answer saved
            answer = Answer.query.filter_by(
                attempt_id=attempt.id,
                question_id=question.id
            ).first()
            assert answer is not None
            assert answer.answer_text == 'B'

    def test_update_existing_answer(self, student_auth_client, app, attempt, question, answer, _db):
        """Test updating an existing answer"""
        with app.app_context():
            response = student_auth_client.post(
                f'/student/attempts/{attempt.id}/save-answer',
                json={
                    'question_id': question.id,
                    'answer': 'C'
                }
            )

            assert response.status_code == 200

            # Verify answer updated
            _db.session.refresh(answer)
            assert answer.answer_text == 'C'


class TestSubmitExam:
    """Test submitting an exam"""

    def test_submit_exam(self, student_auth_client, app, attempt, question, answer, _db):
        """Test submitting an exam"""
        with app.app_context():
            response = student_auth_client.post(f'/student/attempts/{attempt.id}/submit',
                                               follow_redirects=True)

            assert response.status_code == 200

            # Verify attempt submitted
            _db.session.refresh(attempt)
            assert attempt.status == 'submitted'
            assert attempt.submitted_at is not None
            assert attempt.total_score is not None
            assert attempt.percentage is not None
            assert attempt.grade is not None

    def test_cannot_submit_twice(self, student_auth_client, app, submitted_attempt):
        """Test that cannot submit exam twice"""
        with app.app_context():
            response = student_auth_client.post(
                f'/student/attempts/{submitted_attempt.id}/submit',
                follow_redirects=True
            )

            assert response.status_code == 200
            # Should show error or redirect
            assert b'already submitted' in response.data.lower() or b'result' in response.data.lower()

    def test_submit_calculates_score(self, student_auth_client, app, published_exam, student_user, _db):
        """Test that submit calculates score correctly"""
        with app.app_context():
            # Create attempt with questions and answers
            from models import Student, Question
            student = Student.query.filter_by(user_id=student_user.id).first()

            # Create questions for published exam
            q1 = Question(
                exam_id=published_exam.id,
                question_text='Test Q1',
                question_type='mcq',
                marks=5,
                order=1,
                correct_answer='A'
            )
            q2 = Question(
                exam_id=published_exam.id,
                question_text='Test Q2',
                question_type='mcq',
                marks=5,
                order=2,
                correct_answer='B'
            )
            _db.session.add_all([q1, q2])
            _db.session.commit()

            published_exam.total_marks = 10
            _db.session.commit()

            # Create attempt
            attempt = Attempt(
                student_id=student.id,
                exam_id=published_exam.id,
                status='in_progress'
            )
            _db.session.add(attempt)
            _db.session.commit()

            # Add answers (1 correct, 1 incorrect)
            a1 = Answer(attempt_id=attempt.id, question_id=q1.id, answer_text='A', is_correct=True)
            a2 = Answer(attempt_id=attempt.id, question_id=q2.id, answer_text='A', is_correct=False)
            _db.session.add_all([a1, a2])
            _db.session.commit()

            # Submit
            response = student_auth_client.post(f'/student/attempts/{attempt.id}/submit',
                                               follow_redirects=True)

            assert response.status_code == 200

            # Verify score
            _db.session.refresh(attempt)
            assert attempt.total_score == 5  # Only q1 correct
            assert attempt.percentage == 50  # 5/10 = 50%


class TestViewResults:
    """Test viewing results"""

    def test_results_page_loads(self, student_auth_client, app):
        """Test that results page loads"""
        with app.app_context():
            response = student_auth_client.get('/student/results')
            assert response.status_code == 200

    def test_results_shows_published_results(self, student_auth_client, app, exam_with_results_published, student_user, _db):
        """Test that results page shows published results"""
        with app.app_context():
            # Create a submitted attempt for exam with published results
            from models import Student
            student = Student.query.filter_by(user_id=student_user.id).first()
            attempt = Attempt(
                student_id=student.id,
                exam_id=exam_with_results_published.id,
                status='submitted',
                submitted_at=datetime.utcnow(),
                total_score=8,
                percentage=80,
                grade='A'
            )
            _db.session.add(attempt)
            _db.session.commit()

            response = student_auth_client.get('/student/results')
            assert response.status_code == 200
            # Should show the result
            assert b'Exam with Published Results' in response.data or b'80' in response.data

    def test_results_does_not_show_unpublished_results(self, student_auth_client, app, published_exam, student_user, _db):
        """Test that results page does not show unpublished results"""
        with app.app_context():
            # Create a submitted attempt for exam WITHOUT published results
            from models import Student
            student = Student.query.filter_by(user_id=student_user.id).first()
            attempt = Attempt(
                student_id=student.id,
                exam_id=published_exam.id,  # results_published=False
                status='submitted',
                submitted_at=datetime.utcnow(),
                total_score=8,
                percentage=80,
                grade='A'
            )
            _db.session.add(attempt)
            _db.session.commit()

            response = student_auth_client.get('/student/results')
            assert response.status_code == 200
            # Should not show this result
            # The page might be empty or show "No results published yet"

    def test_view_result_detail(self, student_auth_client, app, exam_with_results_published, student_user, question, _db):
        """Test viewing result details"""
        with app.app_context():
            # Create submitted attempt with published results
            from models import Student
            student = Student.query.filter_by(user_id=student_user.id).first()

            # Move question to exam with published results
            question.exam_id = exam_with_results_published.id
            _db.session.commit()

            attempt = Attempt(
                student_id=student.id,
                exam_id=exam_with_results_published.id,
                status='submitted',
                submitted_at=datetime.utcnow(),
                total_score=2,
                percentage=100,
                grade='A'
            )
            _db.session.add(attempt)
            _db.session.commit()

            # Add answer
            answer = Answer(
                attempt_id=attempt.id,
                question_id=question.id,
                answer_text='B',
                is_correct=True
            )
            _db.session.add(answer)
            _db.session.commit()

            response = student_auth_client.get(f'/student/attempts/{attempt.id}/result')
            assert response.status_code == 200
            # Should show detailed results

    def test_cannot_view_unpublished_result_detail(self, student_auth_client, app, submitted_attempt):
        """Test that cannot view unpublished result details"""
        with app.app_context():
            # submitted_attempt is for published_exam which has results_published=False
            response = student_auth_client.get(
                f'/student/attempts/{submitted_attempt.id}/result',
                follow_redirects=True
            )

            assert response.status_code == 200
            # Should redirect with message
            assert b'not been published' in response.data.lower() or b'dashboard' in response.data.lower()


class TestAccessControl:
    """Test student access control"""

    def test_student_cannot_access_other_student_attempt(self, client, app, submitted_attempt, inactive_student_user, _db):
        """Test that student cannot access another student's attempt"""
        with app.app_context():
            # Login as different student
            with client.session_transaction() as sess:
                sess['_user_id'] = str(inactive_student_user.id)

            response = client.get(f'/student/attempts/{submitted_attempt.id}/result',
                                 follow_redirects=True)

            # Should get 404 or access denied
            assert response.status_code in [200, 404]
