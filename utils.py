import pandas as pd
from docx import Document
import PyPDF2
import re
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
    Supported formats: MCQ and True/False only

    Expected format:
    Q1. Question text? [MCQ/TRUE_FALSE]
    A) Option A
    B) Option B
    C) Option C
    D) Option D
    Answer: A
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
                    # Only add if it's MCQ or True/False
                    if current_question.get('question_type') in ['mcq', 'true_false']:
                        questions.append(current_question)

                # Extract question type
                q_type = 'mcq'  # Default to MCQ
                if '[TRUE_FALSE]' in text.upper():
                    q_type = 'true_false'

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
        if current_question and current_question.get('question_type') in ['mcq', 'true_false']:
            questions.append(current_question)

        return {'success': True, 'questions': questions}

    except Exception as e:
        return {'success': False, 'message': f'Error parsing Word document: {str(e)}'}


def parse_questions_from_pdf(file_path):
    """
    Parse questions from PDF document.
    Supported formats: MCQ and True/False only
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
                            # Only add if it's MCQ or True/False
                            if current_question.get('question_type') in ['mcq', 'true_false']:
                                questions.append(current_question)

                        q_type = 'mcq'
                        if '[TRUE_FALSE]' in line.upper():
                            q_type = 'true_false'

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

        if current_question and current_question.get('question_type') in ['mcq', 'true_false']:
            questions.append(current_question)

        return {'success': True, 'questions': questions}

    except Exception as e:
        return {'success': False, 'message': f'Error parsing PDF: {str(e)}'}


def auto_grade_answer(question, answer_text):
    """
    Auto-grade an answer based on question type.
    Only supports MCQ and True/False questions.
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

    return False, 0

def validate_parsed_questions(questions):
    for idx, q in enumerate(questions, start=1):
        if not q.get('question_text'):
            return (False, f"Question {idx} has no text.")
        if q['question_type'] == 'mcq':
            if not all([q.get('option_a'), q.get('option_b')]):
                return (False, f"Question {idx} is missing MCQ options.")
        if not q.get('correct_answer'):
            return (False, f"Question {idx} has no answer.")
    return (True, None)
