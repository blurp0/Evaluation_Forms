from flask_login import UserMixin
from website import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta


# Professor Model
class Professor(UserMixin, db.Model):
    __tablename__ = 'professors'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    overall_performance = db.Column(db.Float, nullable=True)  # Overall performance of professor

    professor_section_subjects = db.relationship('ProfessorSectionSubject', back_populates='professor',
                                                 cascade="all, delete-orphan")

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password)

    def __repr__(self):
        return f"<Professor {self.first_name} {self.last_name}>"



class Student(UserMixin,db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=True)  # Allow null

    # Store hashed password
    password = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        """Set the password by hashing it"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hashed password"""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<Student {self.student_id}: {self.first_name} {self.last_name}>"

#-------------------------------------------------------------------------------------------------------------#
# EvaluationForm and Question Models
class EvaluationForm(db.Model):
    __tablename__ = 'evaluation_forms'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    updated_on = db.Column(db.DateTime, onupdate=datetime.utcnow)  # Tracks when the form is updated
    questions = db.relationship('Question', backref='form', cascade="all, delete")

    def __repr__(self):
        return f"<EvaluationForm {self.title}>"

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    form_id = db.Column(db.Integer, db.ForeignKey('evaluation_forms.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('question_categories.id'), nullable=False)  # Category link
    question_text = db.Column(db.String(255), nullable=False)  # Ensure the correct type here
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    updated_on = db.Column(db.DateTime, onupdate=datetime.utcnow)  # Tracks when the question is updated

    def __repr__(self):
        return f"<Question {self.question_text[:30]} (Category: {self.category_id})>"


class QuestionCategory(db.Model):
    __tablename__ = 'question_categories'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Category name
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    updated_on = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    questions = db.relationship('Question', backref='manage_category', cascade="all, delete", lazy=True)

    def __repr__(self):
        return f"<QuestionCategory {self.name}>"


class FormDistribution(db.Model):
    __tablename__ = 'form_distributions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    form_id = db.Column(db.Integer, db.ForeignKey('evaluation_forms.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    distributed_on = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)  # Added deadline column
    # Removed the `status` column

    # Adding the relationship to StudentFormStatus
    student_form_status = db.relationship('StudentFormStatus', cascade="all, delete-orphan")

    # Relationships
    form = db.relationship('EvaluationForm', backref='distributions', cascade="save-update")
    course = db.relationship('Course', backref='form_distributions')
    section = db.relationship('Section', backref='form_distributions')
    professor = db.relationship('Professor', backref='form_distributions')
    subject = db.relationship('Subject', backref='form_distributions')

    def __repr__(self):
        return (
            f"<FormDistribution form_id={self.form_id} "
            f"professor={self.professor.first_name} {self.professor.last_name} "
            f"subject={self.subject.name} section={self.section.name}>"
        )

    def is_deadline_missed(self):
        """
        Check if the form's deadline has been missed.
        """
        return self.deadline and datetime.utcnow() > self.deadline

    def update_status(self):
        """
        Dynamically updates the FormDistribution status based on associated StudentFormStatus records.
        """
        # Check if deadline is missed, then set 'missing' status for all students
        if self.is_deadline_missed():
            # Update the status of all student form statuses to 'missing' for students who haven't completed
            for student_status in self.student_form_status:
                if student_status.status != 'completed':
                    student_status.status = 'missing'
            db.session.commit()

        # Dynamically calculate the number of pending, completed, and missing statuses
        pending_count = sum(1 for status in self.student_form_status if status.status == 'pending')
        completed_count = sum(1 for status in self.student_form_status if status.status == 'completed')
        missing_count = sum(1 for status in self.student_form_status if status.status == 'missing')

        # If all students have completed, set form to 'completed' status
        if pending_count == 0 and missing_count == 0:
            return 'completed'
        elif pending_count > 0:
            return 'pending'
        elif missing_count > 0:
            return 'missing'

        return 'pending'  # Default case


class StudentFormStatus(db.Model):
    __tablename__ = 'student_form_status'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    form_distribution_id = db.Column(db.Integer, db.ForeignKey('form_distributions.id'), nullable=False)
    status = db.Column(
        db.Enum('pending', 'completed', 'missing', name='student_form_statuses'),
        default='pending',
        nullable=False
    )  # Tracks each student's status
    completed_on = db.Column(db.DateTime, nullable=True)  # Timestamp for when the student completed the form

    # Relationships
    student = db.relationship('Student', backref='form_statuses')
    form_distribution = db.relationship('FormDistribution', backref='student_statuses')  # Changed backref to 'student_statuses'

    def __repr__(self):
        return (
            f"<StudentFormStatus student_id={self.student_id} "
            f"form_distribution_id={self.form_distribution_id} status={self.status}>"
        )


class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('evaluation_forms.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    form_distribution_id = db.Column(db.Integer, db.ForeignKey('form_distributions.id'), nullable=False)  # Track form distribution
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)  # Add subject_id
    answer_value = db.Column(db.Float, nullable=True)  # Change to Float for decimal values
    comment = db.Column(db.Text, nullable=True)  # Optional text for comments or suggestions
    category_id = db.Column(db.Integer, db.ForeignKey('question_categories.id'), nullable=True)  # Foreign key to QuestionCategory

    # Relationships
    form = db.relationship('EvaluationForm', backref='answers')
    student = db.relationship('Student', backref='answers')
    form_distribution = db.relationship('FormDistribution', backref='answers')
    subject = db.relationship('Subject', backref='answers')  # Add relationship with Subject
    category = db.relationship('QuestionCategory', backref='answers')  # Relationship to QuestionCategory

    def __repr__(self):
        return f"<Answer form_id={self.form_id} student_id={self.student_id} category_id={self.category_id}>"

class CategoryRawAnswer(db.Model):
    __tablename__ = 'category_raw_answers'

    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'), nullable=False)  # Link to the Answer model
    category_id = db.Column(db.Integer, db.ForeignKey('question_categories.id'), nullable=False)  # Foreign key to QuestionCategory
    raw_answer_value = db.Column(db.Integer, nullable=True)  # Raw answer (1-5 or other scale)
    comment = db.Column(db.Text, nullable=True)  # Store comments separately for this category

    # Relationship to the Answer model
    answer = db.relationship('Answer', backref='category_raw_answers')
    category = db.relationship('QuestionCategory', backref='category_raw_answers')  # Relationship to QuestionCategory

    def __repr__(self):
        return f"<CategoryRawAnswer answer_id={self.answer_id}, category={self.category.name}, raw_answer_value={self.raw_answer_value}, comment={self.comment}>"


class SavedComment(db.Model):
    __tablename__ = 'saved_comments'

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('answers.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.id'), nullable=False)  # New column
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    answer = db.relationship('Answer', backref='saved_comment')
    professor = db.relationship('Professor', backref='saved_comments')  # Relationship with Professor

    def __repr__(self):
        return f"<SavedComment comment_id={self.comment_id}, professor_id={self.professor_id}>"

#-------------------------------------------------------------------------------------------------------------#
class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    sections = db.relationship('Section', backref='course', lazy=True, cascade="all, delete-orphan")
    subjects = db.relationship('Subject', backref='course', lazy=True, cascade="all, delete-orphan")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Course {self.name}>"

class Section(db.Model):
    __tablename__ = 'sections'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "1-A"
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    students = db.relationship('Student', backref='section', lazy=True, cascade="all, delete-orphan")
    professors_subjects = db.relationship('ProfessorSectionSubject', cascade='all, delete-orphan',
                                          back_populates='section')

    __table_args__ = (
        db.UniqueConstraint('name', 'course_id', name='unique_section_name_per_course'),
    )

    def __repr__(self):
        return f"<Section {self.name} (Course: {self.course.name})>"


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    professor_section_subjects = db.relationship('ProfessorSectionSubject', back_populates='subject')

    __table_args__ = (
        db.UniqueConstraint('name', 'course_id', name='unique_subject_name_per_course'),
    )

    def __repr__(self):
        return f"<Subject {self.name}>"

class ProfessorSectionSubject(db.Model):
    __tablename__ = 'professor_section_subjects'
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)

    professor = db.relationship('Professor', back_populates='professor_section_subjects')
    section = db.relationship('Section', back_populates='professors_subjects')
    subject = db.relationship('Subject', back_populates='professor_section_subjects')

    def __repr__(self):
        return f"<ProfessorSectionSubject Prof:{self.professor.first_name} {self.professor.last_name}, Section:{self.section.name}, Subject:{self.subject.name}>"

class ProfessorPerformance(db.Model):
    __tablename__ = 'professor_performance'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('question_categories.id'), nullable=False)  # Foreign key to QuestionCategory
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)  # Associate with subject
    average_grade = db.Column(db.Float, nullable=False)  # Average grade per category
    total_ratings_count = db.Column(db.Integer, default=0)  # New field to track total number of ratings
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    professor = db.relationship('Professor', backref='performances')
    subject = db.relationship('Subject', backref='performances')
    category = db.relationship('QuestionCategory', backref='professor_performances')  # Relationship to QuestionCategory

    def __repr__(self):
        return f"<ProfessorPerformance Prof:{self.professor.first_name} {self.professor.last_name}, Category:{self.category.name}, Subject:{self.subject.name}, Avg:{self.average_grade}>"

#-------------------------------------------------------------------------------------------------------------#


"""

flask --app website db migrate
flask --app website db upgrade

"""