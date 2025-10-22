import pandas as pd
import openpyxl
from docx import Document
import PyPDF2
import json
import re
from flask_mail import Message
from flask import current_app
from models import (
    db, User, Student, Teacher, SchoolClass, Question, Answer,
    Result, Attempt
)

from datetime import datetime


def parse_excel_students(file_path, class_id):
    """
    Parse Excel file for student bulk upload.
    Expected columns: student_id, first_name, last_name, email, password
    """
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()  # Clean headers

        required_columns = ['student_id', 'first_name', 'last_name', 'email', 'password']
        if not all(col in df.columns for col in required_columns):
            return {'success': False, 'message': f'Missing required columns. Expected: {required_columns}'}

        students_created = []
        errors = []

        for idx, row in df.iterrows():
            try:
                student_id = str(row['student_id']).strip()
                email = str(row['email']).strip().lower()
                first_name = str(row['first_name']).strip()
                last_name = str(row['last_name']).strip()

                # --- Duplicate checks ---
                if User.query.filter_by(email=email).first():
                    errors.append(f"Row {idx+2}: Email {email} already exists")
                    continue

                if Student.query.filter_by(student_id=student_id).first():
                    errors.append(f"Row {idx+2}: Student ID {student_id} already exists")
                    continue

                if Student.query.filter_by(first_name=first_name, last_name=last_name, class_id=class_id).first():
                    errors.append(f"Row {idx+2}: Student {first_name} {last_name} already exists in this class")
                    continue

                # --- Create User ---
                user = User(email=email, role='student')
                user.set_password(str(row['password']))
                db.session.add(user)
                db.session.flush()  # Get user.id

                # --- Create Student ---
                student = Student(
                    user_id=user.id,
                    student_id=student_id,
                    first_name=first_name,
                    last_name=last_name,
                    class_id=class_id
                )
                db.session.add(student)
                students_created.append(student_id)

            except Exception as e:
                db.session.rollback()
                errors.append(f"Row {idx+2}: {str(e)}")
                continue

        if students_created:
            db.session.commit()

        return {
            'success': True,
            'created': len(students_created),
            'students': students_created,
            'errors': errors
        }

    except Exception as e:
        return {'success': False, 'message': f'Error parsing Excel: {str(e)}'}


def parse_excel_teachers(file_path):
    """
    Parse Excel file for teacher bulk upload.
    Expected columns: teacher_id, first_name, last_name, email, password
    """
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()

        required_columns = ['teacher_id', 'first_name', 'last_name', 'email', 'password']
        if not all(col in df.columns for col in required_columns):
            return {'success': False, 'message': f'Missing required columns. Expected: {required_columns}'}

        teachers_created = []
        errors = []

        for idx, row in df.iterrows():
            try:
                teacher_id = str(row['teacher_id']).strip()
                email = str(row['email']).strip().lower()
                first_name = str(row['first_name']).strip()
                last_name = str(row['last_name']).strip()

                # --- Duplicate checks ---
                if User.query.filter_by(email=email).first():
                    errors.append(f"Row {idx+2}: Email {email} already exists")
                    continue

                if Teacher.query.filter_by(teacher_id=teacher_id).first():
                    errors.append(f"Row {idx+2}: Teacher ID {teacher_id} already exists")
                    continue

                if Teacher.query.filter_by(first_name=first_name, last_name=last_name).first():
                    errors.append(f"Row {idx+2}: Teacher {first_name} {last_name} already exists")
                    continue

                # --- Create User ---
                user = User(email=email, role='teacher')
                user.set_password(str(row['password']))
                db.session.add(user)
                db.session.flush()

                # --- Create Teacher ---
                teacher = Teacher(
                    user_id=user.id,
                    teacher_id=teacher_id,
                    first_name=first_name,
                    last_name=last_name
                )
                db.session.add(teacher)
                teachers_created.append(teacher_id)

            except Exception as e:
                db.session.rollback()
                errors.append(f"Row {idx+2}: {str(e)}")
                continue

        if teachers_created:
            db.session.commit()

        return {
            'success': True,
            'created': len(teachers_created),
            'teachers': teachers_created,
            'errors': errors
        }

    except Exception as e:
        return {'success': False, 'message': f'Error parsing Excel: {str(e)}'}


def parse_questions_from_word(file_path):
    """
    Parse questions from Word document.
    Expected format:
    Q1. Question text? [MCQ/TRUE_FALSE/SHORT/ESSAY]
    A) Option A
    B) Option B
    C) Option C
    D) Option D
    Answer: A
    Marks: 2
    Keywords: keyword1, keyword2 (for short answer/essay)
    """
    try:
        doc = Document(file_path)
        questions = []
        current_question = {}
        
        for para in doc.paragraphs:
            text = para.text.strip()
            
            if not text:
                continue
            
            # Detect question start
            if re.match(r'^Q\d+\.', text):
                if current_question:
                    questions.append(current_question)
                
                # Extract question type
                q_type = 'mcq'
                if '[TRUE_FALSE]' in text:
                    q_type = 'true_false'
                elif '[SHORT]' in text:
                    q_type = 'short_answer'
                elif '[ESSAY]' in text:
                    q_type = 'essay'
                
                current_question = {
                    'question_text': re.sub(r'Q\d+\.\s*|\[.*?\]', '', text).strip(),
                    'question_type': q_type,
                    'marks': 1
                }
            
            # Parse options for MCQ
            elif re.match(r'^[A-D]\)', text) and current_question.get('question_type') == 'mcq':
                option_letter = text[0].lower()
                option_text = text[2:].strip()
                current_question[f'option_{option_letter}'] = option_text
            
            # Parse answer
            elif text.lower().startswith('answer:'):
                answer = text.split(':', 1)[1].strip()
                current_question['correct_answer'] = answer
            
            # Parse marks
            elif text.lower().startswith('marks:'):
                marks = text.split(':', 1)[1].strip()
                current_question['marks'] = int(marks)
            
            # Parse keywords
            elif text.lower().startswith('keywords:'):
                keywords = text.split(':', 1)[1].strip()
                current_question['keywords'] = keywords
        
        # Add last question
        if current_question:
            questions.append(current_question)
        
        return {'success': True, 'questions': questions}
        
    except Exception as e:
        return {'success': False, 'message': f'Error parsing Word document: {str(e)}'}


def parse_questions_from_pdf(file_path):
    """
    Parse questions from PDF document.
    Same format as Word document.
    """
    try:
        questions = []
        current_question = {}
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                lines = text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    # Detect question start
                    if re.match(r'^Q\d+\.', line):
                        if current_question:
                            questions.append(current_question)
                        
                        q_type = 'mcq'
                        if '[TRUE_FALSE]' in line:
                            q_type = 'true_false'
                        elif '[SHORT]' in line:
                            q_type = 'short_answer'
                        elif '[ESSAY]' in line:
                            q_type = 'essay'
                        
                        current_question = {
                            'question_text': re.sub(r'Q\d+\.\s*|\[.*?\]', '', line).strip(),
                            'question_type': q_type,
                            'marks': 1
                        }
                    
                    elif re.match(r'^[A-D]\)', line) and current_question.get('question_type') == 'mcq':
                        option_letter = line[0].lower()
                        option_text = line[2:].strip()
                        current_question[f'option_{option_letter}'] = option_text
                    
                    elif line.lower().startswith('answer:'):
                        answer = line.split(':', 1)[1].strip()
                        current_question['correct_answer'] = answer
                    
                    elif line.lower().startswith('marks:'):
                        marks = line.split(':', 1)[1].strip()
                        current_question['marks'] = int(marks)
                    
                    elif line.lower().startswith('keywords:'):
                        keywords = line.split(':', 1)[1].strip()
                        current_question['keywords'] = keywords
        
        if current_question:
            questions.append(current_question)
        
        return {'success': True, 'questions': questions}
        
    except Exception as e:
        return {'success': False, 'message': f'Error parsing PDF: {str(e)}'}


def auto_grade_answer(question, answer_text):
    """
    Auto-grade an answer based on question type.
    Returns (is_correct, marks_obtained)
    """
    if question.question_type == 'mcq':
        is_correct = answer_text.upper() == question.correct_answer.upper()
        marks = question.marks if is_correct else 0
        return is_correct, marks
    
    elif question.question_type == 'true_false':
        is_correct = answer_text.lower() == question.correct_answer.lower()
        marks = question.marks if is_correct else 0
        return is_correct, marks
    
    elif question.question_type in ['short_answer', 'essay']:
        # Keyword-based grading
        if not question.keywords:
            return None, 0  # Requires manual grading
        
        keywords = [k.strip().lower() for k in question.keywords.split(',')]
        answer_lower = answer_text.lower()
        
        # Count how many keywords are present
        matched_keywords = sum(1 for keyword in keywords if keyword in answer_lower)
        
        if len(keywords) > 0:
            # Partial marks based on keyword match
            percentage_match = matched_keywords / len(keywords)
            marks = round(question.marks * percentage_match, 2)
            
            # Consider it correct if more than 60% keywords matched
            is_correct = percentage_match >= 0.6
            return is_correct, marks
        
        return None, 0
    
    return None, 0


def send_result_email(mail, student, exam, result):
    """
    Send result email to student.
    """
    try:
        msg = Message(
            subject=f'Exam Result: {exam.title}',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[student.user.email]
        )
        
        msg.body = f"""
Dear {student.full_name},

Your exam result for "{exam.title}" is now available.

Exam Details:
- Subject: {exam.subject.name}
- Class: {exam.school_class.name}
- Term: {exam.term.name}

Results:
- Total Marks: {result.total_marks}
- Marks Obtained: {result.marks_obtained}
- Percentage: {result.percentage}%
- Grade: {result.grade}
- Remarks: {result.remarks}

You can view detailed results by logging into the CBT system.

Best regards,
Academic Team
"""
        
        msg.html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2563eb;">Exam Result Notification</h2>
    
    <p>Dear <strong>{student.full_name}</strong>,</p>
    
    <p>Your exam result for "<strong>{exam.title}</strong>" is now available.</p>
    
    <h3>Exam Details:</h3>
    <ul>
        <li><strong>Subject:</strong> {exam.subject.name}</li>
        <li><strong>Class:</strong> {exam.school_class.name}</li>
        <li><strong>Term:</strong> {exam.term.name}</li>
    </ul>
    
    <h3>Results:</h3>
    <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Marks</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{result.total_marks}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Marks Obtained</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{result.marks_obtained}</td>
        </tr>
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Percentage</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{result.percentage}%</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Grade</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>{result.grade}</strong></td>
        </tr>
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Remarks</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{result.remarks}</td>
        </tr>
    </table>
    
    <p>You can view detailed results by logging into the CBT system.</p>
    
    <p style="margin-top: 30px;">Best regards,<br><strong>Academic Team</strong></p>
</body>
</html>
"""
        
        mail.send(msg)
        
        # Update email sent status
        result.email_sent = True
        result.email_sent_at = datetime.utcnow()
        db.session.commit()
        
        return {'success': True}
        
    except Exception as e:
        return {'success': False, 'message': f'Error sending email: {str(e)}'}


def calculate_exam_statistics(exam):
    from sqlalchemy import func

    results = db.session.query(
        func.avg(Result.percentage).label('mean'),
        func.max(Result.percentage).label('highest'),
        func.min(Result.percentage).label('lowest'),
        func.count(Result.id).label('total_attempts')
    ).join(Attempt).filter(
        Attempt.exam_id == exam.id,
        Result.published == True
    ).first()

    if not results or results.total_attempts == 0:
        return {
            'mean': 0,
            'highest': 0,
            'lowest': 0,
            'total_attempts': 0
        }

    return {
        'mean': round(results.mean or 0, 2),
        'highest': results.highest or 0,
        'lowest': results.lowest or 0,
        'total_attempts': results.total_attempts or 0
    }
