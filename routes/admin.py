from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from models import db, AcademicSession, Term, SchoolClass, Subject, Student, Teacher, User, Exam, Result, Attempt
from forms import AcademicSessionForm, TermForm, SchoolClassForm, SubjectForm, StudentUploadForm, TeacherUploadForm
from utils import parse_excel_students, parse_excel_teachers, send_result_email
from werkzeug.utils import secure_filename
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Statistics
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    total_classes = SchoolClass.query.count()
    total_subjects = Subject.query.count()
    total_exams = Exam.query.count()
    
    # Recent sessions
    sessions = AcademicSession.query.order_by(AcademicSession.created_at.desc()).limit(5).all()
    
    # Recent classes
    classes = SchoolClass.query.order_by(SchoolClass.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_teachers=total_teachers,
                         total_classes=total_classes,
                         total_subjects=total_subjects,
                         total_exams=total_exams,
                         sessions=sessions,
                         classes=classes)


# Academic Sessions
@admin_bp.route('/sessions', methods=['GET', 'POST'])
@login_required
@admin_required
def sessions():
    form = AcademicSessionForm()
    
    if form.validate_on_submit():
        # If setting as current, unset other current sessions
        if form.is_current.data:
            AcademicSession.query.update({AcademicSession.is_current: False})
        
        session = AcademicSession(
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_current=form.is_current.data
        )
        db.session.add(session)
        db.session.commit()
        
        flash(f'Academic session "{session.name}" created successfully!', 'success')
        return redirect(url_for('admin.sessions'))
    
    all_sessions = AcademicSession.query.order_by(AcademicSession.name.desc()).all()
    return render_template('admin/sessions.html', form=form, sessions=all_sessions)


@admin_bp.route('/sessions/<int:session_id>/toggle-current')
@login_required
@admin_required
def toggle_current_session(session_id):
    session = AcademicSession.query.get_or_404(session_id)
    
    # Unset all current sessions
    AcademicSession.query.update({AcademicSession.is_current: False})
    
    # Set this as current
    session.is_current = True
    db.session.commit()
    
    flash(f'"{session.name}" set as current session.', 'success')
    return redirect(url_for('admin.sessions'))


# Terms
@admin_bp.route('/terms', methods=['GET', 'POST'])
@login_required
@admin_required
def terms():
    form = TermForm()
    
    if form.validate_on_submit():
        # If setting as current, unset other current terms
        if form.is_current.data:
            Term.query.update({Term.is_current: False})
        
        term = Term(
            session_id=form.session_id.data,
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_current=form.is_current.data
        )
        db.session.add(term)
        db.session.commit()
        
        flash(f'Term "{term.name}" created successfully!', 'success')
        return redirect(url_for('admin.terms'))
    
    all_terms = Term.query.join(AcademicSession).order_by(AcademicSession.name.desc(), Term.name).all()
    return render_template('admin/terms.html', form=form, terms=all_terms)


# Classes
@admin_bp.route('/classes', methods=['GET', 'POST'])
@login_required
@admin_required
def classes():
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
    return render_template('admin/classes.html', form=form, classes=all_classes)


# Subjects
@admin_bp.route('/subjects', methods=['GET', 'POST'])
@login_required
@admin_required
def subjects():
    form = SubjectForm()
    
    if form.validate_on_submit():
        subject = Subject(
            name=form.name.data,
            code=form.code.data,
            class_id=form.class_id.data,
            teacher_id=form.teacher_id.data
        )
        db.session.add(subject)
        db.session.commit()
        
        flash(f'Subject "{subject.name}" created successfully!', 'success')
        return redirect(url_for('admin.subjects'))
    
    all_subjects = Subject.query.join(SchoolClass).order_by(SchoolClass.name, Subject.name).all()
    return render_template('admin/subjects.html', form=form, subjects=all_subjects)


# Students Management
@admin_bp.route('/students')
@login_required
@admin_required
def students():
    all_students = Student.query.join(SchoolClass).order_by(SchoolClass.name, Student.last_name).all()
    return render_template('admin/students.html', students=all_students)


@admin_bp.route('/students/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_students():
    form = StudentUploadForm()
    
    if form.validate_on_submit():
        file = form.excel_file.data
        filename = secure_filename(file.filename)
        
        # Save file temporarily
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Parse and create students
        result = parse_excel_students(file_path, form.class_id.data)
        
        # Clean up
        os.remove(file_path)
        
        if result['success']:
            flash(f"Successfully created {result['created']} students!", 'success')
            if result['errors']:
                flash(f"Errors: {'; '.join(result['errors'])}", 'warning')
        else:
            flash(f"Error: {result['message']}", 'danger')
        
        return redirect(url_for('admin.students'))
    
    return render_template('admin/upload_students.html', form=form)


# Teachers Management
@admin_bp.route('/teachers')
@login_required
@admin_required
def teachers():
    all_teachers = Teacher.query.order_by(Teacher.last_name).all()
    return render_template('admin/teachers.html', teachers=all_teachers)


@admin_bp.route('/teachers/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_teachers():
    form = TeacherUploadForm()
    
    if form.validate_on_submit():
        file = form.excel_file.data
        filename = secure_filename(file.filename)
        
        # Save file temporarily
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Parse and create teachers
        result = parse_excel_teachers(file_path)
        
        # Clean up
        os.remove(file_path)
        
        if result['success']:
            flash(f"Successfully created {result['created']} teachers!", 'success')
            if result['errors']:
                flash(f"Errors: {'; '.join(result['errors'])}", 'warning')
        else:
            flash(f"Error: {result['message']}", 'danger')
        
        return redirect(url_for('admin.teachers'))
    
    return render_template('admin/upload_teachers.html', form=form)


# Results Management
@admin_bp.route('/results')
@login_required
@admin_required
def results():
    # Get all graded but unpublished results
    unpublished_results = Result.query.filter_by(published=False).join(Attempt).all()
    
    # Get published results
    published_results = Result.query.filter_by(published=True).join(Attempt).order_by(Result.published_at.desc()).limit(50).all()
    
    return render_template('admin/results.html', 
                         unpublished_results=unpublished_results,
                         published_results=published_results)


@admin_bp.route('/results/<int:result_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_result(result_id):
    from flask import current_app
    from extensions import mail
    
    result = Result.query.get_or_404(result_id)
    
    if result.published:
        flash('This result is already published.', 'warning')
        return redirect(url_for('admin.results'))
    
    # Publish result
    result.published = True
    result.published_at = db.func.now()
    
    # Send email if requested
    send_email = request.form.get('send_email') == 'true'
    
    if send_email:
        attempt = result.attempt
        student = attempt.student
        exam = attempt.exam
        
        email_result = send_result_email(mail, student, exam, result)
        
        if email_result['success']:
            flash(f'Result published and email sent to {student.user.email}!', 'success')
        else:
            flash(f'Result published but email failed: {email_result["message"]}', 'warning')
    else:
        flash('Result published successfully!', 'success')
    
    db.session.commit()
    return redirect(url_for('admin.results'))


@admin_bp.route('/results/bulk-publish', methods=['POST'])
@login_required
@admin_required
def bulk_publish_results():
    from flask import current_app
    from extensions import mail
    from datetime import datetime
    
    result_ids = request.form.getlist('result_ids[]')
    send_email = request.form.get('send_email') == 'true'
    
    published_count = 0
    email_count = 0
    
    for result_id in result_ids:
        result = Result.query.get(result_id)
        if result and not result.published:
            result.published = True
            result.published_at = datetime.utcnow()
            
            if send_email:
                attempt = result.attempt
                student = attempt.student
                exam = attempt.exam
                email_result = send_result_email(mail, student, exam, result)
                if email_result['success']:
                    email_count += 1
            
            published_count += 1
    
    db.session.commit()
    
    flash(f'Published {published_count} results. Sent {email_count} emails.', 'success')
    return redirect(url_for('admin.results'))




# Add these routes to your admin_routes.py file

# Class Detail with Update/Delete
@admin_bp.route('/classes/<int:class_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def class_detail(class_id):
    school_class = SchoolClass.query.get_or_404(class_id)
    form = SchoolClassForm(obj=school_class)
    
    if form.validate_on_submit():
        school_class.name = form.name.data
        school_class.level = form.level.data
        db.session.commit()
        flash(f'Class "{school_class.name}" updated successfully!', 'success')
        return redirect(url_for('admin.class_detail', class_id=class_id))
    
    return render_template('admin/class_detail.html', 
                         school_class=school_class, 
                         form=form)


@admin_bp.route('/classes/<int:class_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_class(class_id):
    school_class = SchoolClass.query.get_or_404(class_id)
    
    # Check if class has students
    if school_class.students:
        flash(f'Cannot delete class "{school_class.name}" - it has {len(school_class.students)} students assigned.', 'danger')
        return redirect(url_for('admin.class_detail', class_id=class_id))
    
    name = school_class.name
    db.session.delete(school_class)
    db.session.commit()
    
    flash(f'Class "{name}" deleted successfully!', 'success')
    return redirect(url_for('admin.classes'))


# Subject Detail with Update/Delete
@admin_bp.route('/subjects/<int:subject_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def subject_detail(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    form = SubjectForm(obj=subject)
    
    if form.validate_on_submit():
        subject.name = form.name.data
        subject.code = form.code.data
        subject.class_id = form.class_id.data
        subject.teacher_id = form.teacher_id.data
        db.session.commit()
        flash(f'Subject "{subject.name}" updated successfully!', 'success')
        return redirect(url_for('admin.subject_detail', subject_id=subject_id))
    
    return render_template('admin/subject_detail.html', 
                         subject=subject, 
                         form=form)


@admin_bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    # Check if subject has exams
    if subject.exams:
        flash(f'Cannot delete subject "{subject.name}" - it has {len(subject.exams)} exams.', 'danger')
        return redirect(url_for('admin.subject_detail', subject_id=subject_id))
    
    name = subject.name
    db.session.delete(subject)
    db.session.commit()
    
    flash(f'Subject "{name}" deleted successfully!', 'success')
    return redirect(url_for('admin.subjects'))


# Session Detail with Update/Delete
@admin_bp.route('/sessions/<int:session_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def session_detail(session_id):
    session = AcademicSession.query.get_or_404(session_id)
    form = AcademicSessionForm(obj=session)
    
    if form.validate_on_submit():
        # If setting as current, unset other current sessions
        if form.is_current.data and not session.is_current:
            AcademicSession.query.update({AcademicSession.is_current: False})
        
        session.name = form.name.data
        session.start_date = form.start_date.data
        session.end_date = form.end_date.data
        session.is_current = form.is_current.data
        db.session.commit()
        
        flash(f'Session "{session.name}" updated successfully!', 'success')
        return redirect(url_for('admin.session_detail', session_id=session_id))
    
    return render_template('admin/session_detail.html', 
                         session=session, 
                         form=form)


@admin_bp.route('/sessions/<int:session_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_session(session_id):
    session = AcademicSession.query.get_or_404(session_id)
    
    # Check if session has terms
    if session.terms:
        flash(f'Cannot delete session "{session.name}" - it has {len(session.terms)} terms.', 'danger')
        return redirect(url_for('admin.session_detail', session_id=session_id))
    
    name = session.name
    db.session.delete(session)
    db.session.commit()
    
    flash(f'Session "{name}" deleted successfully!', 'success')
    return redirect(url_for('admin.sessions'))


# Term Detail with Update/Delete
@admin_bp.route('/terms/<int:term_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def term_detail(term_id):
    term = Term.query.get_or_404(term_id)
    form = TermForm(obj=term)
    
    if form.validate_on_submit():
        # If setting as current, unset other current terms
        if form.is_current.data and not term.is_current:
            Term.query.update({Term.is_current: False})
        
        term.session_id = form.session_id.data
        term.name = form.name.data
        term.start_date = form.start_date.data
        term.end_date = form.end_date.data
        term.is_current = form.is_current.data
        db.session.commit()
        
        flash(f'Term "{term.name}" updated successfully!', 'success')
        return redirect(url_for('admin.term_detail', term_id=term_id))
    
    return render_template('admin/term_detail.html', 
                         term=term, 
                         form=form)


@admin_bp.route('/terms/<int:term_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_term(term_id):
    term = Term.query.get_or_404(term_id)
    
    # Check if term has exams
    if term.exams:
        flash(f'Cannot delete term "{term.name}" - it has {len(term.exams)} exams.', 'danger')
        return redirect(url_for('admin.term_detail', term_id=term_id))
    
    name = term.name
    db.session.delete(term)
    db.session.commit()
    
    flash(f'Term "{name}" deleted successfully!', 'success')
    return redirect(url_for('admin.terms'))


# Student Detail with Update/Delete
@admin_bp.route('/students/<int:student_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)
    
    # You'll need to create a StudentEditForm with fields for editing
    # For now, just showing the detail view
    return render_template('admin/student_detail.html', student=student)


@admin_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    
    # Also delete the associated user account
    user = student.user
    name = student.full_name
    
    db.session.delete(student)
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Student "{name}" deleted successfully!', 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_student_status(student_id):
    student = Student.query.get_or_404(student_id)
    student.user.is_active = not student.user.is_active
    db.session.commit()
    
    status = "activated" if student.user.is_active else "deactivated"
    flash(f'Student "{student.full_name}" {status} successfully!', 'success')
    return redirect(url_for('admin.student_detail', student_id=student_id))


# Teacher Detail with Update/Delete
@admin_bp.route('/teachers/<int:teacher_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def teacher_detail(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    return render_template('admin/teacher_detail.html', teacher=teacher)


@admin_bp.route('/teachers/<int:teacher_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    
    # Check if teacher has subjects
    if teacher.subjects:
        flash(f'Cannot delete teacher "{teacher.full_name}" - they have {len(teacher.subjects)} subjects assigned.', 'danger')
        return redirect(url_for('admin.teacher_detail', teacher_id=teacher_id))
    
    user = teacher.user
    name = teacher.full_name
    
    db.session.delete(teacher)
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Teacher "{name}" deleted successfully!', 'success')
    return redirect(url_for('admin.teachers'))


@admin_bp.route('/teachers/<int:teacher_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_teacher_status(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    teacher.user.is_active = not teacher.user.is_active
    db.session.commit()
    
    status = "activated" if teacher.user.is_active else "deactivated"
    flash(f'Teacher "{teacher.full_name}" {status} successfully!', 'success')
    return redirect(url_for('admin.teacher_detail', teacher_id=teacher_id))