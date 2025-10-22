from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, TextAreaField, IntegerField, BooleanField, DateTimeField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional
from models import SchoolClass, Subject


class LoginForm(FlaskForm):
    """Login form for admin and student users"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class SchoolClassForm(FlaskForm):
    """Form for creating/editing school classes"""
    name = StringField('Class Name (e.g., JSS 1A)', validators=[DataRequired(), Length(max=50)])
    level = StringField('Level (e.g., JSS1, SS2)', validators=[Length(max=20)])
    submit = SubmitField('Save Class')


class SubjectForm(FlaskForm):
    """Form for creating/editing subjects"""
    name = StringField('Subject Name', validators=[DataRequired(), Length(max=100)])
    code = StringField('Subject Code', validators=[Length(max=20)])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Subject')

    def __init__(self, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)
        self.class_id.choices = [(c.id, c.name) for c in SchoolClass.query.order_by(SchoolClass.name).all()]


class StudentUploadForm(FlaskForm):
    """Form for bulk uploading students from Excel"""
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    excel_file = FileField('Excel File', validators=[
        DataRequired(),
        FileAllowed(['xlsx', 'xls'], 'Excel files only!')
    ])
    submit = SubmitField('Upload Students')

    def __init__(self, *args, **kwargs):
        super(StudentUploadForm, self).__init__(*args, **kwargs)
        self.class_id.choices = [(c.id, c.name) for c in SchoolClass.query.order_by(SchoolClass.name).all()]


class ExamForm(FlaskForm):
    """Form for creating/editing exams"""
    title = StringField('Exam Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    subject_id = SelectField('Subject', coerce=int, validators=[DataRequired()])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    duration_minutes = IntegerField('Duration (Minutes)', validators=[DataRequired(), NumberRange(min=1)])
    pass_mark = IntegerField('Pass Mark (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    scheduled_start = DateTimeField('Scheduled Start (Optional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    scheduled_end = DateTimeField('Scheduled End (Optional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    submit = SubmitField('Save Exam')

    def __init__(self, *args, **kwargs):
        super(ExamForm, self).__init__(*args, **kwargs)
        self.subject_id.choices = [(s.id, f"{s.name} - {s.school_class.name}")
                                   for s in Subject.query.join(SchoolClass).order_by(Subject.name).all()]
        self.class_id.choices = [(c.id, c.name) for c in SchoolClass.query.order_by(SchoolClass.name).all()]


class QuestionForm(FlaskForm):
    """Form for creating/editing questions - only MCQ and True/False"""
    question_text = TextAreaField('Question Text', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False')
    ], validators=[DataRequired()])
    marks = IntegerField('Marks', validators=[DataRequired(), NumberRange(min=1)])

    # MCQ Options
    option_a = StringField('Option A')
    option_b = StringField('Option B')
    option_c = StringField('Option C')
    option_d = StringField('Option D')

    # Correct answer: 'A', 'B', 'C', 'D' for MCQ or 'True', 'False' for True/False
    correct_answer = StringField('Correct Answer', validators=[DataRequired()])

    submit = SubmitField('Add Question')


class QuestionUploadForm(FlaskForm):
    """Form for bulk uploading questions from Word/PDF"""
    file = FileField('Upload Questions', validators=[
        DataRequired(),
        FileAllowed(['docx', 'pdf'], 'Word or PDF files only!')
    ])
    submit = SubmitField('Upload Questions')


class EmptyForm(FlaskForm):
    """Empty form for CSRF protection in simple actions"""
    submit = SubmitField("Submit")
