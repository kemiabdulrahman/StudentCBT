# StudentCBT Test Suite

Comprehensive test suite for the StudentCBT application covering models, forms, routes, utilities, and templates.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
├── test_models.py           # Model tests (User, Student, Exam, etc.)
├── test_forms.py            # Form validation tests
├── test_auth_routes.py      # Authentication and access control tests
├── test_admin_routes.py     # Admin route tests
├── test_student_routes.py   # Student route tests
├── test_utils.py            # Utility function tests
├── test_templates.py        # Template rendering tests
└── README.md                # This file
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Run only model tests
pytest tests/test_models.py

# Run only route tests
pytest tests/test_admin_routes.py tests/test_student_routes.py

# Run only auth tests
pytest tests/test_auth_routes.py
```

### Run Tests by Category

```bash
# Run tests with specific markers
pytest -m unit
pytest -m integration
pytest -m auth
pytest -m admin
pytest -m student
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=. --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

### Run in Parallel

```bash
# Run tests in parallel (faster)
pytest -n auto
```

### Verbose Output

```bash
# Show detailed test output
pytest -v

# Show even more details
pytest -vv

# Show print statements
pytest -s
```

## Test Categories

### Model Tests (`test_models.py`)
Tests for database models:
- **User**: Password hashing, authentication
- **Student**: Full name property, relationships
- **SchoolClass**: Relationships with students and subjects
- **Subject**: Relationships with classes and exams
- **Exam**: Status, results publication, relationships
- **Question**: MCQ and True/False types
- **Attempt**: Grade calculation, unique constraints
- **Answer**: Correctness checking

### Form Tests (`test_forms.py`)
Tests for form validation:
- **LoginForm**: Email and password validation
- **SchoolClassForm**: Name length, level optional
- **SubjectForm**: Required fields, class selection
- **ExamForm**: Duration, pass mark validation
- **QuestionForm**: MCQ vs True/False validation

### Authentication Tests (`test_auth_routes.py`)
Tests for authentication and access control:
- Login with valid/invalid credentials
- Logout functionality
- Inactive user handling
- Role-based access control
- Session management

### Admin Route Tests (`test_admin_routes.py`)
Tests for admin functionality:
- **Dashboard**: Statistics display
- **Class Management**: CRUD operations
- **Subject Management**: Creation, deletion
- **Student Management**: View, toggle status, delete
- **Exam Management**: Create, edit, publish, close
- **Question Management**: Add, edit, delete questions
- **Results**: Toggle publication, view attempts

### Student Route Tests (`test_student_routes.py`)
Tests for student functionality:
- **Dashboard**: View available exams
- **Start Exam**: Create attempts, prevent duplicates
- **Take Exam**: Answer questions, save progress
- **Submit Exam**: Score calculation, grading
- **View Results**: Published results only
- **Access Control**: Cannot access other students' data

### Utils Tests (`test_utils.py`)
Tests for utility functions:
- **auto_grade_answer()**: MCQ and True/False grading, case sensitivity
- **parse_excel_students()**:
  - Valid Excel parsing
  - Missing columns detection
  - Duplicate handling
  - Invalid data handling
  - User and Student creation

### Template Tests (`test_templates.py`)
Tests for template rendering:
- All admin templates render without errors
- All student templates render without errors
- Base template with different user roles
- Template inheritance
- Context variables availability
- Flash message rendering

## Fixtures

Common fixtures available in all tests (defined in `conftest.py`):

### Application Fixtures
- `app`: Flask application instance
- `client`: Test client for making requests
- `runner`: CLI test runner
- `_db`: Database with tables

### User Fixtures
- `admin_user`: Admin user account
- `student_user`: Active student user
- `inactive_student_user`: Inactive student user

### Data Fixtures
- `school_class`: Sample school class (JSS 1A)
- `subject`: Sample subject (Mathematics)
- `exam`: Draft exam
- `published_exam`: Published exam (results not published)
- `exam_with_results_published`: Exam with published results
- `question`: MCQ question
- `true_false_question`: True/False question
- `attempt`: In-progress attempt
- `submitted_attempt`: Submitted attempt
- `answer`: Sample answer

### Authenticated Clients
- `auth_client`: Client logged in as admin
- `student_auth_client`: Client logged in as student

## Writing New Tests

### Test Naming Convention

```python
class TestFeatureName:
    """Test feature description"""

    def test_specific_behavior(self, fixture1, fixture2):
        """Test that specific behavior works correctly"""
        # Arrange
        # ...

        # Act
        result = do_something()

        # Assert
        assert result == expected
```

### Using Fixtures

```python
def test_something(self, app, _db, admin_user):
    """Test using fixtures"""
    with app.app_context():
        # Use fixtures
        assert admin_user.role == 'admin'
```

### Testing Routes

```python
def test_route(self, auth_client, app):
    """Test route access"""
    with app.app_context():
        response = auth_client.get('/admin/dashboard')
        assert response.status_code == 200
        assert b'expected content' in response.data
```

### Testing Forms

```python
def test_form_validation(self, app):
    """Test form validation"""
    with app.test_request_context():
        form = MyForm(data={
            'field': 'value'
        })
        assert form.validate() is True
```

### Testing Database

```python
def test_database_operation(self, app, _db):
    """Test database operation"""
    with app.app_context():
        obj = MyModel(name='Test')
        _db.session.add(obj)
        _db.session.commit()

        retrieved = MyModel.query.filter_by(name='Test').first()
        assert retrieved is not None
```

## Coverage Goals

- **Models**: 90%+ coverage
- **Forms**: 85%+ coverage
- **Routes**: 80%+ coverage
- **Utils**: 85%+ coverage
- **Templates**: Basic rendering tests

## Common Issues

### Database Errors
If you see database errors, make sure:
- You're using the `_db` fixture
- Operations are within `app.app_context()`
- You call `_db.session.commit()` after changes

### Template Errors
If templates fail to render:
- Check all required variables are passed
- Verify fixture data is complete
- Use `with app.app_context()` or `with app.test_request_context()`

### Import Errors
If you see import errors:
- Make sure you're running from project root
- Activate virtual environment
- Install test dependencies

## Continuous Integration

To run tests in CI/CD:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pip install -r requirements-test.txt
    pytest --cov=. --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Best Practices

1. **Arrange-Act-Assert**: Structure tests clearly
2. **One assertion per test**: Keep tests focused
3. **Use fixtures**: Don't repeat setup code
4. **Test edge cases**: Not just happy paths
5. **Descriptive names**: Test names should explain what they test
6. **Independent tests**: Tests shouldn't depend on each other
7. **Clean up**: Use fixtures that auto-cleanup
8. **Mock external services**: Don't hit real APIs

## Troubleshooting

### Tests fail with "No application found"
Make sure you're using the `app` fixture and proper context:
```python
def test_something(self, app):
    with app.app_context():
        # Your test code
```

### Tests fail with "Working outside of request context"
Use `test_request_context`:
```python
def test_something(self, app):
    with app.test_request_context():
        # Your test code
```

### Database changes not persisting
Make sure to commit:
```python
_db.session.add(obj)
_db.session.commit()
```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing Documentation](https://flask.palletsprojects.com/en/latest/testing/)
- [pytest-flask Documentation](https://pytest-flask.readthedocs.io/)
