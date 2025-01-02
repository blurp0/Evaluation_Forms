from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from website.model import Professor, Subject, Section, Student, db, ProfessorSectionSubject, Course, FormDistribution, \
    Answer, SavedComment, ProfessorPerformance, QuestionCategory, StudentFormStatus

professor = Blueprint('professor', __name__, url_prefix='/professor')

# Home Page
@professor.route('/')
@login_required
def homepage():
    professor = current_user

    overall_performance = professor.overall_performance

    # Find all sections associated with this professor
    sections = Section.query.join(ProfessorSectionSubject).filter(
        ProfessorSectionSubject.professor_id == professor.id
    ).all()

    # Count unique sections
    num_sections = len(sections)

    # Count unique subjects taught by the professor
    num_subjects = len(set(
        ProfessorSectionSubject.query.filter_by(professor_id=professor.id).with_entities(
            ProfessorSectionSubject.subject_id
        ).distinct()
    ))

    # Count total students in sections taught by this professor
    num_students = len(set(
        Student.query.join(Section).filter(
            Section.id.in_([section.id for section in sections])
        ).all()
    ))

    # Get all professor performance data
    performances = ProfessorPerformance.query.filter_by(professor_id=professor.id).all()

    # Find the highest and lowest performing categories
    if performances:
        highest_performance = max(performances, key=lambda p: p.average_grade)
        lowest_performance = min(performances, key=lambda p: p.average_grade)
    else:
        highest_performance = lowest_performance = None

    # Prepare data for template
    data = {
        'overall_performance': overall_performance,
        'num_sections': num_sections,
        'num_subjects': num_subjects,
        'num_students': num_students,
        'highest_performance': highest_performance,
        'lowest_performance': lowest_performance
    }

    return render_template('professor/homepage.html', professor=professor, data=data)

# Manage Subjects
@professor.route('/subjects', methods=['GET'])
@login_required
def manage_subjects():
    # Fetch all subjects assigned to the professor, grouped by course
    courses = (
        db.session.query(Course)
        .join(Section)
        .join(ProfessorSectionSubject)
        .filter(ProfessorSectionSubject.professor_id == current_user.id)
        .options(db.joinedload(Course.sections).joinedload(Section.professors_subjects).joinedload(ProfessorSectionSubject.subject))
        .distinct()
        .all()
    )

    # Group subjects by course, then aggregate sections per subject
    grouped_data = []
    for course in courses:
        subjects_dict = {}
        for section in course.sections:
            for pss in section.professors_subjects:
                if pss.professor_id == current_user.id:
                    subject_name = pss.subject.name
                    if subject_name not in subjects_dict:
                        subjects_dict[subject_name] = []
                    subjects_dict[subject_name].append(section.name)
        grouped_data.append({
            'course_name': course.name,
            'subjects': [{'name': name, 'sections': ', '.join(sorted(set(sections)))} for name, sections in subjects_dict.items()]
        })

    return render_template('professor/manage_subjects.html', grouped_data=grouped_data)


@professor.route('/students', methods=['GET'])
@login_required
def manage_students():
    # Fetch section IDs associated with the professor from ProfessorSectionSubject
    sections = (
        Section.query.join(ProfessorSectionSubject)
        .filter(ProfessorSectionSubject.professor_id == current_user.id)
        .options(db.joinedload(Section.students))  # Preload students for efficiency
        .all()
    )

    # Fetch form distribution IDs related to the professor
    form_distributions = (
        FormDistribution.query.filter_by(professor_id=current_user.id)
        .all()
    )
    form_distribution_ids = [dist.id for dist in form_distributions]

    # Fetch student form statuses for these form distributions
    student_form_statuses = (
        StudentFormStatus.query.filter(
            StudentFormStatus.form_distribution_id.in_(form_distribution_ids)
        ).all()
    )

    # Create a mapping of section -> student -> status count
    section_student_status = {}
    for section in sections:
        section_student_status[section.id] = {}

        # Initialize counts for each status
        for student in section.students:
            section_student_status[section.id][student.id] = {'pending': 0, 'completed': 0, 'missing': 0}

        # Loop through student form statuses and update counts
        for status in student_form_statuses:
            # Check if this student belongs to the current section
            student = next(
                (s for s in section.students if s.id == status.student_id), None
            )
            if student:
                section_student_status[section.id][student.id][status.status] += 1

    return render_template(
        'professor/manage_students.html',
        sections=sections,
        section_student_status=section_student_status
    )



@professor.route('/comments', methods=['GET'])
@login_required
def comments():
    professor_id = current_user.id  # Assuming professors log in as `current_user`

    # Fetch comments linked to the professor via FormDistribution
    comments = Answer.query.join(FormDistribution).filter(
        FormDistribution.professor_id == professor_id,  # Match professor ID
        Answer.comment.isnot(None)  # Only non-null comments
    ).order_by(Answer.id.desc()).all()

    return render_template('professor/comments.html', comments=comments)


@professor.route('/save_comments', methods=['POST'])
@login_required
def save_comments():
    comment_ids = request.form.getlist('comment_ids')  # List of selected comment IDs

    for comment_id in comment_ids:
        # Get the comment and associated professor
        answer = Answer.query.get(comment_id)
        if answer:
            professor_id = answer.form_distribution.professor_id

            # Check if the comment is already saved for this professor
            if not SavedComment.query.filter_by(comment_id=comment_id, professor_id=professor_id).first():
                saved_comment = SavedComment(comment_id=comment_id, professor_id=professor_id)
                db.session.add(saved_comment)

    db.session.commit()
    flash('Selected comments have been saved.')
    return redirect(url_for('professor.comments'))


@professor.route('/saved_comments', methods=['GET'])
@login_required
def saved_comments():
    professor_id = current_user.id  # Assuming the professor is logged in
    saved_comments = SavedComment.query.filter_by(professor_id=professor_id).all()
    return render_template('professor/saved_comments.html', saved_comments=saved_comments)


@professor.route('/performance', methods=['GET'])
@login_required
def view_performance():
    """
    Displays the performance of the logged-in professor grouped by course, section, and subject.
    """
    professor_id = current_user.id  # Assuming the professor is logged in

    # Get all courses, sections, and subjects assigned to the professor
    assignments = (
        db.session.query(
            Course.name.label('course_name'),
            Section.name.label('section_name'),
            Subject.name.label('subject_name'),
            ProfessorSectionSubject.subject_id,
            ProfessorSectionSubject.section_id,
            ProfessorSectionSubject.professor_id
        )
        .join(Section, ProfessorSectionSubject.section_id == Section.id)
        .join(Course, Section.course_id == Course.id)
        .join(Subject, ProfessorSectionSubject.subject_id == Subject.id)
        .filter(ProfessorSectionSubject.professor_id == professor_id)
        .all()
    )

    # Create a dictionary of subject IDs and their corresponding names
    subject_names = {assignment.subject_id: assignment.subject_name for assignment in assignments}

    # Fetch performance data with category names
    performances = (
        db.session.query(
            ProfessorPerformance.subject_id,
            QuestionCategory.name.label('category_name'),
            ProfessorPerformance.average_grade
        )
        .join(QuestionCategory, ProfessorPerformance.category_id == QuestionCategory.id)
        .filter(ProfessorPerformance.professor_id == professor_id)
        .all()
    )

    # Organize performance data by subject ID
    performance_data = {}
    total_grades = 0
    total_subjects = 0
    subject_average_grades = {}  # Store total average for each subject
    category_performance = {}  # Store category performance for graphing

    for performance in performances:
        if performance.subject_id not in performance_data:
            performance_data[performance.subject_id] = []

        performance_data[performance.subject_id].append({
            'category_name': performance.category_name,
            'average_grade': performance.average_grade
        })

        # Add to category performance for the graph
        if performance.category_name not in category_performance:
            category_performance[performance.category_name] = []
        category_performance[performance.category_name].append(performance.average_grade)

        # Calculate total grades for all subjects for the overall average calculation
        total_grades += performance.average_grade
        total_subjects += 1

        # Add category grades and calculate the total average grade for each subject
        if performance.subject_id not in subject_average_grades:
            subject_average_grades[performance.subject_id] = {'total_grades': 0, 'category_count': 0}

        subject_average_grades[performance.subject_id]['total_grades'] += performance.average_grade
        subject_average_grades[performance.subject_id]['category_count'] += 1

    # Calculate total average grade for all subjects
    total_average_grade = total_grades / total_subjects if total_subjects > 0 else None  # Set to None if no subjects

    # Calculate the average grade for each subject
    subject_performance = {}
    for subject_id, grades_data in subject_average_grades.items():
        subject_average = grades_data['total_grades'] / grades_data['category_count'] if grades_data['category_count'] > 0 else None
        subject_performance[subject_id] = subject_average

    # Calculate category performance data (average for each category across all subjects)
    category_labels = list(category_performance.keys())
    category_data = []
    for grades in category_performance.values():
        if len(grades) > 0:
            category_data.append(sum(grades) / len(grades))
        else:
            category_data.append(None)  # or 0, depending on your preference

    # Calculate overall category average
    total_category_grades = sum(category_data) if category_data else 0
    total_categories = len(category_data)
    overall_category_average = total_category_grades / total_categories if total_categories > 0 else None

    # Prepare the data for display in the template
    data = {}
    for assignment in assignments:
        course_name = assignment.course_name
        section_name = assignment.section_name
        subject_name = assignment.subject_name
        subject_id = assignment.subject_id

        if course_name not in data:
            data[course_name] = {}

        if section_name not in data[course_name]:
            data[course_name][section_name] = []

        data[course_name][section_name].append({
            'subject_name': subject_name,
            'subject_id': subject_id,
            'performance': performance_data.get(subject_id, []),
            'overall_performance': subject_performance.get(subject_id, 0)  # Add the subject's overall performance
        })

    # Pass the data and the performance data for categories and subjects to the template
    return render_template(
        'professor/performance.html',
        data=data,
        total_average_grade=total_average_grade,
        overall_category_average=overall_category_average,  # Pass overall category average
        category_performance=category_performance,
        subject_performance=subject_performance,
        category_labels=category_labels,
        category_data=category_data,
        subject_labels=list(subject_names.values()),  # Send subject names as labels
        subject_data=list(subject_performance.values()),  # Send the subject performance data
        subject_names=subject_names  # Pass the subject names dictionary to the frontend
    )


def update_professor_performance():
    """
    Updates the `ProfessorPerformance` table with average grades for each category
    for a professor's subjects.
    """
    performances = (
        db.session.query(
            Answer.form_distribution_id,
            Answer.category_id,  # Use category_id directly
            db.func.avg(Answer.answer_value).label('average_grade'),
            FormDistribution.professor_id,
            FormDistribution.subject_id
        )
        .join(FormDistribution, Answer.form_distribution_id == FormDistribution.id)
        .group_by(
            Answer.category_id,  # Group by category_id
            FormDistribution.professor_id,
            FormDistribution.subject_id
        )
        .all()
    )

    for record in performances:
        performance = ProfessorPerformance.query.filter_by(
            professor_id=record.professor_id,
            subject_id=record.subject_id,
            category_id=record.category_id
        ).first()

        if not performance:
            performance = ProfessorPerformance(
                professor_id=record.professor_id,
                subject_id=record.subject_id,
                category_id=record.category_id,
                average_grade=record.average_grade
            )
            db.session.add(performance)
        else:
            performance.average_grade = record.average_grade

    db.session.commit()
