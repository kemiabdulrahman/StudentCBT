from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Student, SchoolClass, Subject, Assessment, Question, Attempt, Answer
from forms import SchoolClassForm, SubjectForm, StudentUploadForm, AssessmentForm, QuestionForm, QuestionUploadForm, EmptyForm
from utils import (parse_excel_students, parse_questions_from_word, parse_questions_from_pdf,
                  export_assessment_to_pdf, export_assessment_to_excel, export_student_answer_sheet)
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from io import BytesIO

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
    total_assessments = Assessment.query.count()

    # Get recent classes for display
    classes = SchoolClass.query.order_by(SchoolClass.id.desc()).limit(6).all()

    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_classes=total_classes,
                         total_subjects=total_subjects,
                         total_assessments=total_assessments,
                         classes=classes)


# ========== CLASS MANAGEMENT ==========

@admin_bp.route('/classes')
@login_required
@admin_required
def classes():
    """List all classes"""
    all_classes = SchoolClass.query.order_by(SchoolClass.name).all()
    return render_template('admin/classes.html', classes=all_classes)


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

@admin_bp.route('/subjects')
@login_required
@admin_required
def subjects():
    """List all subjects"""
    all_subjects = Subject.query.join(SchoolClass).order_by(SchoolClass.name, Subject.name).all()
    return render_template('admin/subjects.html', subjects=all_subjects)


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


# ========== ASSESSMENT MANAGEMENT ==========

@admin_bp.route('/assessments')
@login_required
@admin_required
def assessments():
    """List all assessments"""
    all_assessments = Assessment.query.order_by(Assessment.created_at.desc()).all()
    return render_template('admin/assessments.html', assessments=all_assessments)


@admin_bp.route('/assessments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_assessment():
    """Create a new assessment"""
    form = AssessmentForm()
    if form.validate_on_submit():
        assessment = Assessment(
            title=form.title.data,
            description=form.description.data,
            subject_id=form.subject_id.data,
            class_id=form.class_id.data,
            duration_minutes=form.duration_minutes.data,
            pass_mark=form.pass_mark.data,
            show_results=form.show_results.data,
            scheduled_start=form.scheduled_start.data,
            scheduled_end=form.scheduled_end.data,
            status='draft'
        )
        db.session.add(assessment)
        db.session.commit()
        flash(f'Assessment "{assessment.title}" created successfully! Now add questions.', 'success')
        return redirect(url_for('admin.assessment_details', assessment_id=assessment.id))

    return render_template('admin/create_assessment.html', form=form)


@admin_bp.route('/assessments/<int:assessment_id>')
@login_required
@admin_required
def assessment_details(assessment_id):
    """View assessment details and questions"""
    assessment = Assessment.query.get_or_404(assessment_id)
    questions = Question.query.filter_by(assessment_id=assessment_id).order_by(Question.order).all()

    # Calculate total marks
    total_marks = sum(q.marks for q in questions)
    assessment.total_marks = total_marks
    db.session.commit()

    return render_template('admin/assessment_details.html', assessment=assessment, questions=questions)


@admin_bp.route('/assessments/<int:assessment_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_assessment(assessment_id):
    """Edit an assessment"""
    assessment = Assessment.query.get_or_404(assessment_id)
    form = AssessmentForm(obj=assessment)

    if form.validate_on_submit():
        assessment.title = form.title.data
        assessment.description = form.description.data
        assessment.subject_id = form.subject_id.data
        assessment.class_id = form.class_id.data
        assessment.duration_minutes = form.duration_minutes.data
        assessment.pass_mark = form.pass_mark.data
        assessment.show_results = form.show_results.data
        assessment.scheduled_start = form.scheduled_start.data
        assessment.scheduled_end = form.scheduled_end.data
        db.session.commit()
        flash(f'Assessment "{assessment.title}" updated successfully!', 'success')
        return redirect(url_for('admin.assessment_details', assessment_id=assessment.id))

    return render_template('admin/edit_assessment.html', form=form, assessment=assessment)


@admin_bp.route('/assessments/<int:assessment_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_assessment(assessment_id):
    """Delete an assessment"""
    assessment = Assessment.query.get_or_404(assessment_id)

    db.session.delete(assessment)
    db.session.commit()
    flash(f'Assessment "{assessment.title}" deleted successfully!', 'success')
    return redirect(url_for('admin.assessments'))


@admin_bp.route('/assessments/<int:assessment_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_assessment(assessment_id):
    """Publish an assessment"""
    assessment = Assessment.query.get_or_404(assessment_id)

    if not assessment.questions:
        flash('Cannot publish assessment without questions!', 'danger')
        return redirect(url_for('admin.assessment_details', assessment_id=assessment.id))

    assessment.status = 'published'
    db.session.commit()
    flash(f'Assessment "{assessment.title}" published successfully!', 'success')
    return redirect(url_for('admin.assessment_details', assessment_id=assessment.id))


@admin_bp.route('/assessments/<int:assessment_id>/close', methods=['POST'])
@login_required
@admin_required
def close_assessment(assessment_id):
    """Close an assessment"""
    assessment = Assessment.query.get_or_404(assessment_id)
    assessment.status = 'closed'
    db.session.commit()
    flash(f'Assessment "{assessment.title}" closed successfully!', 'success')
    return redirect(url_for('admin.assessment_details', assessment_id=assessment.id))


# ========== QUESTION MANAGEMENT ==========

@admin_bp.route('/assessments/<int:assessment_id>/questions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_question(assessment_id):
    """Add a question to an assessment"""
    assessment = Assessment.query.get_or_404(assessment_id)
    form = QuestionForm()

    if form.validate_on_submit():
        # Get the highest order number
        max_order = db.session.query(db.func.max(Question.order)).filter_by(assessment_id=assessment_id).scalar() or 0

        question = Question(
            assessment_id=assessment_id,
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
        return redirect(url_for('admin.assessment_details', assessment_id=assessment_id))

    return render_template('admin/add_question.html', form=form, assessment=assessment)


@admin_bp.route('/assessments/<int:assessment_id>/questions/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_questions(assessment_id):
    """Bulk upload questions from Word/PDF"""
    assessment = Assessment.query.get_or_404(assessment_id)
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
            return redirect(url_for('admin.upload_questions', assessment_id=assessment_id))

        # Clean up file
        os.remove(filepath)

        if result['success']:
            # Get the highest order number
            max_order = db.session.query(db.func.max(Question.order)).filter_by(assessment_id=assessment_id).scalar() or 0

            for idx, q_data in enumerate(result['questions']):
                question = Question(
                    assessment_id=assessment_id,
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
            return redirect(url_for('admin.assessment_details', assessment_id=assessment_id))
        else:
            flash(f'Error: {result["message"]}', 'danger')

    return render_template('admin/upload_questions.html', form=form, assessment=assessment)


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
        return redirect(url_for('admin.assessment_details', assessment_id=question.assessment_id))

    return render_template('admin/edit_question.html', form=form, question=question)


@admin_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_question(question_id):
    """Delete a question"""
    question = Question.query.get_or_404(question_id)
    assessment_id = question.assessment_id

    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('admin.assessment_details', assessment_id=assessment_id))


# ========== ATTEMPTS AND RESULTS ==========

@admin_bp.route('/assessments/<int:assessment_id>/attempts')
@login_required
@admin_required
def assessment_attempts(assessment_id):
    """View all attempts for an assessment"""
    assessment = Assessment.query.get_or_404(assessment_id)
    attempts = Attempt.query.filter_by(assessment_id=assessment_id).order_by(Attempt.submitted_at.desc()).all()

    return render_template('admin/assessment_attempts.html', assessment=assessment, attempts=attempts)


@admin_bp.route('/attempts/<int:attempt_id>')
@login_required
@admin_required
def view_attempt(attempt_id):
    """View a specific attempt in detail"""
    attempt = Attempt.query.get_or_404(attempt_id)
    answers = Answer.query.filter_by(attempt_id=attempt_id).join(Question).order_by(Question.order).all()

    return render_template('admin/view_attempt.html', attempt=attempt, answers=answers)


# ========== EXPORT FUNCTIONALITY ==========

@admin_bp.route('/assessments/<int:assessment_id>/export/pdf')
@login_required
@admin_required
def export_assessment_pdf(assessment_id):
    """Export assessment results to PDF"""
    assessment = Assessment.query.get_or_404(assessment_id)
    attempts = Attempt.query.filter_by(assessment_id=assessment_id, status='submitted').order_by(Attempt.percentage.desc()).all()

    if not attempts:
        flash('No submitted attempts to export!', 'warning')
        return redirect(url_for('admin.assessment_attempts', assessment_id=assessment_id))

    pdf_bytes = export_assessment_to_pdf(assessment, attempts)

    if pdf_bytes:
        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{assessment.title}_Results.pdf'
        )
    else:
        flash('Error generating PDF export!', 'danger')
        return redirect(url_for('admin.assessment_attempts', assessment_id=assessment_id))


@admin_bp.route('/assessments/<int:assessment_id>/export/excel')
@login_required
@admin_required
def export_assessment_excel(assessment_id):
    """Export assessment results to Excel"""
    assessment = Assessment.query.get_or_404(assessment_id)
    attempts = Attempt.query.filter_by(assessment_id=assessment_id, status='submitted').order_by(Attempt.percentage.desc()).all()

    if not attempts:
        flash('No submitted attempts to export!', 'warning')
        return redirect(url_for('admin.assessment_attempts', assessment_id=assessment_id))

    excel_bytes = export_assessment_to_excel(assessment, attempts)

    if excel_bytes:
        return send_file(
            BytesIO(excel_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{assessment.title}_Results.xlsx'
        )
    else:
        flash('Error generating Excel export!', 'danger')
        return redirect(url_for('admin.assessment_attempts', assessment_id=assessment_id))


@admin_bp.route('/attempts/<int:attempt_id>/export/answer-sheet')
@login_required
@admin_required
def export_answer_sheet(attempt_id):
    """Export student answer sheet to PDF"""
    attempt = Attempt.query.get_or_404(attempt_id)

    if attempt.status != 'submitted':
        flash('Cannot export answer sheet for incomplete attempt!', 'warning')
        return redirect(url_for('admin.view_attempt', attempt_id=attempt_id))

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
        return redirect(url_for('admin.view_attempt', attempt_id=attempt_id))
