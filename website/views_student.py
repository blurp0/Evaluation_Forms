from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from website import db
from collections import defaultdict
from website.model import Student, EvaluationForm, Section, Course, FormDistribution, QuestionCategory, \
    Question, Answer, ProfessorSectionSubject, Professor, Subject, CategoryRawAnswer, ProfessorPerformance, \
    StudentFormStatus

student = Blueprint('student', __name__, url_prefix='/student')


@student.route('/')
@login_required
def home():
    student = current_user  # Get the current logged-in student

    student_name = student.first_name + " " + student.last_name

    # Fetch the number of pending, completed, and missing evaluations for this student based on FormDistribution
    pending_evaluations = StudentFormStatus.query.filter_by(
        student_id=student.id,
        status='pending'
    ).join(FormDistribution).filter(FormDistribution.section_id == student.section_id).count()

    completed_evaluations = StudentFormStatus.query.filter_by(
        student_id=student.id,
        status='completed'
    ).join(FormDistribution).filter(FormDistribution.section_id == student.section_id).count()

    missing_evaluations = StudentFormStatus.query.filter_by(
        student_id=student.id,
        status='missing'
    ).join(FormDistribution).filter(FormDistribution.section_id == student.section_id).count()

    return render_template(
        'student/overview.html',
        student_name=student_name,
        pending_evaluations=pending_evaluations,
        completed_evaluations=completed_evaluations,
        missing_evaluations=missing_evaluations
    )


# Profile edit route: Allow students to edit their profile
@student.route('/profile/edit', methods=['GET', 'POST'])
@login_required  # Ensure the user is logged in before they can access this view
def edit_profile():
    user = current_user  # Get the current logged-in student

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        age = request.form.get('age')

        # Validation
        if not first_name or not last_name or not email:
            flash("All fields are required.", "error")
            return render_template('student/edit_profile.html', user=user)

        # Update user info
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.age = age

        # Commit changes to the database
        db.session.commit()

        flash("Profile updated successfully!", "success")
        return redirect(url_for('student.profile'))

    return render_template('student/edit_profile.html', user=user)

# Route for getting sections of a specific course
@student.route('/get_sections/<int:course_id>', methods=['GET'])
def get_sections(course_id):
    sections = Section.query.filter_by(course_id=course_id).all()
    return jsonify({
        'sections': [{'id': section.id, 'name': section.name} for section in sections]
    })

# Profile route: View profile details of the student
@student.route('/profile')
@login_required  # Ensure the user is logged in before they can access this view
def profile():
    user = current_user  # Get the current logged-in student
    section = user.section
    course = section.course if section else None

    return render_template('student/profile.html', user=user, section=section, course=course)

# Manage forms: List all forms distributed to the student's section

# View form: View a specific form's details
@student.route('/form/<int:form_distribution_id>/view')
@login_required
def open_form(form_distribution_id):
    student = current_user

    # Fetch the FormDistribution using form_distribution_id
    form_distribution = FormDistribution.query.get_or_404(form_distribution_id)

    # Ensure the form is for the correct section
    if form_distribution.section_id != student.section_id:
        flash("You do not have access to this form.", "error")
        return redirect(url_for('student.pending_forms'))

    # Fetch the form, professor, and subject directly from the FormDistribution
    form = form_distribution.form  # Get the related EvaluationForm
    professor_name = f"{form_distribution.professor.first_name} {form_distribution.professor.last_name}"
    subject_name = form_distribution.subject.name

    # Check if the student has already submitted the form
    existing_answer = Answer.query.filter_by(form_distribution_id=form_distribution.id, student_id=student.id).first()

    if existing_answer:
        flash("You have already submitted this form.", "error")
        return redirect(url_for('student.pending_forms'))

    # Group questions by category ID for rendering
    categories = {}
    for question in form.questions:
        # Retrieve category name using the category_id from QuestionCategory model
        category = QuestionCategory.query.get(question.category_id)
        category_name = category.name

        # Group questions by category_id and store the category name for rendering
        categories.setdefault(question.category_id, {'name': category_name, 'questions': []})['questions'].append(question)

    return render_template('student/open_form.html', form=form, categories=categories,
                           professor_name=professor_name, subject_name=subject_name, form_distribution=form_distribution)

@student.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    student = current_user

    # Retrieve form_distribution_id from the form submission
    form_distribution_id = request.form.get('form_distribution_id')
    if not form_distribution_id:
        flash("Form distribution ID is missing.", "error")
        return redirect(url_for('student.pending_forms'))

    # Fetch the FormDistribution record
    form_distribution = FormDistribution.query.get_or_404(form_distribution_id)

    # Ensure the student belongs to the section of this form distribution
    if form_distribution.section_id != student.section_id:
        flash("You do not have access to this form.", "error")
        return redirect(url_for('student.pending_forms'))

    # Check if the student already submitted an answer for this form_distribution
    existing_answer = Answer.query.filter_by(
        form_distribution_id=form_distribution_id,
        student_id=student.id
    ).first()
    if existing_answer:
        flash("You have already submitted this form.", "error")
        return redirect(url_for('student.pending_forms'))

    # Group answers by category
    categories = {}
    for question in form_distribution.form.questions:
        # Skip "Comments / Suggestions" category and handle it separately
        if question.manage_category.name == "Comments / Suggestions":
            continue

        question_key = f"question_{question.id}"
        answer_value = request.form.get(question_key)

        if answer_value is None:
            flash(f"Missing answer for question ID {question.id}.", "error")
            return redirect(url_for('student.open_form', form_distribution_id=form_distribution_id))

        # Group ratings by category ID
        category_id = question.manage_category.id
        categories.setdefault(category_id, []).append(int(answer_value))

    # Get subject_id from form_distribution (because each form_distribution relates to a specific subject)
    subject_id = form_distribution.subject_id  # This is the subject associated with the form_distribution

    # Calculate average rating per category and prepare Answer objects
    answers = []
    for category_id, ratings in categories.items():
        average_rating = sum(ratings) / len(ratings)
        answer = Answer(
            form_id=form_distribution.form_id,
            student_id=student.id,
            form_distribution_id=form_distribution_id,
            answer_value=round(average_rating, 2),  # Rounded to 2 decimal places
            category_id=category_id,  # Now storing the category ID instead of the name
            subject_id=subject_id  # Use the subject_id from the form_distribution
        )
        db.session.add(answer)
        db.session.flush()  # Flush to make sure the answer gets inserted and answer_id is set

        # Now store the raw answers for this category in the CategoryRawAnswer table
        for rating in ratings:
            raw_category_answer = CategoryRawAnswer(
                answer_id=answer.id,  # Link to the newly inserted Answer
                category_id=category_id,  # Store the category ID in raw answers
                raw_answer_value=rating
            )
            db.session.add(raw_category_answer)

    # Handle optional comments or suggestions separately
    comments_key = "category_Comments / Suggestions"
    comment = request.form.get(comments_key, "").strip()  # Safely get the comment with a default empty string
    if comment:  # Check if comment is non-empty after stripping
        # Store the comment in the Answer model first
        answer = Answer(
            form_id=form_distribution.form_id,
            student_id=student.id,
            form_distribution_id=form_distribution_id,
            comment=comment,
            category_id=None,  # No category_id for comments
            subject_id=subject_id  # Use the subject_id from the form_distribution
        )
        db.session.add(answer)  # Save the answer first to generate the answer_id
        db.session.flush()  # Flush to make sure the answer is inserted, and the ID is generated

        # No CategoryRawAnswer insertion for comments, we skip it entirely
        # No need to insert raw answers for comments

    # Commit all answers to the database
    db.session.commit()

    # After submission, update the student's form status to 'completed'
    student_form_status = StudentFormStatus.query.filter_by(
        student_id=student.id,
        form_distribution_id=form_distribution.id
    ).first()

    if student_form_status:
        student_form_status.status = 'completed'
        student_form_status.completed_on = datetime.utcnow()  # Timestamp when the form was completed
    else:
        # If no existing record, create a new entry
        student_form_status = StudentFormStatus(
            student_id=student.id,
            form_distribution_id=form_distribution.id,
            status='completed',
            completed_on=datetime.utcnow()  # Timestamp for completion
        )
        db.session.add(student_form_status)

    # Commit the changes to the database
    db.session.commit()

    # Calculate and update professor's performance
    update_professor_performance(form_distribution.professor_id, form_distribution.subject_id, categories)

    flash("Your evaluation has been successfully submitted!", "success")
    return redirect(url_for('student.pending_forms'))

def update_professor_performance(professor_id, subject_id, categories):
    total_performance = 0
    total_category_averages = {}
    total_category_count = {}

    # Loop through each category and its ratings
    for category_id, ratings in categories.items():
        # Avoid division by zero if there are no ratings
        if len(ratings) > 0:
            average_grade = sum(ratings) / len(ratings)
        else:
            average_grade = 0  # Default to 0 if no ratings

        # Check if a performance record already exists for this professor, category, and subject
        existing_performance = ProfessorPerformance.query.filter_by(
            professor_id=professor_id,
            subject_id=subject_id,  # Filter by subject as well
            category_id=category_id
        ).first()

        if existing_performance:
            # If the record exists, calculate a weighted average based on the existing grades
            total_ratings_count = existing_performance.total_ratings_count  # The total ratings count before
            new_ratings_count = len(ratings)  # The new ratings count
            combined_ratings_count = total_ratings_count + new_ratings_count

            # Calculate the new average as the weighted average of old and new ratings
            new_average_grade = (
                (existing_performance.average_grade * total_ratings_count) +
                (average_grade * new_ratings_count)
            ) / combined_ratings_count
            existing_performance.average_grade = round(new_average_grade, 2)
            existing_performance.total_ratings_count = combined_ratings_count  # Update the total ratings count
            existing_performance.updated_at = datetime.utcnow()
        else:
            # Create a new performance record if it does not exist
            new_performance = ProfessorPerformance(
                professor_id=professor_id,
                subject_id=subject_id,
                category_id=category_id,  # Use category ID
                average_grade=round(average_grade, 2),
                total_ratings_count=len(ratings)  # Store the ratings count for future averaging
            )
            db.session.add(new_performance)

        # Add the category's average grade to the professor's overall performance calculation
        total_performance += average_grade
        total_category_averages[category_id] = round(average_grade, 2)
        total_category_count[category_id] = len(ratings)

    # Update the overall performance of the professor across all subjects and categories
    professor = Professor.query.get(professor_id)

    # Get all the average grades from the ProfessorPerformance model (no subject filter for overall performance)
    performances = ProfessorPerformance.query.filter_by(professor_id=professor_id).all()

    # Calculate the professor's overall performance (average of all categories across all subjects)
    if performances:
        overall_average = sum(p.average_grade for p in performances) / len(performances)
    else:
        overall_average = 0

    # Update professor model with overall performance
    professor.overall_performance = round(overall_average, 2)
    professor.category_performance = total_category_averages  # Store category-wise performance in JSON format

    # Commit the changes to the database
    db.session.commit()


@student.route('/pending_forms')
@login_required
def pending_forms():
    student = current_user  # Get the current logged-in student

    # Fetch all subjects related to the student's section through ProfessorSectionSubject
    section = student.section  # The section the student is assigned to
    subject_ids = [pss.subject_id for pss in section.professors_subjects]  # Get all subject IDs in this section

    # Fetch form distributions where the student's status is 'pending'
    form_distributions = (
        db.session.query(FormDistribution)
        .join(StudentFormStatus)
        .filter(
            FormDistribution.section_id == student.section_id,  # Forms assigned to student's section
            FormDistribution.subject_id.in_(subject_ids),  # Forms assigned to subjects the student is enrolled in
            StudentFormStatus.student_id == student.id,  # Forms for the logged-in student
            StudentFormStatus.status == 'pending'  # Only fetch pending forms
        )
        .all()
    )

    # Prepare form_info for each pending form
    pending_forms = []
    for distribution in form_distributions:
        # Create form info to pass to the open_form
        form_info = {
            'form': distribution.form,
            'professor_name': f"{distribution.professor.first_name} {distribution.professor.last_name}",
            'subject_name': distribution.subject.name,
            'form_distribution_id': distribution.id,
            'status': 'pending',  # We are filtering for 'pending' status
            'deadline': distribution.deadline  # Use deadline from FormDistribution
        }

        pending_forms.append(form_info)

    # Return the list of pending forms to the template
    return render_template('student/pending_forms.html', pending_forms=pending_forms)

@student.route('/completed_forms')
@login_required
def completed_forms():
    student = current_user  # Get the current logged-in student

    # Fetch all forms where the student's status is 'completed'
    completed_forms = (
        db.session.query(FormDistribution)
        .join(StudentFormStatus)
        .filter(
            FormDistribution.section_id == student.section_id,  # Forms assigned to student's section
            StudentFormStatus.student_id == student.id,  # Forms for the logged-in student
            StudentFormStatus.status == 'completed'  # Student's status is 'completed'
        )
        .all()
    )

    # Return the rendered page with completed forms
    return render_template('student/completed_forms.html', status='completed', forms=completed_forms)

@student.route('/missing_forms')
@login_required
def missing_forms():
    student = current_user  # Get the current logged-in student

    # Fetch all forms where the deadline has passed and the student's status is 'missing'
    missing_forms = (
        db.session.query(FormDistribution)
        .join(StudentFormStatus)
        .filter(
            FormDistribution.section_id == student.section_id,  # Forms assigned to student's section
            StudentFormStatus.student_id == student.id,  # Forms for the logged-in student
            StudentFormStatus.status == 'missing',  # Student's status is 'missing'
            FormDistribution.deadline < datetime.utcnow()  # Deadline has passed
        )
        .all()
    )

    # Return the rendered page with missing forms
    return render_template('student/missing_forms.html', status='missing', forms=missing_forms)
















