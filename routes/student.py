from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import db, Student, Assessment, Question, Attempt, Answer
from utils import auto_grade_answer, export_student_answer_sheet
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from io import BytesIO

student_bp = Blueprint('student', __name__)


def student_required(f):
    """Decorator to require student role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Access denied. Student privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard showing available exams"""
    student = Student.query.filter_by(user_id=current_user.id).first()

    # Get all published exams for student's class
    all_exams = Assessment.query.filter_by(
        class_id=student.class_id,
        status='published'
    ).order_by(Assessment.created_at.desc()).all()

    nigeria_tz = ZoneInfo('Africa/Lagos')
    now_nigeria = datetime.now(nigeria_tz)

    available_exams = []

    for assessment in all_exams:
        # Check if student has already attempted this assessment
        attempt = Attempt.query.filter_by(student_id=student.id, assessment_id=assessment.id).first()

        # Check if assessment is currently available (scheduling)
        is_available = True
        if assessment.scheduled_start and assessment.scheduled_end:
            start_nigeria = assessment.scheduled_start.replace(tzinfo=ZoneInfo('UTC')).astimezone(nigeria_tz)
            end_nigeria = assessment.scheduled_end.replace(tzinfo=ZoneInfo('UTC')).astimezone(nigeria_tz)
            assessment.start_nigeria = start_nigeria
            assessment.end_nigeria = end_nigeria
            is_available = start_nigeria <= now_nigeria <= end_nigeria
        else:
            assessment.start_nigeria = None
            assessment.end_nigeria = None

        available_exams.append({
            'assessment': assessment,
            'attempt': attempt,
            'is_available': is_available
        })

    return render_template(
        'student/dashboard.html',
        student=student,
        available_exams=available_exams,
        now=now_nigeria
    )


@student_bp.route('/exams/<int:assessment_id>/start', methods=['POST'])
@login_required
@student_required
def start_assessment(assessment_id):
    """Start an assessment attempt"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    assessment = Assessment.query.filter_by(id=assessment_id, class_id=student.class_id).first_or_404()

    # Verify assessment is published
    if assessment.status != 'published':
        flash('This assessment is not available.', 'danger')
        return redirect(url_for('student.dashboard'))

    # Check if assessment is within scheduled time (if scheduled)
    now_utc = datetime.now(ZoneInfo("UTC"))
    if assessment.scheduled_start and assessment.scheduled_end:
        start_utc = assessment.scheduled_start.replace(tzinfo=ZoneInfo("UTC")) if assessment.scheduled_start.tzinfo is None else assessment.scheduled_start.astimezone(ZoneInfo("UTC"))
        end_utc = assessment.scheduled_end.replace(tzinfo=ZoneInfo("UTC")) if assessment.scheduled_end.tzinfo is None else assessment.scheduled_end.astimezone(ZoneInfo("UTC"))

        if not (start_utc <= now_utc <= end_utc):
            flash('This assessment is not currently available.', 'warning')
            return redirect(url_for('student.dashboard'))

    # Check if student has already attempted this assessment
    existing_attempt = Attempt.query.filter_by(
        student_id=student.id,
        assessment_id=assessment.id
    ).first()

    if existing_attempt:
        if existing_attempt.status == 'submitted':
            flash('You have already completed this assessment.', 'warning')
            return redirect(url_for('student.view_result', attempt_id=existing_attempt.id))
        else:
            # Resume in-progress attempt
            attempt_start = existing_attempt.started_at.replace(tzinfo=ZoneInfo("UTC")) if existing_attempt.started_at.tzinfo is None else existing_attempt.started_at
            exam_end_time = attempt_start + timedelta(minutes=assessment.duration_minutes)

            # Check if time expired
            if now_utc >= exam_end_time:
                flash('Your assessment time has expired. Submitting...', 'warning')
                return redirect(url_for('student.submit_assessment', attempt_id=existing_attempt.id))

            session['current_attempt_id'] = existing_attempt.id
            session['exam_end_time'] = exam_end_time.isoformat()
            flash('Resuming your assessment!', 'info')
            return redirect(url_for('student.take_assessment', attempt_id=existing_attempt.id))

    # Create new attempt
    attempt = Attempt(
        student_id=student.id,
        assessment_id=assessment.id,
        status='in_progress',
        started_at=now_utc
    )
    db.session.add(attempt)
    db.session.commit()

    # Calculate assessment end time
    exam_end_time = now_utc + timedelta(minutes=assessment.duration_minutes)
    session['current_attempt_id'] = attempt.id
    session['exam_end_time'] = exam_end_time.isoformat()

    flash('Assessment started! Good luck!', 'success')
    return redirect(url_for('student.take_assessment', attempt_id=attempt.id))


@student_bp.route('/attempts/<int:attempt_id>/take')
@login_required
@student_required
def take_assessment(attempt_id):
    """Take assessment interface"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    attempt = Attempt.query.filter_by(id=attempt_id, student_id=student.id).first_or_404()

    if attempt.status != 'in_progress':
        flash('This attempt has already been submitted.', 'warning')
        return redirect(url_for('student.view_result', attempt_id=attempt.id))

    questions = Question.query.filter_by(assessment_id=attempt.assessment_id).order_by(Question.order).all()
    existing_answers = {a.question_id: a.answer_text for a in Answer.query.filter_by(attempt_id=attempt.id).all()}

    # Get assessment end time
    exam_end_time_str = session.get('exam_end_time')
    if exam_end_time_str:
        exam_end_time = datetime.fromisoformat(exam_end_time_str)
        if exam_end_time.tzinfo is None:
            exam_end_time = exam_end_time.replace(tzinfo=ZoneInfo('UTC'))
    else:
        # Fallback calculation
        exam_end_time = attempt.started_at + timedelta(minutes=attempt.assessment.duration_minutes)
        if exam_end_time.tzinfo is None:
            exam_end_time = exam_end_time.replace(tzinfo=ZoneInfo('UTC'))
        session['exam_end_time'] = exam_end_time.isoformat()

    # Calculate remaining time
    now_utc = datetime.now(ZoneInfo('UTC'))
    remaining_seconds = max(0, int((exam_end_time - now_utc).total_seconds()))

    # If time expired, redirect to submit
    if remaining_seconds == 0:
        flash('Time is up! Submitting your assessment...', 'warning')
        return redirect(url_for('student.submit_assessment', attempt_id=attempt.id))

    return render_template(
        'student/take_exam.html',
        attempt=attempt,
        questions=questions,
        existing_answers=existing_answers,
        remaining_seconds=remaining_seconds
    )


@student_bp.route('/attempts/<int:attempt_id>/save-answer', methods=['POST'])
@login_required
@student_required
def save_answer(attempt_id):
    """Save answer via AJAX"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    attempt = Attempt.query.filter_by(id=attempt_id, student_id=student.id).first_or_404()

    if attempt.status != 'in_progress':
        return jsonify({'success': False, 'message': 'Attempt already submitted'}), 400

    question_id = request.json.get('question_id')
    answer_text = request.json.get('answer_text', '').strip()

    answer = Answer.query.filter_by(attempt_id=attempt.id, question_id=question_id).first()
    if not answer:
        answer = Answer(attempt_id=attempt.id, question_id=question_id)
        db.session.add(answer)

    answer.answer_text = answer_text
    db.session.commit()

    return jsonify({'success': True, 'message': 'Answer saved'})


@student_bp.route('/attempts/<int:attempt_id>/submit', methods=['POST'])
@login_required
@student_required
def submit_assessment(attempt_id):
    """Submit assessment and calculate score"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    attempt = Attempt.query.filter_by(id=attempt_id, student_id=student.id).first_or_404()

    if attempt.status != 'in_progress':
        flash('This attempt has already been submitted.', 'warning')
        return redirect(url_for('student.view_result', attempt_id=attempt.id))

    # Auto-grade all answers
    questions = Question.query.filter_by(assessment_id=attempt.assessment_id).all()

    for question in questions:
        answer = Answer.query.filter_by(attempt_id=attempt.id, question_id=question.id).first()

        if not answer:
            # Create empty answer for unanswered questions
            answer = Answer(
                attempt_id=attempt.id,
                question_id=question.id,
                answer_text='',
                is_correct=False,
                marks_obtained=0
            )
            db.session.add(answer)
        else:
            # Auto-grade the answer
            is_correct, marks = auto_grade_answer(question, answer.answer_text)
            answer.is_correct = is_correct
            answer.marks_obtained = marks

    # Calculate total score and grade
    attempt.status = 'submitted'
    attempt.submitted_at = datetime.utcnow()

    total_score = db.session.query(db.func.sum(Answer.marks_obtained)).filter_by(attempt_id=attempt.id).scalar() or 0
    attempt.total_score = total_score

    if attempt.assessment.total_marks > 0:
        attempt.percentage = (total_score / attempt.assessment.total_marks) * 100
    else:
        attempt.percentage = 0

    # Calculate grade
    attempt.calculate_grade()

    db.session.commit()

    # Clear session
    session.pop('current_attempt_id', None)
    session.pop('exam_end_time', None)

    # Redirect based on show_results setting
    if attempt.assessment.show_results:
        flash('Assessment submitted successfully! View your results below.', 'success')
        return redirect(url_for('student.view_result', attempt_id=attempt.id))
    else:
        flash('Assessment submitted successfully! Your results will be available once the administrator enables them.', 'success')
        return redirect(url_for('student.dashboard'))


@student_bp.route('/attempts/<int:attempt_id>/result')
@login_required
@student_required
def view_result(attempt_id):
    """View assessment result"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    attempt = Attempt.query.filter_by(id=attempt_id, student_id=student.id).first_or_404()

    if attempt.status != 'submitted':
        flash('This assessment has not been submitted yet.', 'warning')
        return redirect(url_for('student.dashboard'))

    # Check if results are enabled for this assessment
    if not attempt.assessment.show_results:
        flash('Your assessment has been submitted successfully! Results will be available once the administrator enables them.', 'info')
        return redirect(url_for('student.dashboard'))

    # Get all answers with questions
    answers = Answer.query.filter_by(attempt_id=attempt.id).join(Question).order_by(Question.order).all()

    return render_template('student/result.html', attempt=attempt, answers=answers)


@student_bp.route('/attempts/<int:attempt_id>/export/answer-sheet')
@login_required
@student_required
def export_my_answer_sheet(attempt_id):
    """Export student's own answer sheet to PDF"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    attempt = Attempt.query.filter_by(id=attempt_id, student_id=student.id).first_or_404()

    if attempt.status != 'submitted':
        flash('Cannot export answer sheet for incomplete attempt!', 'warning')
        return redirect(url_for('student.dashboard'))

    # Check if results are enabled for this assessment
    if not attempt.assessment.show_results:
        flash('Answer sheets will be available once the administrator enables results viewing.', 'info')
        return redirect(url_for('student.dashboard'))

    pdf_bytes = export_student_answer_sheet(attempt)

    if pdf_bytes:
        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{attempt.student.student_id}_{attempt.assessment.title}_Answer_Sheet.pdf'
        )
    else:
        flash('Error generating answer sheet!', 'danger')
        return redirect(url_for('student.view_result', attempt_id=attempt_id))
