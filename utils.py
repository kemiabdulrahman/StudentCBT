import pandas as pd
from docx import Document
import PyPDF2
import re
from email_validator import validate_email, EmailNotValidError
from models import db, User, Student, SchoolClass


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

                # Validate email format
                try:
                    valid = validate_email(email)
                    email = valid.email  # Use normalized form
                except EmailNotValidError as e:
                    errors.append(f"Row {idx+2}: Invalid email format '{email}' - {str(e)}")
                    continue

                # Check for empty required fields
                if not student_id or not first_name or not last_name:
                    errors.append(f"Row {idx+2}: Missing required fields (student_id, first_name, or last_name)")
                    continue

                # Duplicate checks
                if User.query.filter_by(email=email).first():
                    errors.append(f"Row {idx+2}: Email {email} already exists")
                    continue

                if Student.query.filter_by(student_id=student_id).first():
                    errors.append(f"Row {idx+2}: Student ID {student_id} already exists")
                    continue

                if Student.query.filter_by(first_name=first_name, last_name=last_name, class_id=class_id).first():
                    errors.append(f"Row {idx+2}: Student {first_name} {last_name} already exists in this class")
                    continue

                # Create User
                user = User(email=email, role='student')
                user.set_password(str(row['password']))
                db.session.add(user)
                db.session.flush()  # Get user.id

                # Create Student
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


def parse_questions_from_word(file_path):
    """
    Parse questions from Word document.
    Supported formats: MCQ, True/False, and Fill-in-the-Blank

    Expected format:
    Q1. Question text? [MCQ/TRUE_FALSE/FILL_BLANK]
    A) Option A
    B) Option B
    C) Option C
    D) Option D
    Answer: A (or answer text for fill-blank)
    Marks: 2
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
                    # Add if it's a supported question type
                    if current_question.get('question_type') in ['mcq', 'true_false', 'fill_blank']:
                        questions.append(current_question)

                # Extract question type
                q_type = 'mcq'  # Default to MCQ
                if '[TRUE_FALSE]' in text.upper():
                    q_type = 'true_false'
                elif '[FILL_BLANK]' in text.upper() or '[FILL-BLANK]' in text.upper():
                    q_type = 'fill_blank'

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
                try:
                    current_question['marks'] = int(marks)
                except ValueError:
                    current_question['marks'] = 1

        # Add last question if valid
        if current_question and current_question.get('question_type') in ['mcq', 'true_false', 'fill_blank']:
            questions.append(current_question)

        return {'success': True, 'questions': questions}

    except Exception as e:
        return {'success': False, 'message': f'Error parsing Word document: {str(e)}'}


def parse_questions_from_pdf(file_path):
    """
    Parse questions from PDF document.
    Supported formats: MCQ, True/False, and Fill-in-the-Blank
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
                            # Add if it's a supported question type
                            if current_question.get('question_type') in ['mcq', 'true_false', 'fill_blank']:
                                questions.append(current_question)

                        q_type = 'mcq'
                        if '[TRUE_FALSE]' in line.upper():
                            q_type = 'true_false'
                        elif '[FILL_BLANK]' in line.upper() or '[FILL-BLANK]' in line.upper():
                            q_type = 'fill_blank'

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
                        try:
                            current_question['marks'] = int(marks)
                        except ValueError:
                            current_question['marks'] = 1

        if current_question and current_question.get('question_type') in ['mcq', 'true_false', 'fill_blank']:
            questions.append(current_question)

        return {'success': True, 'questions': questions}

    except Exception as e:
        return {'success': False, 'message': f'Error parsing PDF: {str(e)}'}


def auto_grade_answer(question, answer_text):
    """
    Auto-grade an answer based on question type.
    Supports MCQ, True/False, and Fill-in-the-Blank questions.
    Returns (is_correct, marks_obtained)
    """
    if not answer_text:
        return False, 0

    if question.question_type == 'mcq':
        is_correct = answer_text.upper().strip() == question.correct_answer.upper().strip()
        marks = question.marks if is_correct else 0
        return is_correct, marks

    elif question.question_type == 'true_false':
        is_correct = answer_text.lower().strip() == question.correct_answer.lower().strip()
        marks = question.marks if is_correct else 0
        return is_correct, marks

    elif question.question_type == 'fill_blank':
        # Case-insensitive comparison for fill-in-the-blank
        is_correct = answer_text.lower().strip() == question.correct_answer.lower().strip()
        marks = question.marks if is_correct else 0
        return is_correct, marks

    return False, 0


def export_assessment_to_pdf(assessment, attempts):
    """
    Export assessment results to PDF.
    Returns PDF bytes or None on error.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=1  # Center
        )
        title = Paragraph(f"Assessment Results: {assessment.title}", title_style)
        elements.append(title)

        # Assessment Info
        info_style = styles['Normal']
        info_data = [
            f"<b>Class:</b> {assessment.school_class.name}",
            f"<b>Subject:</b> {assessment.subject.name}",
            f"<b>Total Marks:</b> {assessment.total_marks}",
            f"<b>Pass Mark:</b> {assessment.pass_mark}%",
            f"<b>Total Students:</b> {len(attempts)}"
        ]
        for info in info_data:
            elements.append(Paragraph(info, info_style))
        elements.append(Spacer(1, 0.3 * inch))

        # Results table
        table_data = [['#', 'Student ID', 'Student Name', 'Score', 'Percentage', 'Grade', 'Status']]

        for idx, attempt in enumerate(attempts, 1):
            status = 'Pass' if attempt.percentage >= assessment.pass_mark else 'Fail'
            table_data.append([
                str(idx),
                attempt.student.student_id,
                attempt.student.full_name,
                f"{attempt.total_score}/{assessment.total_marks}",
                f"{attempt.percentage:.1f}%",
                attempt.grade,
                status
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        print(f"Error exporting to PDF: {str(e)}")
        return None


def export_assessment_to_excel(assessment, attempts):
    """
    Export assessment results to Excel.
    Returns Excel bytes or None on error.
    """
    try:
        from io import BytesIO
        import pandas as pd

        data = []
        for attempt in attempts:
            status = 'Pass' if attempt.percentage >= assessment.pass_mark else 'Fail'
            data.append({
                'Student ID': attempt.student.student_id,
                'First Name': attempt.student.first_name,
                'Last Name': attempt.student.last_name,
                'Email': attempt.student.user.email,
                'Score': f"{attempt.total_score}/{assessment.total_marks}",
                'Percentage': f"{attempt.percentage:.2f}%",
                'Grade': attempt.grade,
                'Status': status,
                'Submitted At': attempt.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if attempt.submitted_at else 'N/A'
            })

        df = pd.DataFrame(data)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Results')

            # Auto-adjust column widths
            worksheet = writer.sheets['Results']
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = max_length

        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        print(f"Error exporting to Excel: {str(e)}")
        return None


def export_student_answer_sheet(attempt):
    """
    Export student's answer sheet to PDF showing all questions and their answers.
    Returns PDF bytes or None on error.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_LEFT
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=1
        )
        title = Paragraph(f"Answer Sheet: {attempt.assessment.title}", title_style)
        elements.append(title)

        # Student Info
        info_style = styles['Normal']
        info_data = [
            f"<b>Student:</b> {attempt.student.full_name} ({attempt.student.student_id})",
            f"<b>Class:</b> {attempt.assessment.school_class.name}",
            f"<b>Subject:</b> {attempt.assessment.subject.name}",
            f"<b>Score:</b> {attempt.total_score}/{attempt.assessment.total_marks} ({attempt.percentage:.1f}%)",
            f"<b>Grade:</b> {attempt.grade}",
            f"<b>Submitted:</b> {attempt.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if attempt.submitted_at else 'N/A'}"
        ]
        for info in info_data:
            elements.append(Paragraph(info, info_style))
        elements.append(Spacer(1, 0.3 * inch))

        # Question style
        question_style = ParagraphStyle(
            'QuestionStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=8,
            leftIndent=10
        )

        answer_style = ParagraphStyle(
            'AnswerStyle',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=20,
            spaceAfter=5
        )

        # Get all answers with questions
        answers = attempt.answers
        for idx, answer in enumerate(answers, 1):
            question = answer.question

            # Question number and text
            q_text = f"<b>Q{idx}.</b> {question.question_text}"
            elements.append(Paragraph(q_text, question_style))

            # Options for MCQ
            if question.question_type == 'mcq':
                for option in ['a', 'b', 'c', 'd']:
                    option_text = getattr(question, f'option_{option}', None)
                    if option_text:
                        elements.append(Paragraph(f"{option.upper()}) {option_text}", answer_style))

            # Student's answer
            answer_color = 'green' if answer.is_correct else 'red'
            student_answer = f"<b>Your Answer:</b> <font color='{answer_color}'>{answer.answer_text or 'Not Answered'}</font>"
            elements.append(Paragraph(student_answer, answer_style))

            # Correct answer
            correct_answer = f"<b>Correct Answer:</b> {question.correct_answer}"
            elements.append(Paragraph(correct_answer, answer_style))

            # Marks
            marks_text = f"<b>Marks:</b> {answer.marks_obtained}/{question.marks}"
            elements.append(Paragraph(marks_text, answer_style))

            elements.append(Spacer(1, 0.2 * inch))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        print(f"Error exporting answer sheet: {str(e)}")
        return None
