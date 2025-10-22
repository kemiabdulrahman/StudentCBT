from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, TextAreaField, IntegerField, BooleanField, DateField, DateTimeField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError, NumberRange, Optional
from models import User, AcademicSession, Term, SchoolClass, Subject


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class AcademicSessionForm(FlaskForm):
    name = StringField('Session Name (e.g., 2024/2025)', validators=[DataRequired(), Length(max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    is_current = BooleanField('Set as Current Session')
    submit = SubmitField('Create Session')


class TermForm(FlaskForm):
    session_id = SelectField('Academic Session', coerce=int, validators=[DataRequired()])
    name = StringField('Term Name (e.g., First Term)', validators=[DataRequired(), Length(max=50)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    is_current = BooleanField('Set as Current Term')
    submit = SubmitField('Create Term')
    
    def __init__(self, *args, **kwargs):
        super(TermForm, self).__init__(*args, **kwargs)
        self.session_id.choices = [(s.id, s.name) for s in AcademicSession.query.order_by(AcademicSession.name.desc()).all()]


class SchoolClassForm(FlaskForm):
    name = StringField('Class Name (e.g., JSS 1A)', validators=[DataRequired(), Length(max=50)])
    level = StringField('Level (e.g., JSS1, SS2)', validators=[Length(max=20)])
    submit = SubmitField('Create Class')


class SubjectForm(FlaskForm):
    name = StringField('Subject Name', validators=[DataRequired(), Length(max=100)])
    code = StringField('Subject Code', validators=[Length(max=20)])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    teacher_id = SelectField('Teacher', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Subject')
    
    def __init__(self, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)
        from models import Teacher
        self.class_id.choices = [(c.id, c.name) for c in SchoolClass.query.order_by(SchoolClass.name).all()]
        self.teacher_id.choices = [(t.id, f"{t.full_name} ({t.teacher_id})") for t in Teacher.query.order_by(Teacher.first_name).all()]


class StudentUploadForm(FlaskForm):
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    excel_file = FileField('Excel File', validators=[
        DataRequired(),
        FileAllowed(['xlsx', 'xls'], 'Excel files only!')
    ])
    submit = SubmitField('Upload Students')
    
    def __init__(self, *args, **kwargs):
        super(StudentUploadForm, self).__init__(*args, **kwargs)
        self.class_id.choices = [(c.id, c.name) for c in SchoolClass.query.order_by(SchoolClass.name).all()]


class TeacherUploadForm(FlaskForm):
    excel_file = FileField('Excel File', validators=[
        DataRequired(),
        FileAllowed(['xlsx', 'xls'], 'Excel files only!')
    ])
    submit = SubmitField('Upload Teachers')


class ExamForm(FlaskForm):
    title = StringField('Exam Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    subject_id = SelectField('Subject', coerce=int, validators=[DataRequired()])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    term_id = SelectField('Term', coerce=int, validators=[DataRequired()])
    duration_minutes = IntegerField('Duration (Minutes)', validators=[DataRequired(), NumberRange(min=1)])
    pass_mark = IntegerField('Pass Mark (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    allow_multiple_attempts = BooleanField('Allow Multiple Attempts')
    max_attempts = IntegerField('Max Attempts', validators=[Optional(), NumberRange(min=1)])
    scheduled_start = DateTimeField('Scheduled Start (Optional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    scheduled_end = DateTimeField('Scheduled End (Optional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    submit = SubmitField('Create Exam')
    
    def __init__(self, teacher_id=None, *args, **kwargs):
        super(ExamForm, self).__init__(*args, **kwargs)
        
        # Filter subjects by teacher
        if teacher_id:
            self.subject_id.choices = [(s.id, f"{s.name} - {s.school_class.name}") 
                                       for s in Subject.query.filter_by(teacher_id=teacher_id).all()]
            # Get unique classes from teacher's subjects
            classes = set()
            for subject in Subject.query.filter_by(teacher_id=teacher_id).all():
                classes.add((subject.class_id, subject.school_class.name))
            self.class_id.choices = sorted(list(classes), key=lambda x: x[1])
        else:
            self.subject_id.choices = [(s.id, f"{s.name} - {s.school_class.name}") 
                                       for s in Subject.query.all()]
            self.class_id.choices = [(c.id, c.name) for c in SchoolClass.query.order_by(SchoolClass.name).all()]
        
        self.term_id.choices = [(t.id, f"{t.name} - {t.session.name}") 
                               for t in Term.query.join(AcademicSession).order_by(AcademicSession.name.desc()).all()]


class QuestionForm(FlaskForm):
    question_text = TextAreaField('Question Text', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay')
    ], validators=[DataRequired()])
    marks = IntegerField('Marks', validators=[DataRequired(), NumberRange(min=1)])
    
    # MCQ Options
    option_a = StringField('Option A')
    option_b = StringField('Option B')
    option_c = StringField('Option C')
    option_d = StringField('Option D')
    correct_answer = StringField('Correct Answer (A/B/C/D or True/False)')
    
    # Keywords for auto-grading
    keywords = StringField('Keywords (comma-separated, for short answer/essay)')
    
    submit = SubmitField('Add Question')


class QuestionUploadForm(FlaskForm):
    file = FileField('Upload Questions', validators=[
        DataRequired(),
        FileAllowed(['docx', 'pdf'], 'Word or PDF files only!')
    ])
    submit = SubmitField('Upload Questions')


class GradeAnswerForm(FlaskForm):
    marks_obtained = IntegerField('Marks Obtained', validators=[DataRequired(), NumberRange(min=0)])
    teacher_feedback = TextAreaField('Feedback (Optional)')
    submit = SubmitField('Submit Grade')


class PublishResultForm(FlaskForm):
    send_email = BooleanField('Send Email Notification', default=True)
    submit = SubmitField('Publish Result')


class EmptyForm(FlaskForm):
    """Just for CSRF protection in simple actions."""
    submit = SubmitField("Submit")
