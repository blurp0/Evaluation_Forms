from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from website.model import db, Student, Professor, Section, Course

auth = Blueprint('auth', __name__)

@auth.route('/')
def home_page():
    return render_template('home.html')


from sqlalchemy.exc import IntegrityError


# Helper function to handle registration logic
def handle_registration(form_data, user_type):
    first_name = form_data.get('first_name')
    last_name = form_data.get('last_name')
    student_id = form_data.get('student_id')  # Only for students
    email = form_data.get('email')  # Only for professors
    password = form_data.get('password')

    # Validation checks
    if not all([first_name, last_name, password]):
        flash("All fields are required!", "error")
        return False

    # Handling for students
    if user_type == 'student':
        if not student_id:
            flash("Student ID is required!", "error")
            return False

        if Student.query.filter_by(student_id=student_id).first():
            flash("Student ID is already in use!", "error")
            return False

        # Additional student fields (section_id) if needed
        section_id = form_data.get('section_id')
        if not section_id:
            flash("Section is required!", "error")
            return False

        # Creating the student
        hashed_password = generate_password_hash(password)
        new_user = Student(
            first_name=first_name,
            last_name=last_name,
            student_id=student_id,
            email=email,  # Optional for students
            password=hashed_password,
            section_id=section_id
        )

    # Handling for professors
    elif user_type == 'professor':
        if not email:
            flash("Email is required!", "error")
            return False

        if Professor.query.filter_by(email=email).first():
            flash("Email is already in use!", "error")
            return False

        # Creating the professor
        hashed_password = generate_password_hash(password)
        new_user = Professor(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password
        )

    try:
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()  # Rollback the session if there is a duplicate entry error
        flash("The email or student ID is already in use. Please try a different one.", "error")
        return False

    return new_user


@auth.route('/register', methods=['GET', 'POST'])
def register():
    # Fetch all courses for the dropdown (only needed for students)
    courses = Course.query.all()

    if request.method == 'POST':
        role = request.form.get('role')  # Get the selected role: student or professor

        if role == 'student':
            if handle_registration(request.form, 'student'):
                flash("Student account created successfully!", "success")
                return redirect(url_for('auth.login'))
        elif role == 'professor':
            if handle_registration(request.form, 'professor'):
                flash("Professor account created successfully!", "success")
                return redirect(url_for('auth.login'))
        else:
            flash("Invalid role selected.", "error")
            return redirect(url_for('auth.register'))

    return render_template('register.html', courses=courses)


@auth.route('/get_sections/<int:course_id>', methods=['GET'])
def get_sections(course_id):
    # Fetch all sections for the selected course
    sections = Section.query.filter_by(course_id=course_id).all()
    return jsonify({
        'sections': [{'id': section.id, 'name': section.name} for section in sections]
    })


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')  # Either 'student' or 'professor'
        identifier = request.form.get('identifier')  # Student ID for students, Email for professors
        password = request.form.get('password')

        if role == 'student':
            user = Student.query.filter_by(student_id=identifier).first()
        elif role == 'professor':
            user = Professor.query.filter_by(email=identifier).first()
        else:
            flash("Invalid role selected. Please try again.", "error")
            return redirect(url_for('auth.login'))

        if user and check_password_hash(user.password, password):
            # Store role in session
            session['role'] = role
            login_user(user)  # This logs in the user and sets `current_user`
            flash(f"Welcome back, {user.first_name}!", "success")

            # Redirect based on role
            if role == 'student':
                return redirect(url_for('student.home'))
            elif role == 'professor':
                return redirect(url_for('professor.homepage'))
        else:
            flash("Invalid credentials. Please try again.", "error")

    return render_template('login.html')



@auth.route('/logout')
@login_required
def logout():
    session.pop('role', None)  # Clear role from session
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))


