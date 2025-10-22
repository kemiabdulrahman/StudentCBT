from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, Teacher, Exam, Question, Attempt, Answer, Result, Subject
from forms import ExamForm, QuestionForm, QuestionUploadForm, GradeAnswerForm, EmptyForm
from utils import parse_questions_from_word, parse_questions_from_pdf, auto_grade_answer, calculate_exam_statistics
from werkzeug.utils import secure_filename
from datetime import datetime
import os

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')


def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('You need teacher privileges to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    # Get teacher's statistics
    total_subjects = Subject.query.filter_by(teacher_id=teacher.id).count()
    total_exams = Exam.query.filter_by(teacher_id=teacher.id).count()
    draft_exams = Exam.query.filter_by(teacher_id=teacher.id, status='draft').count()
    published_exams = Exam.query.filter_by(teacher_id=teacher.id, status='published').count()
    
    # Pending grading
    pending_grading = db.session.query(Answer).join(Attempt).join(Exam).filter(
        Exam.teacher_id == teacher.id,
        Answer.graded == False,
        Attempt.status == 'submitted'
    ).count()
    
    # Recent exams
    recent_exams = Exam.query.filter_by(teacher_id=teacher.id).order_by(Exam.created_at.desc()).limit(5).all()
    
    # Subjects taught
    subjects = Subject.query.filter_by(teacher_id=teacher.id).all()
    
    return render_template('teacher/dashboard.html',
                         teacher=teacher,
                         total_subjects=total_subjects,
                         total_exams=total_exams,
                         draft_exams=draft_exams,
                         published_exams=published_exams,
                         pending_grading=pending_grading,
                         recent_exams=recent_exams,
                         subjects=subjects)


# Exams Management
@teacher_bp.route('/exams')
@login_required
@teacher_required
def exams():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    all_exams = Exam.query.filter_by(teacher_id=teacher.id).order_by(Exam.created_at.desc()).all()
    
    return render_template('teacher/exams.html', exams=all_exams)

@teacher_bp.route('/exams/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_exam():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    form = ExamForm()

    if form.validate_on_submit():
        exam = Exam(
            title=form.title.data,
            description=form.description.data,
            subject_id=form.subject_id.data,
            class_id=form.class_id.data,
            teacher_id=teacher.id,
            term_id=form.term_id.data,
            duration_minutes=form.duration_minutes.data,
            pass_mark=form.pass_mark.data,
            allow_multiple_attempts=form.allow_multiple_attempts.data,
            max_attempts=form.max_attempts.data or 1,
            scheduled_start=form.scheduled_start.data,
            scheduled_end=form.scheduled_end.data,
            status='draft'
        )
        db.session.add(exam)
        db.session.commit()

        flash(f'Exam "{exam.title}" created successfully!', 'success')
        return redirect(url_for('teacher.exam_details', exam_id=exam.id))

    return render_template('teacher/create_exam.html', form=form, teacher=teacher)

@teacher_bp.route("/exams/<int:exam_id>")
@login_required
@teacher_required
def exam_details(exam_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    exam = Exam.query.filter_by(id=exam_id, teacher_id=teacher.id).first_or_404()
    
    # Questions & attempts
    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.order).all()
    attempts = Attempt.query.filter_by(exam_id=exam.id).order_by(Attempt.started_at.desc()).all()
    
    # Stats only if published
    stats = calculate_exam_statistics(exam) if exam.status == "published" else None

    publish_form = EmptyForm()
    close_form = EmptyForm()

    return render_template(
        "teacher/exam_details.html",
        exam=exam,
        questions=questions,
        attempts=attempts,
        stats=stats,
        publish_form=publish_form,
        close_form=close_form
    )

@teacher_bp.route('/exams/<int:exam_id>/publish', methods=['POST'])
@login_required
@teacher_required
def publish_exam(exam_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    exam = Exam.query.filter_by(id=exam_id, teacher_id=teacher.id).first_or_404()
    
    if exam.status == 'published':
        flash('This exam is already published.', 'warning')
        return redirect(url_for('teacher.exam_details', exam_id=exam.id))
    
    # Check if exam has questions
    question_count = Question.query.filter_by(exam_id=exam.id).count()
    if question_count == 0:
        flash('Cannot publish exam without questions. Please add questions first.', 'danger')
        return redirect(url_for('teacher.exam_details', exam_id=exam.id))
    
    # Calculate total marks
    total_marks = db.session.query(db.func.sum(Question.marks)).filter_by(exam_id=exam.id).scalar() or 0
    exam.total_marks = total_marks
    exam.status = 'published'
    
    db.session.commit()
    
    flash(f'Exam "{exam.title}" published successfully!', 'success')
    return redirect(url_for('teacher.exam_details', exam_id=exam.id))


@teacher_bp.route('/exams/<int:exam_id>/close', methods=['POST'])
@login_required
@teacher_required
def close_exam(exam_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    exam = Exam.query.filter_by(id=exam_id, teacher_id=teacher.id).first_or_404()
    
    exam.status = 'closed'
    db.session.commit()
    
    flash(f'Exam "{exam.title}" closed successfully!', 'success')
    return redirect(url_for('teacher.exam_details', exam_id=exam.id))


# Questions Management
@teacher_bp.route('/exams/<int:exam_id>/questions/add', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_question(exam_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    exam = Exam.query.filter_by(id=exam_id, teacher_id=teacher.id).first_or_404()
    
    form = QuestionForm()
    
    if form.validate_on_submit():
        # Get current max order
        max_order = db.session.query(db.func.max(Question.order)).filter_by(exam_id=exam.id).scalar() or 0
        
        question = Question(
            exam_id=exam.id,
            question_text=form.question_text.data,
            question_type=form.question_type.data,
            marks=form.marks.data,
            order=max_order + 1,
            correct_answer=form.correct_answer.data,
            keywords=form.keywords.data
        )
        
        # Add MCQ options if applicable
        if form.question_type.data == 'mcq':
            question.option_a = form.option_a.data
            question.option_b = form.option_b.data
            question.option_c = form.option_c.data
            question.option_d = form.option_d.data
        
        db.session.add(question)
        db.session.commit()
        
        flash('Question added successfully!', 'success')
        return redirect(url_for('teacher.exam_details', exam_id=exam.id))
    
    return render_template('teacher/add_question.html', form=form, exam=exam)


@teacher_bp.route('/exams/<int:exam_id>/questions/upload', methods=['GET', 'POST'])
@login_required
@teacher_required
def upload_questions(exam_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    exam = Exam.query.filter_by(id=exam_id, teacher_id=teacher.id).first_or_404()
    
    form = QuestionUploadForm()
    
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        
        # Save file temporarily
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Parse questions based on file type
        if filename.endswith('.docx'):
            result = parse_questions_from_word(file_path)
        else:
            result = parse_questions_from_pdf(file_path)
        
        # Clean up
        os.remove(file_path)
        
        if result['success']:
            # Get current max order
            max_order = db.session.query(db.func.max(Question.order)).filter_by(exam_id=exam.id).scalar() or 0
            
            # Create questions
            for idx, q_data in enumerate(result['questions']):
                question = Question(
                    exam_id=exam.id,
                    question_text=q_data['question_text'],
                    question_type=q_data['question_type'],
                    marks=q_data.get('marks', 1),
                    order=max_order + idx + 1,
                    option_a=q_data.get('option_a'),
                    option_b=q_data.get('option_b'),
                    option_c=q_data.get('option_c'),
                    option_d=q_data.get('option_d'),
                    correct_answer=q_data.get('correct_answer'),
                    keywords=q_data.get('keywords')
                )
                db.session.add(question)
            
            db.session.commit()
            flash(f"Successfully uploaded {len(result['questions'])} questions!", 'success')
        else:
            flash(f"Error: {result['message']}", 'danger')
        
        return redirect(url_for('teacher.exam_details', exam_id=exam.id))
    
    return render_template('teacher/upload_questions.html', form=form, exam=exam)


# Grading
@teacher_bp.route('/grading')
@login_required
@teacher_required
def grading():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    # Get all submitted attempts for teacher's exams that need grading
    pending_attempts = db.session.query(Attempt).join(Exam).filter(
        Exam.teacher_id == teacher.id,
        Attempt.status == 'submitted'
    ).order_by(Attempt.submitted_at.desc()).all()
    
    return render_template('teacher/grading.html', attempts=pending_attempts)


@teacher_bp.route('/grading/attempt/<int:attempt_id>')
@login_required
@teacher_required
def grade_attempt(attempt_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    attempt = db.session.query(Attempt).join(Exam).filter(
        Attempt.id == attempt_id,
        Exam.teacher_id == teacher.id
    ).first_or_404()
    
    # Get all answers with questions
    answers = Answer.query.filter_by(attempt_id=attempt.id).join(Question).order_by(Question.order).all()
    
    return render_template('teacher/grade_attempt.html', attempt=attempt, answers=answers)


@teacher_bp.route('/grading/answer/<int:answer_id>', methods=['POST'])
@login_required
@teacher_required
def grade_answer(answer_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    answer = db.session.query(Answer).join(Attempt).join(Exam).filter(
        Answer.id == answer_id,
        Exam.teacher_id == teacher.id
    ).first_or_404()
    
    marks_obtained = float(request.form.get('marks_obtained', 0))
    feedback = request.form.get('feedback', '')
    
    # Validate marks
    if marks_obtained > answer.question.marks:
        return jsonify({'success': False, 'message': 'Marks cannot exceed question marks'}), 400
    
    answer.marks_obtained = marks_obtained
    answer.is_correct = marks_obtained >= (answer.question.marks * 0.6)
    answer.teacher_feedback = feedback
    answer.graded = True
    answer.graded_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Answer graded successfully'})


@teacher_bp.route('/grading/attempt/<int:attempt_id>/finalize', methods=['POST'])
@login_required
@teacher_required
def finalize_grading(attempt_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    attempt = db.session.query(Attempt).join(Exam).filter(
        Attempt.id == attempt_id,
        Exam.teacher_id == teacher.id
    ).first_or_404()
    
    # Check if all answers are graded
    ungraded_count = Answer.query.filter_by(attempt_id=attempt.id, graded=False).count()
    
    if ungraded_count > 0:
        flash(f'Please grade all answers first. {ungraded_count} answers remaining.', 'warning')
        return redirect(url_for('teacher.grade_attempt', attempt_id=attempt.id))
    
    # Calculate total score
    total_score = db.session.query(db.func.sum(Answer.marks_obtained)).filter_by(attempt_id=attempt.id).scalar() or 0
    
    # Update attempt
    attempt.total_score = total_score
    attempt.percentage = (total_score / attempt.exam.total_marks) * 100 if attempt.exam.total_marks > 0 else 0
    attempt.status = 'graded'
    
    # Create or update result
    result = Result.query.filter_by(attempt_id=attempt.id).first()
    if not result:
        result = Result(attempt_id=attempt.id)
        db.session.add(result)
    
    result.total_marks = attempt.exam.total_marks
    result.marks_obtained = total_score
    result.percentage = attempt.percentage
    result.calculate_grade()
    
    db.session.commit()
    
    flash('Grading finalized successfully! Result created.', 'success')
    return redirect(url_for('teacher.grading'))


# View Results
@teacher_bp.route('/results')
@login_required
@teacher_required
def results():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    # Get all results for teacher's exams
    all_results = db.session.query(Result).join(Attempt).join(Exam).filter(
        Exam.teacher_id == teacher.id
    ).order_by(Result.created_at.desc()).all()
    
    return render_template('teacher/results.html', results=all_results)


@teacher_bp.route('/results/<int:result_id>')
@login_required
@teacher_required
def result_details(result_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    result = db.session.query(Result).join(Attempt).join(Exam).filter(
        Result.id == result_id,
        Exam.teacher_id == teacher.id
    ).first_or_404()
    
    # Get all answers
    answers = Answer.query.filter_by(attempt_id=result.attempt.id).join(Question).order_by(Question.order).all()
    
    return render_template('teacher/result_details.html', result=result, answers=answers)



@teacher_bp.route('/exams/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_exam(exam_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    exam = Exam.query.filter_by(id=exam_id).first_or_404()
    
    # Verify ownership
    if exam.subject.teacher_id != teacher.id:
        flash('You do not have permission to edit this exam.', 'danger')
        return redirect(url_for('teacher.exams'))
    
    # Create form and populate with existing data
    form = ExamForm(teacher_id=teacher.id, obj=exam)
    
    if form.validate_on_submit():
        try:
            # Update exam fields
            exam.title = form.title.data
            exam.description = form.description.data
            exam.subject_id = form.subject_id.data
            exam.class_id = form.class_id.data
            exam.term_id = form.term_id.data
            exam.duration_minutes = form.duration_minutes.data
            exam.pass_mark = form.pass_mark.data
            exam.allow_multiple_attempts = form.allow_multiple_attempts.data
            exam.max_attempts = form.max_attempts.data if form.allow_multiple_attempts.data else 1
            exam.scheduled_start = form.scheduled_start.data
            exam.scheduled_end = form.scheduled_end.data
            exam.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Exam updated successfully!', 'success')
            return redirect(url_for('teacher.exam_details', exam_id=exam.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating exam: {str(e)}', 'danger')
    
    return render_template('teacher/edit_exam.html', form=form, exam=exam)