# CBT Platform - MVP

A streamlined Computer-Based Testing (CBT) platform for educational institutions. This MVP version focuses on simplicity and ease of use, with automatic grading for MCQ and True/False questions.

## Features

### Admin Features
- Manage school classes and subjects
- Bulk upload students from Excel
- Create and manage exams
- Add questions manually or bulk upload from Word/PDF files
- Publish/close exams
- View student attempts and results
- Support MCQ and True/False question types only

### Student Features
- View available exams
- Take exams with countdown timer
- One attempt per exam (no retakes)
- Instant results after submission (automatic grading)
- Resume exam if interrupted

### Key Characteristics
- **Two user roles only**: Admin and Student
- **Automatic grading**: All questions are auto-graded (MCQ and True/False)
- **One attempt per exam**: Students get one chance per exam
- **No complex workflows**: No terms, sessions, or result publication
- **Simple and fast**: Students come, take exam, see results, and leave

## Tech Stack

- **Backend**: Flask 3.0
- **Database**: SQLite (can upgrade to PostgreSQL)
- **Frontend**: Tailwind CSS 4, Vanilla JavaScript
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF with CSRF protection

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd StudentCBT
```

### 2. Create a virtual environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and update the following:
# - SECRET_KEY: Generate a strong secret key
# - DATABASE_URI: (Optional) Set to PostgreSQL URI for production
# - MAIL_* variables: (Optional) Configure if you need email functionality
```

To generate a secure SECRET_KEY:
```python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Initialize the database

```bash
python app.py
```

The application will automatically:
- Create the database tables
- Create a default admin user (email: admin@cbt.com, password: admin123)

**Important**: Change the default admin password immediately after first login!

## Running the Application

### Development Mode

```bash
python app.py
```

The application will run on `http://localhost:5000`

Default admin credentials:
- **Email**: admin@cbt.com
- **Password**: admin123

### Production Mode

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Or use the provided production configuration:

```bash
export FLASK_ENV=production
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Database Migrations (Optional)

If you need to make changes to the database schema:

```bash
# Initialize migrations (first time only)
flask db init

# Create a migration
flask db migrate -m "Description of changes"

# Apply the migration
flask db upgrade
```

## Usage Guide

### For Administrators

1. **Login** with admin credentials
2. **Create Classes**: Add school classes (e.g., "JSS 1A", "SS2 Science")
3. **Create Subjects**: Add subjects for each class
4. **Upload Students**: Use Excel template to bulk upload students
5. **Create Exams**: Set up exams with duration, pass mark, and optional scheduling
6. **Add Questions**:
   - Add questions manually one by one
   - Or bulk upload from Word/PDF files
7. **Publish Exam**: Make the exam available to students
8. **Monitor**: View student attempts and results

### For Students

1. **Login** with credentials provided by admin
2. **View Dashboard**: See all available exams
3. **Start Exam**: Click on an exam to start (one attempt only!)
4. **Take Exam**: Answer questions within the time limit
5. **Submit**: Review and submit your answers
6. **View Results**: See your score, grade, and correct answers immediately

## Excel Upload Format

### Students Upload

Create an Excel file with the following columns:

| student_id | first_name | last_name | email | password |
|------------|------------|-----------|-------|----------|
| STU001 | John | Doe | john@example.com | password123 |
| STU002 | Jane | Smith | jane@example.com | password456 |

## Question Upload Format

### Word/PDF Format

```
Q1. [MCQ] What is the capital of Nigeria?
A) Lagos
B) Abuja
C) Kano
D) Port Harcourt
Answer: B
Marks: 1

Q2. [TRUE_FALSE] Python is a programming language
Answer: True
Marks: 1

Q3. [MCQ] Which of the following is a prime number?
A) 4
B) 6
C) 7
D) 8
Answer: C
Marks: 2
```

**Notes:**
- Use `[MCQ]` for multiple choice questions
- Use `[TRUE_FALSE]` for true/false questions
- Answer must be A, B, C, D for MCQ or True/False for true/false
- Marks field is optional (defaults to 1)

## Project Structure

```
StudentCBT/
├── app.py                  # Application entry point
├── config.py               # Configuration settings
├── models.py               # Database models
├── forms.py                # WTForms definitions
├── utils.py                # Utility functions
├── extensions.py           # Flask extensions
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── .gitignore             # Git ignore rules
├── routes/
│   ├── auth.py            # Authentication routes
│   ├── admin.py           # Admin routes
│   └── student.py         # Student routes
├── templates/             # Jinja2 templates
│   ├── base.html
│   ├── auth/
│   ├── admin/
│   └── student/
└── instance/              # Instance-specific files (not in git)
    └── cbt_app.db         # SQLite database
```

## Security Considerations

1. **Change default admin password** immediately after first login
2. **Use strong SECRET_KEY** in production
3. **Use HTTPS** in production
4. **Set secure session cookies** (SESSION_COOKIE_SECURE=True with HTTPS)
5. **Regular backups** of the database
6. **Keep dependencies updated** for security patches

## Troubleshooting

### Database locked error
This usually happens with SQLite when multiple processes try to write. For production, use PostgreSQL.

### Import errors
Make sure you're in the virtual environment and all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Port already in use
Change the port in `app.py` or kill the process using the port:
```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>
```

## Future Enhancements

Potential features for future versions:
- Question randomization
- Exam analytics and statistics
- Student performance reports
- Multiple language support
- Mobile app
- Question bank management
- Import/export functionality

## License

This project is proprietary software for CDSSM Ibadan.

## Support

For support, please contact the system administrator.

## Acknowledgments

Built with Flask and love for education.
