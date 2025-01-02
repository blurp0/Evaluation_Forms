from collections import defaultdict
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from .algorithms import linear_search
from .model import EvaluationForm, Question, Course, Section, Student, Subject, Professor, QuestionCategory, \
    FormDistribution, ProfessorSectionSubject, Answer, ProfessorPerformance, StudentFormStatus
from . import db

admin = Blueprint('admin', __name__)

@admin.route('/')
def home():
    # Count forms by status
    pending_count = db.session.query(StudentFormStatus).filter(StudentFormStatus.status == 'pending').count()
    completed_count = db.session.query(StudentFormStatus).filter(StudentFormStatus.status == 'completed').count()
    missing_count = db.session.query(StudentFormStatus).filter(StudentFormStatus.status == 'missing').count()

    # Count the number of students and professors
    student_count = db.session.query(Student).count()
    professor_count = db.session.query(Professor).count()

    # Get the top 1 professor by overall performance, if any
    top_professor_overall = db.session.query(Professor).order_by(Professor.overall_performance.desc()).first()

    # Get professors, their courses, and subjects, along with their performance
    professor_performance_by_course = {}

    # Query to get all courses
    courses = db.session.query(Course).all()

    # Function to generate acronym from category name
    def generate_acronym(category_name):
        words = category_name.split()
        acronym = ''.join([word[0].upper() for word in words])
        return acronym

    # Create a set to hold all categories
    all_categories = set()  # Keep track of all categories across all courses
    for course in courses:
        professor_performance_by_course[course.name] = {}

        # Get all sections for the course
        sections = db.session.query(Section).filter(Section.course_id == course.id).all()

        for section in sections:
            # Get professors and subjects for each section
            professor_section_subjects = db.session.query(ProfessorSectionSubject) \
                .filter(ProfessorSectionSubject.section_id == section.id) \
                .all()

            # Calculate the average performance for each category within the course
            for pss in professor_section_subjects:
                professor = pss.professor
                subject = pss.subject

                # Get the performance data for the professor in the subject and each category
                performance_data = db.session.query(
                    QuestionCategory.name.label('category_name'),
                    func.avg(ProfessorPerformance.average_grade).label('average_performance')
                ).join(
                    QuestionCategory, QuestionCategory.id == ProfessorPerformance.category_id
                ).filter(
                    ProfessorPerformance.professor_id == professor.id,
                    ProfessorPerformance.subject_id == subject.id
                ).group_by(
                    QuestionCategory.id
                ).all()

                # Aggregate the average performance by category for the course
                for category, avg_performance in performance_data:
                    if category not in professor_performance_by_course[course.name]:
                        professor_performance_by_course[course.name][category] = []
                    professor_performance_by_course[course.name][category].append(avg_performance)
                    all_categories.add(category)  # Add the category to the global set of categories

    # Now calculate the average performance for each category within each course
    course_category_averages = {}
    for course_name, categories in professor_performance_by_course.items():
        course_category_averages[course_name] = {}
        for category, performances in categories.items():
            course_category_averages[course_name][category] = sum(performances) / len(performances)

    # Query to get average performance for each professor per category (if needed for the chart)
    performance_data = db.session.query(
        QuestionCategory.name.label('category_name'),
        func.avg(ProfessorPerformance.average_grade).label('average_performance')
    ).join(
        QuestionCategory, QuestionCategory.id == ProfessorPerformance.category_id
    ).group_by(
        QuestionCategory.id
    ).all()

    # If performance_data is not empty, format it
    if performance_data:
        category_names = [row.category_name for row in performance_data]
        average_performances = [row.average_performance for row in performance_data]
    else:
        category_names = []
        average_performances = []

    # Generate acronyms for each category
    category_acronyms = {category: generate_acronym(category) for category in all_categories}

    # Convert all_categories to a list of acronyms
    course_labels = [category_acronyms.get(category, category) for category in all_categories]

    # Prepare the acronym and full name list for the legend
    acronyms_and_full_names = [(full_name, acronym) for full_name, acronym in category_acronyms.items()]

    # Pass all counts, top professors, and performance data to the template
    return render_template(
        'admin/overview.html',
        pending_count=pending_count,
        completed_count=completed_count,
        missing_count=missing_count,
        student_count=student_count,
        professor_count=professor_count,
        top_professor_overall=top_professor_overall,
        course_performance_data=course_category_averages,
        category_names=category_names,
        average_performances=average_performances,
        course_labels=course_labels,  # Ensure course_labels (acronyms) are passed to template
        acronyms_and_full_names=acronyms_and_full_names  # Pass acronym mapping
    )

#------------------------------------------------------------------------------------#
# Manage Course Route

# Shows the list of courses
@admin.route('/manage_courses')
def manage_courses():
    courses = Course.query.options(
        joinedload(Course.sections),
        joinedload(Course.subjects)
    ).all()

    course_data = [
        {
            'id': course.id,
            'name': course.name,
            'sections': [{'id': section.id, 'name': section.name} for section in course.sections],
            'subjects': [{'id': subject.id, 'name': subject.name} for subject in course.subjects],
        }
        for course in courses
    ]

    return render_template('admin/manage_course/manage_courses.html', courses=course_data)

# Add course route
@admin.route('/course/add', methods=['GET', 'POST'])
def add_course():
    if request.method == 'POST':
        course_name = request.form['name']
        section_names = request.form.getlist('section_names[]')
        subject_names = request.form.getlist('subject_names[]')

        # Check if the course already exists
        existing_course = Course.query.filter_by(name=course_name).first()
        if existing_course:
            flash('Course with this name already exists!', 'error')
            return render_template('admin/manage_course/add_course.html')

        # Create and add new course
        new_course = Course(name=course_name)
        db.session.add(new_course)
        db.session.commit()  # Commit to get the course ID

        # Add sections
        for section_name in section_names:
            if section_name:
                new_section = Section(name=section_name, course_id=new_course.id)
                db.session.add(new_section)

        # Add subjects
        for subject_name in subject_names:
            if subject_name:
                new_subject = Subject(name=subject_name, course_id=new_course.id)
                db.session.add(new_subject)

        db.session.commit()

        flash('Course, Sections, and Subjects added successfully!')
        return redirect(url_for('admin.manage_courses'))  # Redirect to course management

    return render_template('admin/manage_course/add_course.html')

# Edit course route
@admin.route('/course/edit/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        # Update course name
        if 'name' in request.form:
            course.name = request.form['name']

        # Add new sections
        section_names = request.form.getlist('section_names[]')
        for section_name in section_names:
            if section_name:  # Ensure name is not empty
                new_section = Section(name=section_name, course=course)
                db.session.add(new_section)

        # Add new subjects
        subject_names = request.form.getlist('subject_names[]')
        for subject_name in subject_names:
            if subject_name:  # Ensure name is not empty
                new_subject = Subject(name=subject_name, course=course)
                db.session.add(new_subject)

        db.session.commit()
        flash('Course updated successfully, along with new sections and subjects!')
        return redirect(url_for('admin.manage_courses'))

    return render_template('admin/manage_course/edit_course.html', course=course)


# Add section route
@admin.route('/course/<int:course_id>/add_section', methods=['POST'])
def add_section(course_id):
    course = Course.query.get_or_404(course_id)
    section_name = request.form['section_name']
    if section_name:
        new_section = Section(name=section_name, course=course)
        db.session.add(new_section)
        db.session.commit()
        flash('Section added successfully!')
    return redirect(url_for('admin.edit_course', course_id=course.id))

# Edit section route
@admin.route('/section/edit/<int:section_id>', methods=['GET', 'POST'])
def edit_section(section_id):
    section = Section.query.get_or_404(section_id)  # Get the section by ID

    if request.method == 'POST':
        section.name = request.form['section_name']  # Update the section name
        db.session.commit()  # Commit the changes to the database
        flash('Section updated successfully!')  # Flash a success message
        return redirect(url_for('admin.edit_course', course_id=section.course_id))  # Redirect to the course edit page

    return render_template('admin/manage_course/edit_section.html', section=section)  # Render the section edit form


# Add subject route
@admin.route('/course/<int:course_id>/add_subject', methods=['POST'])
def add_subject(course_id):
    course = Course.query.get_or_404(course_id)
    subject_name = request.form['subject_name']
    if subject_name:
        new_subject = Subject(name=subject_name, course=course)
        db.session.add(new_subject)
        db.session.commit()
        flash('Subject added successfully!')
    return redirect(url_for('admin.edit_course', course_id=course.id))

# Edit subject route
@admin.route('/admin/subject/edit/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    if request.method == 'POST':
        subject.name = request.form['subject_name']
        db.session.commit()
        flash('Subject updated successfully!')
        return redirect(url_for('admin.edit_course', course_id=subject.course_id))
    return render_template('admin/manage_course/edit_subject.html', subject=subject)


@admin.route('/course/delete/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)

    # Ensure the course has sections and subjects before deletion
    if course.sections or course.subjects:
        flash('This course has sections or subjects associated with it. Remove them first before deleting.', 'danger')
        return redirect(url_for('admin.manage_courses'))

    # Delete the course
    db.session.delete(course)
    db.session.commit()

    flash('Course deleted successfully!')
    return redirect(url_for('admin.manage_courses'))  # Redirect back to course management page

# Delete section route
@admin.route('/section/delete/<int:section_id>', methods=['POST'])
def delete_section(section_id):
    section = Section.query.get_or_404(section_id)
    course_id = section.course_id
    db.session.delete(section)
    db.session.commit()
    flash('Section deleted successfully!')
    return redirect(url_for('admin.edit_course', course_id=course_id))

# Delete subject route
@admin.route('/subject/delete/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    course_id = subject.course_id
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully!')
    return redirect(url_for('admin.edit_course', course_id=course_id))


#------------------------------------------------------------------------------------#

@admin.route('/manage_professors', methods=['GET'])
def load_professors():
    search_query = request.args.get('search', '').strip()  # Get the search query
    professors = Professor.query.all()  # Fetch all professors from the database

    if search_query:
        # Use the linear search algorithm
        professors = linear_search(professors, search_query, 'first_name', 'last_name', 'email')

    # Fetch performance data for each professor (instead of in a separate route)
    performance_data = ProfessorPerformance.query.all()
    categories = QuestionCategory.query.filter(QuestionCategory.name != "Comments / Suggestions").all()

    # Prepare category data for performance calculation
    category_id_to_name = {category.id: category.name for category in categories}
    professor_performance = defaultdict(lambda: defaultdict(lambda: {'categories': {}, 'subject_name': ''}))
    overall_performance = {}

    # Calculate the performance data for each professor
    for professor in professors:
        total_grade = 0
        total_subjects = 0
        professor_category_performance = {}

        for record in performance_data:
            if record.professor_id == professor.id:
                subject_id = record.subject_id
                category_id = record.category_id
                average_grade = record.average_grade
                subject_name = record.subject.name

                professor_performance[professor.id][subject_id]['subject_name'] = subject_name
                professor_performance[professor.id][subject_id]['categories'][category_id] = average_grade

                total_grade += average_grade
                total_subjects += 1

                if category_id not in professor_category_performance:
                    professor_category_performance[category_id] = {'total': 0, 'count': 0}
                professor_category_performance[category_id]['total'] += average_grade
                professor_category_performance[category_id]['count'] += 1

        overall_average = total_grade / total_subjects if total_subjects > 0 else 0
        overall_performance[professor.id] = {'overall_average': overall_average, 'categories': professor_category_performance}

    return render_template(
        'admin/manage_professor/professor.html',
        professors=professors,
        search_query=search_query,
        professor_performance=professor_performance,
        overall_performance=overall_performance,
        categories=categories,
        category_id_to_name=category_id_to_name
    )

@admin.route('/manage_professor/<int:professor_id>', methods=['GET', 'POST'])
def manage_professor(professor_id):
    professor = Professor.query.get_or_404(professor_id)

    # Get the sections and subjects handled by the professor
    handled_sections = ProfessorSectionSubject.query.filter_by(professor_id=professor_id).all()

    # Prepare a dictionary for courses with sections and their associated subjects
    courses_with_sections = {}
    for professor_section in handled_sections:
        section = professor_section.section
        course = section.course
        subject = professor_section.subject  # Access the subject relationship directly

        if course not in courses_with_sections:
            courses_with_sections[course] = {'sections': {}}

        # Add section and its associated subjects
        if section not in courses_with_sections[course]['sections']:
            courses_with_sections[course]['sections'][section] = []

        # Add subject to the list for the section
        if subject and subject not in courses_with_sections[course]['sections'][section]:
            courses_with_sections[course]['sections'][section].append(subject)

    # Fetch all courses, sections, and subjects for dropdowns in the modal
    all_courses = Course.query.all()
    all_sections = Section.query.all()
    all_subjects = Subject.query.all()

    # Handle form submission
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        section_id = request.form.get('section_id')
        subject_ids = request.form.getlist('subject_ids')  # Get multiple subject IDs

        if course_id and section_id and subject_ids:
            for subject_id in subject_ids:
                # Check if the association already exists
                existing_entry = ProfessorSectionSubject.query.filter_by(
                    professor_id=professor_id,
                    section_id=section_id,
                    subject_id=subject_id
                ).first()

                if not existing_entry:
                    # Create a new entry for each selected subject
                    professor_section_subject = ProfessorSectionSubject(
                        professor_id=professor_id,
                        section_id=section_id,
                        subject_id=subject_id
                    )
                    db.session.add(professor_section_subject)

            db.session.commit()

            flash('Section and subjects added successfully!', 'success')
            return redirect(url_for('admin.manage_professor', professor_id=professor_id))

    # Pass data to the template
    return render_template(
        'admin/manage_professor/manage_professor.html',
        professor=professor,
        courses_with_sections=courses_with_sections,
        courses=all_courses,
        sections=all_sections,
        subjects=all_subjects
    )

@admin.route('/professor_performance/<int:professor_id>', methods=['GET'])
def professor_performance(professor_id):
    professor = Professor.query.get_or_404(professor_id)  # Fetch the professor
    performance_data = ProfessorPerformance.query.filter_by(professor_id=professor_id).all()  # Fetch their performance data
    categories = QuestionCategory.query.filter(QuestionCategory.name != "Comments / Suggestions").all()

    # Convert categories to a JSON serializable format
    categories_data = [{'id': category.id, 'name': category.name} for category in categories]

    category_id_to_name = {category.id: category.name for category in categories}
    professor_performance = defaultdict(lambda: {'categories': {}, 'subject_name': '', 'total_average': 0})
    overall_performance = {}

    total_grade = 0
    total_subjects = 0
    professor_category_performance = {}

    # Calculate performance data
    for record in performance_data:
        subject_id = record.subject_id
        category_id = record.category_id
        average_grade = record.average_grade
        subject_name = record.subject.name

        professor_performance[subject_id]['subject_name'] = subject_name
        professor_performance[subject_id]['categories'][category_id] = average_grade

        # Add the average grade to the total for calculating the subject's average later
        if isinstance(professor_performance[subject_id]['total_average'], (int, float)):  # Ensure it's a number
            professor_performance[subject_id]['total_average'] += average_grade
        else:
            professor_performance[subject_id]['total_average'] = average_grade

        total_grade += average_grade
        total_subjects += 1

        if category_id not in professor_category_performance:
            professor_category_performance[category_id] = {'total': 0, 'count': 0}
        professor_category_performance[category_id]['total'] += average_grade
        professor_category_performance[category_id]['count'] += 1

    # Now calculate the total average for each subject
    for subject_id, subject_data in professor_performance.items():
        total_categories = len(subject_data['categories'])
        if total_categories > 0:
            subject_data['total_average'] /= total_categories  # Calculate average

    overall_average = total_grade / total_subjects if total_subjects > 0 else 0
    overall_performance = {'overall_average': overall_average, 'categories': professor_category_performance}

    # Calculate the best and worst categories based on average scores
    best_category = None
    worst_category = None
    best_category_score = float('-inf')
    worst_category_score = float('inf')

    for category_id, performance in professor_category_performance.items():
        average_score = performance['total'] / performance['count'] if performance['count'] > 0 else 0
        if average_score > best_category_score:
            best_category_score = average_score
            best_category = {'id': category_id, 'name': category_id_to_name[category_id], 'score': best_category_score}
        if average_score < worst_category_score:
            worst_category_score = average_score
            worst_category = {'id': category_id, 'name': category_id_to_name[category_id], 'score': worst_category_score}

    # Add best and worst categories to overall_performance
    overall_performance['best_category'] = best_category
    overall_performance['worst_category'] = worst_category

    return render_template('admin/manage_professor/professors_performance.html',
        professor=professor,
        professor_performance=professor_performance,
        overall_performance=overall_performance,
        categories_data=categories_data,  # Pass the serialized categories
        category_id_to_name=category_id_to_name
    )

@admin.route('/professor/<int:professor_id>/edit', methods=['GET', 'POST'])
def edit_professor(professor_id):
    professor = Professor.query.get_or_404(professor_id)  # Fetch the professor by ID

    if request.method == 'POST':
        professor.first_name = request.form['first_name']  # Update professor's first name
        professor.last_name = request.form['last_name']  # Update professor's last name
        professor.email = request.form['email']  # Update professor's email
        db.session.commit()  # Commit changes to the database
        flash('Professor updated successfully!', 'success')  # Show success message
        return redirect(url_for('admin.load_professors'))  # Redirect to the professor's details page

    return render_template('admin/manage_professor/edit_professor.html', professor=professor)

@admin.route('/professor/<int:professor_id>/delete', methods=['POST'])
def delete_professor(professor_id):
    professor = Professor.query.get_or_404(professor_id)  # Fetch the professor by ID
    try:
        db.session.delete(professor)  # Delete the professor from the session
        db.session.commit()  # Commit the change
        flash('Professor deleted successfully!', 'success')  # Show success message
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        flash('An error occurred while deleting the professor.', 'danger')  # Show error message
    return redirect(url_for('admin.load_professors'))  # Redirect to manage professors page

@admin.route('/section/<int:section_id>/edit', methods=['GET', 'POST'])
def edit_professor_section(section_id):
    # Get the section to edit
    section = Section.query.get_or_404(section_id)

    # Get the list of subjects assigned to this section
    existing_subjects = [professor_section_subject.subject_id for professor_section_subject in section.professors_subjects]

    if request.method == 'POST':
        # Don't change the Section's name or course, just update section_id and subjects
        new_section_id = request.form['section_id']  # The form should send the new section_id
        selected_subject_ids = request.form.getlist('subject_ids')

        # Ensure professor_id is set (it should be associated with the section)
        professor_section_subject = section.professors_subjects[0] if section.professors_subjects else None
        if not professor_section_subject:
            flash('This section has no associated professor.', 'danger')
            return redirect(url_for('admin.view_professor', professor_id=None))  # or handle accordingly

        professor_id = professor_section_subject.professor_id  # Retrieve the professor_id from the relationship

        # Remove existing subjects
        for professor_section_subject in section.professors_subjects:
            db.session.delete(professor_section_subject)

        # Add new subjects
        for subject_id in selected_subject_ids:
            professor_section_subject = ProfessorSectionSubject(
                professor_id=professor_id,  # Use the professor_id from the relationship
                section_id=new_section_id,  # Use the new section_id from the form
                subject_id=subject_id
            )
            db.session.add(professor_section_subject)

        db.session.commit()
        flash('Section updated successfully!', 'success')
        return redirect(url_for('admin.manage_professor', professor_id=professor_id))

    # Fetch all courses for the dropdown
    all_courses = Course.query.all()

    # The section's course is fixed (read-only)
    selected_course = section.course

    # Fetch sections filtered by course_id (fetch sections belonging to the selected course)
    sections = Section.query.filter_by(course_id=selected_course.id).all()

    # Fetch subjects for the selected section
    all_subjects = Subject.query.filter_by(course_id=selected_course.id).all()

    return render_template(
        'admin/manage_professor/edit_professor_section.html',
        section=section,
        course=selected_course,  # Passing the course to be displayed
        subjects=all_subjects,
        existing_subjects=existing_subjects,
        sections=sections  # Pass filtered sections to the template
    )

@admin.route('/section/add/<int:course_id>', methods=['GET', 'POST'])
def add_professor_section(course_id):
    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        name = request.form['name']
        new_section = Section(name=name, course_id=course_id)
        db.session.add(new_section)
        db.session.commit()
        flash('Section added successfully!', 'success')
        return redirect(url_for('admin.view_professor', professor_id=request.form['professor_id']))

    return render_template('admin/manage_professor/add_section.html', course=course)

@admin.route('/section/<int:section_id>/delete', methods=['POST'])
def delete_professor_section(section_id):
    section = Section.query.get_or_404(section_id)

    # Find the professor linked to this section through ProfessorSectionSubject
    professor_section_subjects = ProfessorSectionSubject.query.filter_by(section_id=section_id).all()
    professor_id = professor_section_subjects[0].professor_id if professor_section_subjects else None

    try:
        # Delete all related ProfessorSectionSubject entries
        for entry in professor_section_subjects:
            db.session.delete(entry)

        # Delete the section
        db.session.delete(section)
        db.session.commit()
        flash('Section deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the section: {str(e)}', 'danger')

    # Redirect to the manage_professor page
    return redirect(url_for('admin.manage_professor', professor_id=professor_id))

@admin.route('/professor/<int:professor_id>/add_subject_to_section/<int:section_id>', methods=['GET', 'POST'])
def add_subject_to_section(professor_id, section_id):
    professor = Professor.query.get_or_404(professor_id)
    section = Section.query.get_or_404(section_id)

    if request.method == 'POST':
        subject_id = request.form['subject_id']
        subject = Subject.query.get_or_404(subject_id)

        # Create a new ProfessorSectionSubject entry
        professor_section_subject = ProfessorSectionSubject(professor_id=professor.id,
                                                            section_id=section.id,
                                                            subject_id=subject.id)
        db.session.add(professor_section_subject)
        db.session.commit()
        flash('Subject added to section successfully!', 'success')
        return redirect(url_for('admin.view_professor', professor_id=professor.id))

    subjects = Subject.query.filter_by(course_id=section.course_id).all()
    return render_template('admin/manage_professor/add_subject_to_section.html', professor=professor,
                           section=section, subjects=subjects)


#------------------------------------------------------------------------------------#
# Manage Evaluation Forms Route

# Show the list of the Existing Evaluation Form
@admin.route('/manage_forms')
def manage_forms():
    # Query the database for all evaluation forms
    forms = EvaluationForm.query.order_by(EvaluationForm.created_on.desc()).all()

    # Pass the forms to the template
    return render_template('admin/manage_form/manage_forms.html', forms=forms)

# Create Evaluation Form Route
@admin.route('/create_form', methods=['GET', 'POST'])
def create_form():
    categories = QuestionCategory.query.all()  # Fetch all categories from the database

    if request.method == 'POST':
        form_title = request.form.get('form_title')
        form_description = request.form.get('form_description')

        # Validate the form data
        if not form_title or not form_description:
            flash("Please fill out all fields.", "error")
            return redirect(request.url)

        # Save the evaluation form to the database
        new_form = EvaluationForm(title=form_title, description=form_description)
        db.session.add(new_form)
        db.session.commit()  # Commit to get the form ID

        # Process questions by category
        for category in categories:
            # Use category-specific name pattern to get the questions for this category
            question_field_name = f"category_questions_{category.id}[]"
            questions = request.form.getlist(question_field_name)

            # Skip categories with no questions
            if not questions:
                continue

            # Save each question for the category
            for question_text in questions:
                if question_text.strip():  # Ensure non-empty questions are saved
                    new_question = Question(
                        form_id=new_form.id,
                        category_id=category.id,
                        question_text=question_text.strip()
                    )
                    db.session.add(new_question)

        # Automatically add a single-entry question for "Comments / Suggestions"
        comments_category = QuestionCategory.query.filter_by(name="Comments / Suggestions").first()
        if comments_category:
            new_question = Question(
                form_id=new_form.id,
                category_id=comments_category.id,
                question_text="Comments / Suggestions"
            )
            db.session.add(new_question)

        db.session.commit()
        flash("Evaluation form created successfully!", "success")
        return redirect(url_for('admin.manage_forms'))

    return render_template('admin/manage_form/create_form.html', categories=categories)

# View Evaluation Form Route
@admin.route('/view_form/<int:form_id>')
def view_form(form_id):
    # Fetch the form by ID along with its questions
    form = EvaluationForm.query.get_or_404(form_id)

    # Group questions by category
    questions_by_category = {}
    categories = QuestionCategory.query.all()  # Fetch all categories

    for category in categories:
        # Get all questions that belong to the current category
        questions_by_category[category] = [
            question for question in form.questions if question.category_id == category.id
        ]

    return render_template('admin/manage_form/view_form.html', form=form, questions_by_category=questions_by_category)

# Edit Evaluation Form Route
@admin.route('/edit_form/<int:form_id>', methods=['GET', 'POST'])
def edit_form(form_id):
    form = EvaluationForm.query.get_or_404(form_id)
    categories = QuestionCategory.query.filter(QuestionCategory.name != "Comments / Suggestions").all()  # Exclude Comments/Suggestions

    if request.method == 'POST':
        # Update form details
        form.title = request.form.get('form_title')
        form.description = request.form.get('form_description')

        # Process existing questions
        for question_id, question_text in request.form.items():
            if question_id.startswith("questions"):
                question_id = int(question_id.split("[")[1].split("]")[0])  # Extract question ID
                question = Question.query.get(question_id)
                if question:
                    question.question_text = question_text.strip()

        # Handle deletions (questions marked for removal)
        removed_question_ids = request.form.getlist('removed_questions[]')
        for question_id in removed_question_ids:
            question = Question.query.get(question_id)
            if question:
                db.session.delete(question)

        # Handle new questions by category
        for category in categories:
            category_question_field = f"new_questions_{category.id}[]"
            new_questions = request.form.getlist(category_question_field)
            for new_question_text in new_questions:
                if new_question_text.strip():  # Ensure non-empty input
                    new_question = Question(
                        form_id=form.id,
                        category_id=category.id,
                        question_text=new_question_text.strip()
                    )
                    db.session.add(new_question)

        db.session.commit()
        flash("Form updated successfully!", "success")
        return redirect(url_for('admin.manage_forms'))

    # Organize questions by category for the frontend
    questions_by_category = {
        category: Question.query.filter_by(form_id=form.id, category_id=category.id).all()
        for category in categories
    }

    return render_template(
        'admin/manage_form/edit_form.html',
        form=form,
        questions_by_category=questions_by_category,
    )

# Delete Evaluation Form Route
@admin.route('/delete_form/<int:form_id>', methods=['POST'])
def delete_form(form_id):
    form = EvaluationForm.query.get_or_404(form_id)

    try:
        db.session.delete(form)  # Delete the form
        db.session.commit()  # Commit the changes to the database
        flash("Form deleted successfully!", "success")
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")

    return redirect(url_for('admin.manage_forms'))

@admin.route('/distribute_forms', methods=['GET', 'POST'])
def distribute_forms():
    if request.method == 'POST':
        # Handle form submission
        form_ids = [form.id for form in EvaluationForm.query.all()]
        course_id = request.form.get('course_id')
        professor_ids = request.form.getlist('professor_ids')
        subject_ids = request.form.getlist('subject_ids')
        section_ids = request.form.getlist('section_ids')
        deadline = request.form.get('deadline')  # Get deadline from the form

        # Validate input fields
        if not form_ids or not course_id or not professor_ids or not section_ids or not deadline:
            flash("Please fill out all fields, including the deadline.", "error")
            return redirect(url_for('admin.distribute_forms'))

        try:
            # Parse the deadline input
            deadline_dt = datetime.strptime(deadline, '%Y-%m-%d')
        except ValueError:
            flash("Invalid deadline format. Please use YYYY-MM-DD.", "error")
            return redirect(url_for('admin.distribute_forms'))

        # Fetch course and associated records
        course = Course.query.get(course_id)
        professors = Professor.query.filter(Professor.id.in_(professor_ids)).all()
        subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
        sections = Section.query.filter(Section.id.in_(section_ids)).all()

        # Process form distribution for each selected form
        for form_id in form_ids:
            for professor in professors:
                for subject in subjects:
                    for section in sections:
                        # Create a form distribution entry
                        new_distribution = FormDistribution(
                            form_id=form_id,
                            course_id=course.id,
                            section_id=section.id,
                            professor_id=professor.id,
                            subject_id=subject.id,
                            deadline=deadline_dt
                        )
                        db.session.add(new_distribution)
                        db.session.flush()  # Ensure new_distribution.id is generated

                        # Fetch all students in the section
                        students = Student.query.filter(Student.section_id == section.id).all()

                        # Create individual StudentFormStatus records
                        for student in students:
                            student_status = StudentFormStatus(
                                form_distribution_id=new_distribution.id,
                                student_id=student.id,
                                status='pending'  # Set initial status to 'pending'
                            )
                            db.session.add(student_status)

        db.session.commit()
        flash("Forms distributed successfully!", "success")
        return redirect(url_for('admin.manage_forms'))

    # GET request - render the form distribution page
    forms = EvaluationForm.query.all()
    courses = Course.query.all()
    return render_template(
        'admin/manage_form/distribute_form.html',
        forms=forms,
        courses=courses
    )

@admin.route('/get_course_details/<int:course_id>')
def get_course_details(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    # Get professors, subjects, and sections related to the course
    professors = Professor.query.join(ProfessorSectionSubject).join(Section).join(Course).filter(Course.id == course_id).all()
    subjects = Subject.query.filter(Subject.course_id == course_id).all()
    sections = Section.query.filter(Section.course_id == course_id).all()

    # Prepare data for frontend
    professor_data = [{'id': prof.id, 'first_name': prof.first_name, 'last_name': prof.last_name} for prof in professors]
    subject_data = [{'id': subj.id, 'name': subj.name} for subj in subjects]
    section_data = [{'id': sec.id, 'name': sec.name} for sec in sections]

    return jsonify({
        'professors': professor_data,
        'subjects': subject_data,
        'sections': section_data
    })

@admin.route('/complete_distribution', methods=['POST'])
def complete_distribution():
    # Get selected form, course, professor, student, and other related IDs
    form_ids = request.form.getlist('form_ids')
    course_id = request.form.get('course_id')
    professor_ids = request.form.getlist('professor_ids')
    subject_ids = request.form.getlist('subject_ids')
    section_ids = request.form.getlist('section_ids')
    student_ids = request.form.getlist('student_ids')  # For student-based distribution

    if not form_ids or (not professor_ids and not student_ids):  # Check for either professors or students
        flash("All fields are required to distribute forms.", "error")
        return redirect(url_for('admin.manage_forms'))

    # Handle form distribution based on the selected distribution type
    if professor_ids:
        # Distribute forms to professors
        for form_id in form_ids:
            for professor_id in professor_ids:
                for subject_id in subject_ids:
                    professor_sections = db.session.query(ProfessorSectionSubject).filter(
                        ProfessorSectionSubject.professor_id == professor_id,
                        ProfessorSectionSubject.subject_id == subject_id
                    ).all()

                    for pss in professor_sections:
                        if str(pss.section.id) in section_ids:
                            section = pss.section
                            new_distribution = FormDistribution(
                                form_id=form_id,
                                course_id=course_id,
                                section_id=section.id,
                                professor_id=professor_id,
                                subject_id=subject_id
                            )
                            db.session.add(new_distribution)

                            # Create StudentFormStatus records for each student in the section
                            students = Student.query.filter(Student.section_id == section.id).all()
                            for student in students:
                                student_status = StudentFormStatus(
                                    form_distribution_id=new_distribution.id,
                                    student_id=student.id,
                                    status='pending'  # Set initial status to 'pending'
                                )
                                db.session.add(student_status)

    elif student_ids:
        # Distribute forms to students
        for form_id in form_ids:
            for student_id in student_ids:
                new_distribution = FormDistribution(
                    form_id=form_id,
                    student_id=student_id
                )
                db.session.add(new_distribution)

                # Create StudentFormStatus record for the student
                student_status = StudentFormStatus(
                    form_distribution_id=new_distribution.id,
                    student_id=student_id,
                    status='pending'  # Set initial status to 'pending'
                )
                db.session.add(student_status)

    db.session.commit()
    flash("Forms distributed successfully!", "success")
    return redirect(url_for('admin.manage_forms'))


#------------------------------------------------------------------------------------#

@admin.route('/manage_students', methods=['GET', 'POST'])
def manage_students():
    # Fetch all courses for the dropdown
    courses = Course.query.all()
    selected_course_id = request.args.get('course_id', type=int)
    selected_section_id = request.args.get('section_id', type=int)

    # Fetch sections based on the selected course
    sections = Section.query.filter_by(course_id=selected_course_id).all() if selected_course_id else []

    return render_template(
        'admin/manage_student/manage_student.html',
        courses=courses,
        sections=sections,
        selected_course_id=selected_course_id,
        selected_section_id=selected_section_id,
    )

@admin.route('/get_students/<int:course_id>/<int:section_id>', methods=['GET'])
def get_students(course_id, section_id):
    try:
        print(f"Fetching students for course_id: {course_id}, section_id: {section_id}")

        # Fetch students based on section_id
        students = Student.query.filter_by(section_id=section_id).all()

        if not students:
            raise ValueError(f"No students found for section {section_id}")

        # Prepare student data to return as JSON (no evaluation form data)
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
            })

        return jsonify(students_data)

    except Exception as e:
        print(f"Error fetching students: {e}")
        return jsonify({'error': 'Failed to fetch students'}), 500

# View Student
@admin.route('/view_student/<int:student_id>', methods=['GET'])
def view_student(student_id):
    # Fetch the student
    student = Student.query.get_or_404(student_id)

    # Ensure the student belongs to a section
    if not student.section_id:
        flash("This student is not assigned to a section.", "error")
        return redirect(url_for('admin.manage_students'))

    # Query form statuses for the student
    form_statuses = StudentFormStatus.query.filter_by(student_id=student_id).all()

    # Calculate the counts of statuses
    completed_count = sum(1 for status in form_statuses if status.status == 'completed')
    pending_count = sum(1 for status in form_statuses if status.status == 'pending')
    missing_count = sum(1 for status in form_statuses if status.status == 'missing')

    # Pass data to the template
    return render_template(
        'admin/manage_student/view.html',
        student=student,
        completed_count=completed_count,
        pending_count=pending_count,
        missing_count=missing_count,
    )

# Edit Student
@admin.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == 'POST':
        student.first_name = request.form['first_name']
        student.last_name = request.form['last_name']
        student.email = request.form['email']
        student.age = request.form['age'] or None  # Ensure empty field is handled
        student.section_id = request.form['section_id']  # Section change
        db.session.commit()
        return redirect(url_for('admin.view_student', student_id=student.id))

    # For GET requests, pass the sections available for selection
    sections = Section.query.all()
    return render_template('admin/manage_student/edit.html', student=student, sections=sections)

# Delete Student
@admin.route('/delete_student/<int:student_id>', methods=['GET'])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('admin.manage_students'))


#------------------------------------------------------------------------------------#

# Manage Categories Route
@admin.route('/categories', methods=['GET'])
def manage_categories():
    # Fetch all categories
    categories = QuestionCategory.query.order_by(QuestionCategory.created_on.desc()).all()
    return render_template('admin/manage_category/manage_categories.html', categories=categories)

# Add Category Route
@admin.route('/categories/add', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        category_names = request.form.getlist('category_name[]')  # Get all category names

        if not category_names or not all(category_names):
            flash("All category names are required.", "error")
            return redirect(request.url)

        # Check for duplicates in the form and database
        for name in category_names:
            if QuestionCategory.query.filter_by(name=name).first():
                flash(f"Category '{name}' already exists.", "error")
                return redirect(request.url)

        # Add the new categories
        new_categories = [QuestionCategory(name=name) for name in category_names]
        db.session.add_all(new_categories)
        db.session.commit()

        flash("Categories added successfully!", "success")
        return redirect(url_for('admin.manage_categories'))

    return render_template('admin/manage_category/add_category.html')

# Edit Category Route
@admin.route('/categories/edit', methods=['GET', 'POST'])
def edit_category():
    categories = QuestionCategory.query.order_by(QuestionCategory.created_on.desc()).all()

    if request.method == 'POST':
        # Handle bulk updates
        for category_id, category_name in zip(request.form.getlist('category_id[]'), request.form.getlist('category_name[]')):
            if not category_name.strip():
                flash("Category name cannot be empty.", "error")
                return redirect(request.url)

            category = QuestionCategory.query.get(category_id)
            if category:
                # Prevent duplicates
                if QuestionCategory.query.filter(QuestionCategory.id != category.id, QuestionCategory.name == category_name.strip()).first():
                    flash(f"Category '{category_name}' already exists.", "error")
                    return redirect(request.url)

                # Update category name
                category.name = category_name.strip()

        # Add new categories if any
        for new_category_name in request.form.getlist('new_category_name[]'):
            if new_category_name.strip():
                if QuestionCategory.query.filter_by(name=new_category_name.strip()).first():
                    flash(f"Category '{new_category_name}' already exists.", "error")
                    return redirect(request.url)

                # Add new category
                new_category = QuestionCategory(name=new_category_name.strip())
                db.session.add(new_category)

        db.session.commit()
        flash("Categories updated successfully!", "success")
        return redirect(url_for('admin.manage_categories'))

    return render_template('admin/manage_category/edit_category.html', categories=categories)

# Delete Category Route
@admin.route('/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    category = QuestionCategory.query.get_or_404(category_id)

    try:
        db.session.delete(category)  # Delete manage_category and associated questions due to cascade
        db.session.commit()
        flash("Category deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "error")

    return redirect(url_for('admin.manage_categories'))


# Endpoint to fetch sections dynamically (used for AJAX)
@admin.route('/get_sections/<int:course_id>', methods=['GET'])
def get_sections(course_id):
    sections = Section.query.filter_by(course_id=course_id).all()
    sections_data = [{'id': section.id, 'name': section.name} for section in sections]
    return jsonify(sections_data)

# Endpoint to fetch subjects dynamically (used for AJAX)
@admin.route('/get_subjects/<int:course_id>', methods=['GET'])
def get_subjects(course_id):
    subjects = Subject.query.filter_by(course_id=course_id).all()
    subjects_data = [{'id': subject.id, 'name': subject.name} for subject in subjects]
    return jsonify(subjects_data)




