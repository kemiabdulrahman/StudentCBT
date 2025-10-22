from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from functools import wraps
from models import db, Student, Exam, Question, Attempt, Answer, Result
from utils import auto_grade_answer
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

student_bp = Blueprint('student', __name__, url_prefix='/student')

# -----------------------------
# Decorators
# -----------------------------
def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('You need student privileges to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------
# Dashboard
# -----------------------------
# -----------------------------
@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    student = Student.query.filter_by(user_id=current_user.id).first()
    available_exams = Exam.query.filter_by(
        class_id=student.class_id, status='published'
    ).order_by(Exam.created_at.desc()).all()

    nigeria_tz = ZoneInfo('Africa/Lagos')
    now_nigeria = datetime.now(nigeria_tz)

    active_exams = []
    upcoming_exams = []

    for exam in available_exams:
        if exam.scheduled_start and exam.scheduled_end:
            start_nigeria = exam.scheduled_start.replace(tzinfo=ZoneInfo('UTC')).astimezone(nigeria_tz)
            end_nigeria = exam.scheduled_end.replace(tzinfo=ZoneInfo('UTC')).astimezone(nigeria_tz)

            # attach converted times to the exam object
            exam.start_nigeria = start_nigeria
            exam.end_nigeria = end_nigeria

            if start_nigeria <= now_nigeria <= end_nigeria:
                active_exams.append(exam)
            elif start_nigeria > now_nigeria:
                upcoming_exams.append(exam)
        else:
            # exams without schedule are just considered active
            exam.start_nigeria = None
            exam.end_nigeria = None
            active_exams.append(exam)

    recent_attempts = Attempt.query.filter_by(student_id=student.id).order_by(
        Attempt.started_at.desc()
    ).limit(5).all()

    published_results = db.session.query(Result).join(Attempt).filter(
        Attempt.student_id == student.id, Result.published == True
    ).order_by(Result.published_at.desc()).limit(5).all()

    total_attempts = Attempt.query.filter_by(student_id=student.id).count()
    completed_attempts = Attempt.query.filter_by(student_id=student.id, status='graded').count()

    return render_template(
        'student/dashboard.html',
        student=student,
        active_exams=active_exams,
        upcoming_exams=upcoming_exams,
        recent_attempts=recent_attempts,
        published_results=published_results,
        total_attempts=total_attempts,
        completed_attempts=completed_attempts,
        now=now_nigeria
    )

# -----------------------------
# Exams List
# -----------------------------
@student_bp.route('/exams')
@login_required
@student_required
def exams():
    student = Student.query.filter_by(user_id=current_user.id).first()
    all_exams = Exam.query.filter_by(class_id=student.class_id, status='published').order_by(Exam.created_at.desc()).all()

    exams_with_attempts = []
    for exam in all_exams:
        attempt_count = Attempt.query.filter_by(student_id=student.id, exam_id=exam.id).count()
        exams_with_attempts.append({
            'exam': exam,
            'attempt_count': attempt_count,
            'can_attempt': exam.allow_multiple_attempts or attempt_count == 0
        })

    return render_template('student/exams.html', exams=exams_with_attempts)

@student_bp.route('/exams/<int:exam_id>/start', methods=['POST'])
@login_required
@student_required
def start_exam(exam_id):
    student = Student.query.filter_by(user_id=current_user.id).first()
    exam = Exam.query.filter_by(id=exam_id, class_id=student.class_id).first_or_404()

    # Verify exam is available
    if exam.status != 'published':
        flash('This exam is not available.', 'danger')
        return redirect(url_for('student.exams'))

    # Current time in UTC for consistency
    now_utc = datetime.now(ZoneInfo("UTC"))

    # Convert exam schedule to UTC for comparison
    if exam.scheduled_start and exam.scheduled_end:
        # Ensure times are timezone-aware
        if exam.scheduled_start.tzinfo is None:
            start_utc = exam.scheduled_start.replace(tzinfo=ZoneInfo("UTC"))
        else:
            start_utc = exam.scheduled_start.astimezone(ZoneInfo("UTC"))
            
        if exam.scheduled_end.tzinfo is None:
            end_utc = exam.scheduled_end.replace(tzinfo=ZoneInfo("UTC"))
        else:
            end_utc = exam.scheduled_end.astimezone(ZoneInfo("UTC"))
        
        # Check if exam is currently available
        if not (start_utc <= now_utc <= end_utc):
            flash('This exam is not currently available.', 'danger')
            return redirect(url_for('student.exam_info', exam_id=exam.id))

    # Check if there is an in-progress attempt to resume
    existing_attempt = Attempt.query.filter_by(
        student_id=student.id,
        exam_id=exam.id,
        status='in_progress'
    ).first()

    if existing_attempt:
        # Calculate the original end time (when they started + duration)
        attempt_start = existing_attempt.started_at
        if attempt_start.tzinfo is None:
            attempt_start = attempt_start.replace(tzinfo=ZoneInfo("UTC"))
        
        exam_end_time = attempt_start + timedelta(minutes=exam.duration_minutes)
        
        # Check if time has already expired
        if now_utc >= exam_end_time:
            flash('Your exam time has expired. The exam will be auto-submitted.', 'warning')
            # Auto-submit the expired attempt
            existing_attempt.status = 'submitted'
            existing_attempt.submitted_at = now_utc
            db.session.commit()
            return redirect(url_for('student.attempt_summary', attempt_id=existing_attempt.id))
        
        # Resume with correct remaining time
        session['current_attempt_id'] = existing_attempt.id
        session['exam_end_time'] = exam_end_time.isoformat()
        flash('Resuming your exam!', 'info')
        return redirect(url_for('student.take_exam', attempt_id=existing_attempt.id))

    # Check attempt limits for new attempts
    attempt_count = Attempt.query.filter_by(student_id=student.id, exam_id=exam.id).count()
    if not exam.allow_multiple_attempts and attempt_count > 0:
        flash('You have already attempted this exam.', 'warning')
        return redirect(url_for('student.exam_info', exam_id=exam.id))

    if exam.allow_multiple_attempts and attempt_count >= exam.max_attempts:
        flash('You have reached the maximum number of attempts for this exam.', 'warning')
        return redirect(url_for('student.exam_info', exam_id=exam.id))

    # Create new attempt
    attempt = Attempt(
        student_id=student.id,
        exam_id=exam.id,
        attempt_number=attempt_count + 1,
        status='in_progress',
        started_at=now_utc
    )
    db.session.add(attempt)
    db.session.commit()

    # Calculate and store exam end time in UTC
    exam_end_time = now_utc + timedelta(minutes=exam.duration_minutes)
    session['current_attempt_id'] = attempt.id
    session['exam_end_time'] = exam_end_time.isoformat()

    flash('Exam started! Good luck!', 'success')
    return redirect(url_for('student.take_exam', attempt_id=attempt.id))
# -----------------------------
# Exam Info
# -----------------------------
@student_bp.route('/exams/<int:exam_id>')
@login_required
@student_required
def exam_info(exam_id):
    student = Student.query.filter_by(user_id=current_user.id).first_or_404()
    exam = Exam.query.filter_by(id=exam_id, class_id=student.class_id).first_or_404()
    previous_attempts = Attempt.query.filter_by(student_id=student.id, exam_id=exam.id).order_by(Attempt.started_at.desc()).all()

    can_attempt = len(previous_attempts) < exam.max_attempts if exam.allow_multiple_attempts else len(previous_attempts) == 0

    nigeria_tz = ZoneInfo('Africa/Lagos')
    now_nigeria = datetime.now(nigeria_tz)

    is_available = True
    if exam.scheduled_start and exam.scheduled_end:
        start_nigeria = exam.scheduled_start.replace(tzinfo=ZoneInfo('UTC')).astimezone(nigeria_tz)
        end_nigeria = exam.scheduled_end.replace(tzinfo=ZoneInfo('UTC')).astimezone(nigeria_tz)
        is_available = start_nigeria <= now_nigeria <= end_nigeria

    return render_template(
        'student/exam_info.html',
        exam=exam,
        previous_attempts=previous_attempts,
        can_attempt=can_attempt,
        is_available=is_available,
        now=now_nigeria
    )

# -----------------------------
# Take Exam
# -----------------------------
@student_bp.route('/attempts/<int:attempt_id>/take')
@login_required
@student_required
def take_exam(attempt_id):
    student = Student.query.filter_by(user_id=current_user.id).first()
    attempt = Attempt.query.filter_by(id=attempt_id, student_id=student.id).first_or_404()

    if attempt.status != 'in_progress':
        flash('This attempt has already been submitted.', 'warning')
        return redirect(url_for('student.dashboard'))

    questions = Question.query.filter_by(exam_id=attempt.exam_id).order_by(Question.order).all()
    existing_answers = {a.question_id: a.answer_text for a in Answer.query.filter_by(attempt_id=attempt.id).all()}

    # Get exam end time from session or calculate it
    exam_end_time_str = session.get('exam_end_time')
    
    if exam_end_time_str:
        # Session stores UTC time, convert to aware datetime
        exam_end_time = datetime.fromisoformat(exam_end_time_str)
        if exam_end_time.tzinfo is None:
            exam_end_time = exam_end_time.replace(tzinfo=ZoneInfo('UTC'))
    else:
        # Fallback: calculate from attempt start time + duration
        exam_end_time = attempt.started_at + timedelta(minutes=attempt.exam.duration_minutes)
        if exam_end_time.tzinfo is None:
            exam_end_time = exam_end_time.replace(tzinfo=ZoneInfo('UTC'))
        # Store in session for next time
        session['exam_end_time'] = exam_end_time.isoformat()
    
    # Get current time in UTC for accurate comparison
    now_utc = datetime.now(ZoneInfo('UTC'))
    remaining_seconds = max(0, int((exam_end_time - now_utc).total_seconds()))

    return render_template(
        'student/take_exam.html',
        attempt=attempt,
        questions=questions,
        existing_answers=existing_answers,
        remaining_seconds=remaining_seconds
    )

# -----------------------------
# Save Answer (AJAX)
# -----------------------------
@student_bp.route('/attempts/<int:attempt_id>/save-answer', methods=['POST'])
@login_required
@student_required
def save_answer(attempt_id):
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

# -----------------------------
# Submit Exam
# -----------------------------
@student_bp.route('/attempts/<int:attempt_id>/submit', methods=['POST'])
@login_required
@student_required
def submit_exam(attempt_id):
    student = Student.query.filter_by(user_id=current_user.id).first()
    attempt = Attempt.query.filter_by(id=attempt_id, student_id=student.id).first_or_404()

    if attempt.status != 'in_progress':
        flash('This attempt has already been submitted.', 'warning')
        return redirect(url_for('student.dashboard'))

    questions = Question.query.filter_by(exam_id=attempt.exam_id).all()

    for question in questions:
        answer = Answer.query.filter_by(attempt_id=attempt.id, question_id=question.id).first()
        if not answer:
            answer = Answer(attempt_id=attempt.id, question_id=question.id, answer_text='', is_correct=False, marks_obtained=0, graded=True)
            db.session.add(answer)
        elif not answer.graded:
            is_correct, marks = auto_grade_answer(question, answer.answer_text)
            answer.is_correct = is_correct
            answer.marks_obtained = marks
            if question.question_type in ['mcq', 'true_false'] or (question.question_type in ['short_answer', 'essay'] and question.keywords):
                answer.graded = True

    attempt.status = 'submitted'
    attempt.submitted_at = datetime.utcnow()
    total_score = db.session.query(db.func.sum(Answer.marks_obtained)).filter_by(attempt_id=attempt.id, graded=True).scalar() or 0
    attempt.total_score = total_score
    if attempt.exam.total_marks > 0:
        attempt.percentage = (total_score / attempt.exam.total_marks) * 100

    db.session.commit()
    session.pop('current_attempt_id', None)
    session.pop('exam_end_time', None)

    flash('Exam submitted successfully! Your teacher will grade it soon.', 'success')
    return redirect(url_for('student.attempt_summary', attempt_id=attempt.id))

# -----------------------------
# Attempt Summary
# -----------------------------
@student_bp.route('/attempts/<int:attempt_id>/summary')
@login_required
@student_required
def attempt_summary(attempt_id):
    student = Student.query.filter_by(user_id=current_user.id).first()
    attempt = Attempt.query.filter_by(id=attempt_id, student_id=student.id).first_or_404()
    return render_template('student/attempt_summary.html', attempt=attempt)

# -----------------------------
# Results
# -----------------------------
@student_bp.route('/results')
@login_required
@student_required
def results():
    student = Student.query.filter_by(user_id=current_user.id).first()
    all_results = db.session.query(Result).join(Attempt).filter(
        Attempt.student_id == student.id,
        Result.published == True
    ).order_by(Result.published_at.desc()).all()
    return render_template('student/results.html', results=all_results)

@student_bp.route('/results/<int:result_id>')
@login_required
@student_required
def result_details(result_id):
    student = Student.query.filter_by(user_id=current_user.id).first()
    result = db.session.query(Result).join(Attempt).filter(
        Result.id == result_id,
        Attempt.student_id == student.id,
        Result.published == True
    ).first_or_404()

    answers = Answer.query.filter_by(attempt_id=result.attempt.id).join(Question).order_by(Question.order).all()
    return render_template('student/result_details.html', result=result, answers=answers)
