from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from flask_login import LoginManager

# Initialize db and login manager globally
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'GERM'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/evaluations'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize the database and Flask-Migrate
    db.init_app(app)
    migrate = Migrate(app, db)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Where to redirect if login required

    # Register blueprints
    from .views_student import student
    from .views_professor import professor
    from .views_admin import admin
    from .auth import auth

    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(student, url_prefix='/student')
    app.register_blueprint(professor, url_prefix='/professor')
    app.register_blueprint(admin, url_prefix='/admin')

    # APScheduler setup
    scheduler = BackgroundScheduler()

    def update_form_statuses():
        # Ensure we're inside the Flask app context to access the database
        with app.app_context():  # Use app.app_context() instead of current_app.app_context()
            from .model import FormDistribution  # Import here to avoid circular import
            form_distributions = FormDistribution.query.all()

            for form_distribution in form_distributions:
                if form_distribution.is_deadline_missed():  # Check if the deadline is missed
                    form_distribution.update_status()  # Update the status of the form

            db.session.commit()  # Commit the changes

    # Schedule the task to run every 10 minutes
    scheduler.add_job(update_form_statuses, 'interval', minutes=60)
    scheduler.start()

    return app

# Define the user loader to load user from the session by user_id
from .model import Student, Professor
from flask import session

@login_manager.user_loader
def load_user(user_id):
    role = session.get('role')

    if role == 'student':
        return Student.query.get(int(user_id))
    elif role == 'professor':
        return Professor.query.get(int(user_id))

    return None

