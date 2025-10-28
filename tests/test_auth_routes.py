"""
Test authentication routes
"""
import pytest
from flask import url_for


class TestLogin:
    """Test login route"""

    def test_login_page_loads(self, client):
        """Test that login page loads"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data

    def test_login_with_valid_credentials(self, client, admin_user, app):
        """Test login with valid credentials"""
        with app.app_context():
            response = client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            assert response.status_code == 200
            # Should redirect to dashboard
            assert b'Dashboard' in response.data or b'dashboard' in response.data

    def test_login_with_invalid_password(self, client, admin_user, app):
        """Test login with invalid password"""
        with app.app_context():
            response = client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'wrongpassword'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'Invalid' in response.data or b'invalid' in response.data

    def test_login_with_invalid_email(self, client, app):
        """Test login with non-existent email"""
        with app.app_context():
            response = client.post('/login', data={
                'email': 'nonexistent@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'Invalid' in response.data or b'invalid' in response.data

    def test_login_with_inactive_user(self, client, inactive_student_user, app):
        """Test login with inactive user"""
        with app.app_context():
            response = client.post('/login', data={
                'email': 'inactive@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'deactivated' in response.data or b'inactive' in response.data.lower()

    def test_login_redirects_based_on_role(self, client, student_user, app):
        """Test that login redirects to correct dashboard based on role"""
        with app.app_context():
            # Login as student
            response = client.post('/login', data={
                'email': 'student@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            assert response.status_code == 200
            # Should see student content
            assert b'Exams' in response.data or b'exams' in response.data


class TestLogout:
    """Test logout route"""

    def test_logout_redirects_to_login(self, auth_client, app):
        """Test that logout redirects to login"""
        with app.app_context():
            response = auth_client.get('/logout', follow_redirects=True)
            assert response.status_code == 200
            assert b'Login' in response.data or b'login' in response.data

    def test_logout_clears_session(self, client, admin_user, app):
        """Test that logout clears the session"""
        with app.app_context():
            # Login
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            })

            # Logout
            client.get('/logout')

            # Try to access protected route
            response = client.get('/admin/dashboard', follow_redirects=True)
            # Should be redirected to login
            assert b'Login' in response.data or b'login' in response.data


class TestAccessControl:
    """Test access control"""

    def test_unauthenticated_cannot_access_admin(self, client, app):
        """Test that unauthenticated users cannot access admin routes"""
        with app.app_context():
            response = client.get('/admin/dashboard', follow_redirects=True)
            assert response.status_code == 200
            # Should be redirected to login
            assert b'Login' in response.data or b'login' in response.data

    def test_unauthenticated_cannot_access_student(self, client, app):
        """Test that unauthenticated users cannot access student routes"""
        with app.app_context():
            response = client.get('/student/dashboard', follow_redirects=True)
            assert response.status_code == 200
            # Should be redirected to login
            assert b'Login' in response.data or b'login' in response.data

    def test_student_cannot_access_admin(self, student_auth_client, app):
        """Test that students cannot access admin routes"""
        with app.app_context():
            response = student_auth_client.get('/admin/dashboard', follow_redirects=True)
            assert response.status_code == 200
            # Should see access denied message
            assert b'denied' in response.data.lower() or b'Login' in response.data

    def test_admin_cannot_access_student_routes(self, auth_client, app):
        """Test that admins cannot access student routes"""
        with app.app_context():
            response = auth_client.get('/student/dashboard', follow_redirects=True)
            assert response.status_code == 200
            # Should see access denied message
            assert b'denied' in response.data.lower() or b'Login' in response.data
