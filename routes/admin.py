from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Student, SchoolClass, Subject, Exam, Question, Attempt, Answer
from forms import SchoolClassForm, SubjectForm, StudentUploadForm, ExamForm, QuestionForm, QuestionUploadForm, EmptyForm
from utils import parse_excel_students, parse_questions_from_word, parse_questions_from_pdf
import os
from werkzeug.utils import secure_filename
from datetime import datetime

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system statistics"""
    total_students = Student.query.count()
    total_classes = SchoolClass.query.count()
    total_subjects = Subject.query.count()

    # Get recent classes for display
    classes = SchoolClass.query.order_by(SchoolClass.id.desc()).limit(6).all()

    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_classes=total_classes,
                         total_subjects=total_subjects,
                         classes=classes)


# ========== CLASS MANAGEMENT ==========

@admin_bp.route('/classes', methods=['GET', 'POST'])
@login_required
@admin_required
def classes():
    """List all classes and handle inline creation"""
    form = SchoolClassForm()

    if form.validate_on_submit():
        school_class = SchoolClass(
            name=form.name.data,
            level=form.level.data
        )
        db.session.add(school_class)
        db.session.commit()
        flash(f'Class "{school_class.name}" created successfully!', 'success')
        return redirect(url_for('admin.classes'))

    all_classes = SchoolClass.query.order_by(SchoolClass.name).all()
    return render_template('admin/classes.html', classes=all_classes, form=form)


@admin_bp.route('/classes/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_class():
    """Create a new class"""
    form = SchoolClassForm()
    if form.validate_on_submit():
        school_class = SchoolClass(
            name=form.name.data,
            level=form.level.data
        )
        db.session.add(school_class)
        db.session.commit()
        flash(f'Class "{school_class.name}" created successfully!', 'success')
        return redirect(url_for('admin.classes'))

    return render_template('admin/create_class.html', form=form)


@admin_bp.route('/classes/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_class(class_id):
    """Edit a class"""
    school_class = SchoolClass.query.get_or_404(class_id)
    form = SchoolClassForm(obj=school_class)

    if form.validate_on_submit():
        school_class.name = form.name.data
        school_class.level = form.level.data
        db.session.commit()
        flash(f'Class "{school_class.name}" updated successfully!', 'success')
        return redirect(url_for('admin.classes'))

    return render_template('admin/edit_class.html', form=form, school_class=school_class)


@admin_bp.route('/classes/<int:class_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_class(class_id):
    """Delete a class"""
    school_class = SchoolClass.query.get_or_404(class_id)

    # Check if class has students
    if school_class.students:
        flash(f'Cannot delete class "{school_class.name}" because it has students assigned.', 'danger')
        return redirect(url_for('admin.classes'))

    db.session.delete(school_class)
    db.session.commit()
    flash(f'Class "{school_class.name}" deleted successfully!', 'success')
    return redirect(url_for('admin.classes'))


# ========== SUBJECT MANAGEMENT ==========

@admin_bp.route('/subjects', methods=['GET', 'POST'])
@login_required
@admin_required
def subjects():
    """List all subjects and handle inline creation"""
    form = SubjectForm()

    if form.validate_on_submit():
        subject = Subject(
            name=form.name.data,
            code=form.code.data,
            class_id=form.class_id.data
        )
        db.session.add(subject)
        db.session.commit()
        flash(f'Subject "{subject.name}" created successfully!', 'success')
        return redirect(url_for('admin.subjects'))

    all_subjects = Subject.query.join(SchoolClass).order_by(SchoolClass.name, Subject.name).all()
    return render_template('admin/subjects.html', subjects=all_subjects, form=form)


@admin_bp.route('/subjects/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_subject():
    """Create a new subject"""
    form = SubjectForm()
    if form.validate_on_submit():
        subject = Subject(
            name=form.name.data,
            code=form.code.data,
            class_id=form.class_id.data
        )
        db.session.add(subject)
        db.session.commit()
        flash(f'Subject "{subject.name}" created successfully!', 'success')
        return redirect(url_for('admin.subjects'))

    return render_template('admin/create_subject.html', form=form)


@admin_bp.route('/subjects/<int:subject_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_subject(subject_id):
    """Edit a subject"""
    subject = Subject.query.get_or_404(subject_id)
    form = SubjectForm(obj=subject)

    if form.validate_on_submit():
        subject.name = form.name.data
        subject.code = form.code.data
        subject.class_id = form.class_id.data
        db.session.commit()
        flash(f'Subject "{subject.name}" updated successfully!', 'success')
        return redirect(url_for('admin.subjects'))

    return render_template('admin/edit_subject.html', form=form, subject=subject)


@admin_bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subject(subject_id):
    """Delete a subject"""
    subject = Subject.query.get_or_404(subject_id)

    # Check if subject has exams
    if subject.exams:
        flash(f'Cannot delete subject "{subject.name}" because it has exams assigned.', 'danger')
        return redirect(url_for('admin.subjects'))

    db.session.delete(subject)
    db.session.commit()
    flash(f'Subject "{subject.name}" deleted successfully!', 'success')
    return redirect(url_for('admin.subjects'))


# ========== STUDENT MANAGEMENT ==========

@admin_bp.route('/students')
@login_required
@admin_required
def students():
    """List all students"""
    all_students = Student.query.join(SchoolClass).order_by(SchoolClass.name, Student.last_name).all()
    return render_template('admin/students.html', students=all_students)


@admin_bp.route('/students/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_students():
    """Bulk upload students from Excel"""
    form = StudentUploadForm()
    if form.validate_on_submit():
        file = form.excel_file.data
        filename = secure_filename(file.filename)
        filepath = os.path.join('instance', filename)
        file.save(filepath)

        result = parse_excel_students(filepath, form.class_id.data)

        # Clean up file
        os.remove(filepath)

        if result['success']:
            flash(f'Successfully uploaded {result["created"]} students!', 'success')
            if result['errors']:
                for error in result['errors'][:5]:  # Show first 5 errors
                    flash(error, 'warning')
            return redirect(url_for('admin.students'))
        else:
            flash(f'Error: {result["message"]}', 'danger')

    return render_template('admin/upload_students.html', form=form)


@admin_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_student(student_id):
    """Delete a student"""
    student = Student.query.get_or_404(student_id)
    user = student.user

    db.session.delete(student)
    db.session.delete(user)
    db.session.commit()

    flash(f'Student "{student.full_name}" deleted successfully!', 'success')
    return redirect(url_for('admin.students'))


# ========== EXAM MANAGEMENT ==========

@admin_bp.route('/exams')
@login_required
@admin_required
def exams():
    """List all exams"""
    all_exams = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template('admin/exams.html', exams=all_exams)


@admin_bp.route('/exams/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_exam():
    """Create a new exam"""
    form = ExamForm()
    if form.validate_on_submit():
        exam = Exam(
            title=form.title.data,
            description=form.description.data,
            subject_id=form.subject_id.data,
            class_id=form.class_id.data,
            duration_minutes=form.duration_minutes.data,
            pass_mark=form.pass_mark.data,
            scheduled_start=form.scheduled_start.data,
            scheduled_end=form.scheduled_end.data,
            status='draft'
        )
        db.session.add(exam)
        db.session.commit()
        flash(f'Exam "{exam.title}" created successfully! Now add questions.', 'success')
        return redirect(url_for('admin.exam_details', exam_id=exam.id))

    return render_template('admin/create_exam.html', form=form)


@admin_bp.route('/exams/<int:exam_id>')
@login_required
@admin_required
def exam_details(exam_id):
    """View exam details and questions"""
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.order).all()

    # Calculate total marks
    total_marks = sum(q.marks for q in questions)
    exam.total_marks = total_marks
    db.session.commit()

    return render_template('admin/exam_details.html', exam=exam, questions=questions)


@admin_bp.route('/exams/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_exam(exam_id):
    """Edit an exam"""
    exam = Exam.query.get_or_404(exam_id)
    form = ExamForm(obj=exam)

    if form.validate_on_submit():
        exam.title = form.title.data
        exam.description = form.description.data
        exam.subject_id = form.subject_id.data
        exam.class_id = form.class_id.data
        exam.duration_minutes = form.duration_minutes.data
        exam.pass_mark = form.pass_mark.data
        exam.scheduled_start = form.scheduled_start.data
        exam.scheduled_end = form.scheduled_end.data
        db.session.commit()
        flash(f'Exam "{exam.title}" updated successfully!', 'success')
        return redirect(url_for('admin.exam_details', exam_id=exam.id))

    return render_template('admin/edit_exam.html', form=form, exam=exam)


@admin_bp.route('/exams/<int:exam_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_exam(exam_id):
    """Delete an exam"""
    exam = Exam.query.get_or_404(exam_id)

    db.session.delete(exam)
    db.session.commit()
    flash(f'Exam "{exam.title}" deleted successfully!', 'success')
    return redirect(url_for('admin.exams'))


@admin_bp.route('/exams/<int:exam_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_exam(exam_id):
    """Publish an exam"""
    exam = Exam.query.get_or_404(exam_id)

    if not exam.questions:
        flash('Cannot publish exam without questions!', 'danger')
        return redirect(url_for('admin.exam_details', exam_id=exam.id))

    exam.status = 'published'
    db.session.commit()
    flash(f'Exam "{exam.title}" published successfully!', 'success')
    return redirect(url_for('admin.exam_details', exam_id=exam.id))


@admin_bp.route('/exams/<int:exam_id>/close', methods=['POST'])
@login_required
@admin_required
def close_exam(exam_id):
    """Close an exam"""
    exam = Exam.query.get_or_404(exam_id)
    exam.status = 'closed'
    db.session.commit()
    flash(f'Exam "{exam.title}" closed successfully!', 'success')
    return redirect(url_for('admin.exam_details', exam_id=exam.id))


# ========== QUESTION MANAGEMENT ==========

@admin_bp.route('/exams/<int:exam_id>/questions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_question(exam_id):
    """Add a question to an exam"""
    exam = Exam.query.get_or_404(exam_id)
    form = QuestionForm()

    if form.validate_on_submit():
        # Get the highest order number
        max_order = db.session.query(db.func.max(Question.order)).filter_by(exam_id=exam_id).scalar() or 0

        question = Question(
            exam_id=exam_id,
            question_text=form.question_text.data,
            question_type=form.question_type.data,
            marks=form.marks.data,
            correct_answer=form.correct_answer.data,
            order=max_order + 1
        )

        if form.question_type.data == 'mcq':
            question.option_a = form.option_a.data
            question.option_b = form.option_b.data
            question.option_c = form.option_c.data
            question.option_d = form.option_d.data

        db.session.add(question)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('admin.exam_details', exam_id=exam_id))

    return render_template('admin/add_question.html', form=form, exam=exam)


@admin_bp.route('/exams/<int:exam_id>/questions/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_questions(exam_id):
    """Bulk upload questions from Word/PDF"""
    exam = Exam.query.get_or_404(exam_id)
    form = QuestionUploadForm()

    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        filepath = os.path.join('instance', filename)
        file.save(filepath)

        # Parse based on file type
        if filename.endswith('.docx'):
            result = parse_questions_from_word(filepath)
        elif filename.endswith('.pdf'):
            result = parse_questions_from_pdf(filepath)
        else:
            flash('Invalid file type!', 'danger')
            os.remove(filepath)
            return redirect(url_for('admin.upload_questions', exam_id=exam_id))

        # Clean up file
        os.remove(filepath)

        if result['success']:
            # Get the highest order number
            max_order = db.session.query(db.func.max(Question.order)).filter_by(exam_id=exam_id).scalar() or 0

            for idx, q_data in enumerate(result['questions']):
                question = Question(
                    exam_id=exam_id,
                    question_text=q_data['question_text'],
                    question_type=q_data['question_type'],
                    marks=q_data.get('marks', 1),
                    correct_answer=q_data.get('correct_answer', ''),
                    order=max_order + idx + 1
                )

                if q_data['question_type'] == 'mcq':
                    question.option_a = q_data.get('option_a')
                    question.option_b = q_data.get('option_b')
                    question.option_c = q_data.get('option_c')
                    question.option_d = q_data.get('option_d')

                db.session.add(question)

            db.session.commit()
            flash(f'Successfully uploaded {len(result["questions"])} questions!', 'success')
            return redirect(url_for('admin.exam_details', exam_id=exam_id))
        else:
            flash(f'Error: {result["message"]}', 'danger')

    return render_template('admin/upload_questions.html', form=form, exam=exam)


@admin_bp.route('/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_question(question_id):
    """Edit a question"""
    question = Question.query.get_or_404(question_id)
    form = QuestionForm(obj=question)

    if form.validate_on_submit():
        question.question_text = form.question_text.data
        question.question_type = form.question_type.data
        question.marks = form.marks.data
        question.correct_answer = form.correct_answer.data

        if form.question_type.data == 'mcq':
            question.option_a = form.option_a.data
            question.option_b = form.option_b.data
            question.option_c = form.option_c.data
            question.option_d = form.option_d.data

        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('admin.exam_details', exam_id=question.exam_id))

    return render_template('admin/edit_question.html', form=form, question=question)


@admin_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_question(question_id):
    """Delete a question"""
    question = Question.query.get_or_404(question_id)
    exam_id = question.exam_id

    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('admin.exam_details', exam_id=exam_id))


# ========== ATTEMPTS AND RESULTS ==========

@admin_bp.route('/exams/<int:exam_id>/attempts')
@login_required
@admin_required
def exam_attempts(exam_id):
    """View all attempts for an exam"""
    exam = Exam.query.get_or_404(exam_id)
    attempts = Attempt.query.filter_by(exam_id=exam_id).order_by(Attempt.submitted_at.desc()).all()

    return render_template('admin/exam_attempts.html', exam=exam, attempts=attempts)


@admin_bp.route('/attempts/<int:attempt_id>')
@login_required
@admin_required
def view_attempt(attempt_id):
    """View a specific attempt in detail"""
    attempt = Attempt.query.get_or_404(attempt_id)
    answers = Answer.query.filter_by(attempt_id=attempt_id).join(Question).order_by(Question.order).all()

    return render_template('admin/view_attempt.html', attempt=attempt, answers=answers)


@admin_bp.route('/exams/<int:exam_id>/toggle-results', methods=['POST'])
@login_required
@admin_required
def toggle_exam_results(exam_id):
    """Toggle results publication for an exam"""
    exam = Exam.query.get_or_404(exam_id)

    # Toggle the results_published status
    exam.results_published = not exam.results_published
    db.session.commit()

    if exam.results_published:
        flash(f'Results for "{exam.title}" are now visible to students!', 'success')
    else:
        flash(f'Results for "{exam.title}" are now hidden from students!', 'warning')

    return redirect(url_for('admin.exam_attempts', exam_id=exam.id))
