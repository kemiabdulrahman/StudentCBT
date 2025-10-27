from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions
mail = Mail()
csrf = CSRFProtect()
migrate = Migrate()
db = SQLAlchemy()