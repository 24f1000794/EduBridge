from .database import db
from datetime import datetime
from flask_login import UserMixin
#from werkzeug.security import generate_password_hash


# # Association Table: User ↔ Mentor
user_mentor_association = db.Table(
    'user_mentor_association',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('mentor_id', db.Integer, db.ForeignKey('mentor.id'))
)

# # Association Table: Mentor ↔ Course
mentor_course_association = db.Table(
    'mentor_course_association',
    db.Column('mentor_id', db.Integer, db.ForeignKey('mentor.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'))
)

# Association table for Progress-Badge many-to-many relationship
progress_badges = db.Table('progress_badges',
    db.Column('progress_id', db.Integer, db.ForeignKey('progress.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('badges.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    fullname = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    qualification = db.Column(db.String(200), nullable = False)
    language_pref = db.Column(db.String(200), nullable = False)
    interest = db.Column(db.String(200), nullable = False)
    date_of_birth = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='student')

    # #Relationship
    quiz_attempts = db.relationship('QuizAttempt', backref='quiz_user', lazy='dynamic')
    answers = db.relationship('Answer', backref='answer_user', lazy='dynamic')
    quizzes_created = db.relationship('Quiz', backref='creator', lazy='dynamic', foreign_keys='Quiz.created_by_user_id')
    mentors = db.relationship('Mentor', secondary=user_mentor_association, back_populates='students')
    messages_sent = db.relationship('Messages', backref='sender', lazy='dynamic', foreign_keys='Messages.sender_id')
    messages_received = db.relationship('MentorMessages', backref='receiver', lazy='dynamic', foreign_keys='MentorMessages.receiver_id')
    progress = db.relationship('Progress', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')
    def __repr__(self):
        return f"<User {self.username}>"
    # # Relationships
    # progress_entries = db.relationship('Progress', back_populates='user', lazy='dynamic')  # Renamed
    # messages_sent = db.relationship('Message', backref='sender', lazy='dynamic', foreign_keys='Message.sender_id')
    # notes = db.relationship('Note', backref='uploader', lazy='dynamic')
    # quizzes_created_as_admin = db.relationship('Quiz', foreign_keys='Quiz.created_by_user_id', backref='admin_creator', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.username}>"
    
    # def get_id(self):
    #     return f"user:{self.id}"
    # def role(self):
    #     return self.role  # or 'student', depending on your logic

    
    
    # def __init__(self, username, fullname, email, password, qualification, dob):
    #     self.username = username
    #     self.fullname = fullname
    #     self.email = email
    #     #self.password = generate_password_hash(password)
    #     self.qualification = qualification
    #     self.dob = dob
    #     self.is_active = True  

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable = False)
    language = db.Column(db.String(10), default='en')
    level = db.Column(db.String(50), nullable=False)
    # Relationships
    modules = db.relationship('Module', backref='course_modules', lazy='subquery', cascade="all, delete-orphan")
    quizzes = db.relationship('Quiz', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    # progress = db.relationship('Progress', back_populates='course', lazy='dynamic')
    progress = db.relationship('Progress', back_populates='course', lazy='dynamic')
    notes = db.relationship('Note', backref='course', lazy='dynamic',cascade='all, delete-orphan')
    quiz_attempts = db.relationship("QuizAttempt", backref="quiz_course", lazy="dynamic")
    mentors = db.relationship('Mentor', secondary=mentor_course_association, back_populates='courses')


class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    video_path = db.Column(db.String(200))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    #course = db.relationship('Course', back_populates='modules')
    submodules = db.relationship('SubModule', backref='module', cascade='all, delete-orphan')

class SubModule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    video_path = db.Column(db.String(200))
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    #module = db.relationship('Module', backref='submodules')  # Ensure relationship with module

class Progress(db.Model):
    __tablename__ = 'progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=True)  # Null for assignments
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # Score out of 100
    completion_percentage = db.Column(db.Float, default=0.0)  # % of course completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # # Relationships
    user = db.relationship('User', backref='progress')
    # quiz = db.relationship('Quiz', backref='progress')
    # course = db.relationship('Course', backref='progress_records', lazy='dynamic')
    badges = db.relationship('Badge', secondary='progress_badges', backref='progress')
    # quiz_attempt = db.relationship('QuizAttempt', backref='progress_entry', uselist=False)  # Updated backref name

   # Relationships
    user = db.relationship('User', back_populates='progress', lazy='joined')
    course = db.relationship('Course', back_populates='progress', lazy='joined')
    badges = db.relationship('Badge', secondary='progress_badges', backref='progress')
    quiz_attempts = db.relationship('QuizAttempt', backref='progress_record', lazy='dynamic')

    def __repr__(self):
        return f'<Progress user_id={self.user_id} course_id={self.course_id} completion={self.completion_percentage}>'

class Badge(db.Model):
    __tablename__ = 'badges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Quiz Master"
    description = db.Column(db.String(200), nullable=False)  # e.g., "Scored 80%+ in a quiz"
    icon_url = db.Column(db.String(200), nullable=True)  # URL to badge icon
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Badge name={self.name}>'

class Mentor(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    expertise = db.Column(db.String(200))
    availability = db.Column(db.String(80), default=True)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(80),nullable=False)
    language_pref = db.Column(db.String(80),nullable=False)
    role = db.Column(db.String(80), default='mentor')
    #role=db.Column(db.String(50), default='mentor')
    # Relationships
    courses = db.relationship('Course', secondary=mentor_course_association, back_populates='mentors')
    messages_received = db.relationship('Messages', backref='receiver', lazy='dynamic', foreign_keys='Messages.receiver_id')
    messages_sent = db.relationship('MentorMessages', backref='sender', lazy='dynamic', foreign_keys='MentorMessages.sender_id')
    quizzes_created_as_mentor = db.relationship('Quiz', foreign_keys='Quiz.created_by_mentor_id', lazy='dynamic')
    notes_uploaded = db.relationship('Note', backref='mentor_uploader', lazy='dynamic')
    students = db.relationship('User', secondary=user_mentor_association, back_populates='mentors')
    # @property
    # def role(self):
    #     return self.role
    def get_id(self):
        # Ensure get_id returns a string, not a set
        return str(self.id)

class Messages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    def __repr__(self):
        return f'<Message from user_id={self.sender_id} to mentor_id={self.receiver_id}>'

class MentorMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MentorMessage from mentor_id={self.sender_id} to user_id={self.receiver_id}>'
    
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    uploaded_by_mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=True)
    uploaded_by_admin = db.Column(db.Boolean, default=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)




class Quiz(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(80), nullable = False)
    time_limit = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.Integer, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_by_mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable = True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    #user_creator = db.relationship('User', foreign_keys=[created_by_user_id])
    #mentor_creator = db.relationship('Mentor', foreign_keys=[created_by_mentor_id])

    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', back_populates='quiz', lazy='dynamic', cascade='all, delete-orphan')
    #attempts = db.relationship('QuizAttempt', back_populates='quiz')
    answers = db.relationship('Answer', backref='quiz', lazy='dynamic')
    created_by_mentor = db.relationship('Mentor', foreign_keys=[created_by_mentor_id], backref=db.backref('mentor_quizzes', lazy='dynamic', overlaps="quizzes_created_as_mentor"), overlaps="quizzes_created_as_mentor")
    

    __table_args__ = (
    db.CheckConstraint(
        '(created_by_user_id IS NOT NULL AND created_by_mentor_id IS NULL) OR '
        '(created_by_user_id IS NULL AND created_by_mentor_id IS NOT NULL)',
        name='check_single_creator'
    ),
)


    def __repr__(self):
        return f'<Quiz {self.title}>'

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    #correct_answer = db.Column(db.String(100), nullable=False)

    # options = db.relationship('Option', backref='question', lazy='dynamic', cascade='all, delete-orphan')
    options = db.relationship('Option', backref='question', lazy='dynamic', cascade='all, delete-orphan')
    answers = db.relationship('Answer', backref='question', lazy='dynamic')
    def __repr__(self):
        return f'<Question {self.text[:50]}>'

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_answers = db.relationship('Answer', backref='selected_option', lazy='dynamic')



class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)  # e.g., Maths, Science
    score = db.Column(db.Integer, default=0)  
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_taken = db.Column(db.Integer, nullable=True)  # Time taken in seconds
    completed = db.Column(db.Boolean, default=False)
    progress_id = db.Column(db.Integer, db.ForeignKey('progress.id'), nullable=True)  

    # Relationships
    # user = db.relationship('User', backref='quiz_attempts')
    # quiz = db.relationship('Quiz', backref='attempts', lazy='dynamic')
    # course = db.relationship('Course', backref='course_attempts', lazy='dynamic')  # Changed backref
    # progress = db.relationship('Progress', backref='quiz_attempt', uselist=False)
    # answers = db.relationship('Answer', backref='attempt', lazy='dynamic', cascade='all, delete-orphan')
    # Relationships
    user = db.relationship('User', back_populates='quiz_attempts', overlaps="quiz_user")
    # quiz = db.relationship('Quiz', backref='quiz_attempts')
    quiz = db.relationship('Quiz', back_populates='attempts')
    course = db.relationship('Course', back_populates='quiz_attempts', overlaps="quiz_course")
    progress = db.relationship('Progress', back_populates='quiz_attempts', uselist=False, overlaps="progress_record")
    answers = db.relationship('Answer', backref='attempt', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<QuizAttempt user_id={self.user_id} quiz_id={self.quiz_id} score={self.score}>'

class Answer(db.Model):
    __tablename__ = 'answer'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempt.id'), nullable=False)  # Added foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

   
