from datetime import datetime
import os
import random
import traceback
import requests
#from sqlalchemy.orm import Session
from flask_socketio import SocketIO,emit,join_room
from flask_mail import Mail,Message 
from flask import Flask, jsonify
from flask import render_template, redirect, request, url_for,session,flash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from functools import wraps
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
from config import Config
from models import db, User
from forms.userform import RegistrationForm, LoginForm,forgetPasswordForm,requestResetPasswordForm,mentorRegistration,MessageForm
from werkzeug.utils import secure_filename
from models.user import Messages, User, Course,Mentor,Progress,Module,Quiz,Question,Option,QuizAttempt,Answer,Badge,SubModule,Note,Messages,MentorMessages




load_dotenv() #load environmental variable

app = Flask(__name__)
app.config.from_object(Config) # load database configuration
db.init_app(app) #initialize the DB
csrf = CSRFProtect(app) # enable CSRF protection
bcrypt = Bcrypt(app)
mail = Mail(app)
socketio = SocketIO(app)
# mail.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect here if user not logged in
GROQ_API_KEY = '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'

UPLOAD_FOLDER = 'static/uploads/' 

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# @login_manager.user_loader
# def load_user(user_id):
#     user_type, user_id = user_id.split(":")
#     if user_type == "mentor":
#         return Mentor.query.get(int(user_id))
#     else:
#         return User.query.get(int(user_id))

@login_manager.user_loader
def load_user(user_id):
    # try:
    #     user_type, user_id = user_id.split(":")
    # except ValueError:
    #     # If there's an error in the format, you can log it or handle it accordingly
    #     return None  # Or some default handling, like returning a 404 or redirecting to a login page.

    user_type = session.get('user_type')  # Get user type from session

    if user_type == 'mentor':
        # Load mentor by ID
        return db.session.get(Mentor, (user_id))
    elif user_type == 'student':
        # Load user by ID
        return db.session.get(User, int(user_id))
    return None

    # try: 
    #     user_type, uid = user_id.split(":")
    #     uid = int(uid)
    #     if user_type == "user":
    #         return User.query.get(uid)
    #     elif user_type == "mentor":
    #         return Mentor.query.get(uid)
    # except Exception as e:
    #     print("Error loading user:", e)
    #     return None
    #return User.query.get(int(user_id)) or Mentor.query.get(int(user_id))

# Helper function to calculate quiz score
def calculate_quiz_score(attempt):
    quiz = Quiz.query.get(attempt.quiz_id)
    total_questions = len(quiz.questions)
    if total_questions == 0:
        return 0
    correct_answers = sum(1 for answer in attempt.answers if answer.selected_option.is_correct)
    score_percentage = (correct_answers / total_questions) * 100
    return score_percentage

# Helper function to award badges
def award_badges(progress):
    badges = []
    if progress.score >= 80:
        badge = Badge.query.filter_by(name='Quiz Master').first()
        if badge and badge not in progress.badges:
            progress.badges.append(badge)
            badges.append(badge.name)
    db.session.commit()
    return badges

#Helper function is for RBAC
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role not in allowed_roles:
                flash('Access denied: insufficient permissions.', 'error')
                return redirect(url_for('quiz_list'))  # Or a 403 page
            return f(*args, **kwargs)
        return decorated_function
    return decorator


#set up the admin
def create_admin():
    from models.user import User
    admin_exists = User.query.filter_by(role='admin').first()
    if not admin_exists:
        hashed_password = bcrypt.generate_password_hash('123456789').decode('utf-8')
        admin = User(
            username='admin',
            fullname='admin',
            email='bathampranshu67@gmail.com',
            password=hashed_password,
            qualification='N/A',
            language_pref='N/A',
            interest='N/A',
            date_of_birth='N/A',
            role='admin',
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created successfully!")
    else:
        print("ℹ️ Admin user already exists.")


@app.route('/')
def LandingPage():
    return render_template('LandingPage.html')

@app.route('/user/register', methods=['GET', 'POST'])
def register():
    # form = RegistrationForm(request.form)
    form = RegistrationForm(request.form)
    if request.method == 'GET':
        return render_template("registration.html", form=form)
    
    if request.method == 'POST' and form.validate_on_submit():
        username = form.username.data
        fullname = form.fullname.data
        email = form.email.data
        password = form.password.data
        qualification = form.qualification.data
        language_pref=form.language_pref.data
        interest = ','.join(form.interest.data)
        date_of_birth = form.date_of_birth.data

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Check if username already exists
        exist_user = User.query.filter_by(username=username).first()
        if exist_user:
            flash("Username already exists. Try another one", "danger")
            print('Username already exists. Try another one", "danger')
            return redirect(url_for('register'))  

        # Check for missing fields
        if not username or not password or not fullname or not email:
            flash("Please fill all required fields.", "warning")
            print("Please fill all required fields.", "warning")
            return redirect(url_for('register')) 
        # Create new user
        new_user = User(
            username=username, 
            fullname=fullname, 
            email=email, 
            password=hashed_password,
            qualification=qualification, 
            language_pref=language_pref,
            interest=interest,
            date_of_birth=date_of_birth,
        )
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login')) 
    # Handle validation errors
    flash("Form validation failed. Please check the details.", "danger")
    print("Failed")
    return render_template("registration.html", form=form) 

@app.route('/mentor/register', methods=['GET', 'POST']) # left
def mentor_register():
    form = mentorRegistration(request.form)
    if request.method == 'POST'and form.validate_on_submit():
        username = form.username.data
        fullname = form.mentor_name.data
        email = form.email.data
        password = form.password.data
        expertise = form.expertise.data
        availability = form.availiable.data[0]
        language_pref = form.language_pref.data

        #check exsitence
        exist_user = Mentor.query.filter_by(username=username).first()
        if exist_user:
            flash("Username already exists. Try another one", "danger")
            return render_template('mentor_register.html')
        # hashpassword
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        #check for missing fields
        if not username or not password or not fullname or not email or not expertise or not availability:
            flash("Please fill all required fields.", "warning")
            return render_template('mentor_register.html', form=form)
        # Create new user
        new_mentor = Mentor(username=username,fullname=fullname,email=email,password=hashed_password,expertise=expertise,availability=availability,language_pref=language_pref)
        db.session.add(new_mentor)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('mentor_register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'GET':
        return render_template("login.html", form=form)

    if request.method == 'POST' and form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Check in User table
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            # session['username'] = user.username
            # session['role'] = 'student'
            login_user(user)
            session['user_type'] = 'student'
            if user.role == 'student':
                return redirect(url_for('dashboard', id=user.id))
            elif user.role == 'admin':
                return redirect(url_for('AdminDashboard'))

        # If not found or not valid in User, check Mentor
        mentor = Mentor.query.filter_by(username=username).first()
        # print(mentor)
        # print(current_user.role)
        # print(mentor.password)
        if mentor and bcrypt.check_password_hash(mentor.password, password):
            #   session['username'] = mentor.username
            #   session['role'] = 'mentor'
            login_user(mentor)
            session['user_type'] = 'mentor'
            session['role'] = 'mentor'
            # print("Logged in?", current_user.is_authenticated)
            # print("Current user:", current_user)
            # print("Session:", dict(session))
            print("Redirecting to mentor_dashboard with ID:", mentor.id)
            return redirect(url_for('mentor_dashboard' , id = mentor.id))

        # If neither matched
        flash("Invalid username or password.", "danger")
        return redirect(url_for('login'))

    flash("Login form validation failed. Please try again.", "danger")
    return render_template("login.html", form=form)


#Dashboards
@app.route('/user/<int:id>/dashboard', methods=['GET', 'POST']) # check
@login_required
def dashboard(id):
    user = User.query.get_or_404(id)
    if request.method == 'GET':
        course = Course.query.filter(Course.name.ilike(f"%{user.interest}%")).all()
        if course:
            print("Course exist", course)
        else:
            print("course is not exist")
        return render_template('dashboard.html', user=user, courses=course)
    else:
        flash("You must log in first.", "warning")
        return redirect(url_for('login'))


@app.route('/mentor/<int:id>/dashboard') # check
@login_required
def mentor_dashboard(id):
    mentor = Mentor.query.get_or_404(id)
    messages = Messages.query.filter_by(receiver_id=current_user.id).order_by(Messages.timestamp.asc()).all()
    #if 'username' in session and session.get('role') == 'mentor':
    print(current_user.role)
    if current_user.role == 'mentor':
        return render_template('mentor_dashborad.html', mentor_name = mentor.fullname, messages=messages)
    else:
        flash("You must log in first.", "warning")
        return redirect(url_for('login'))

@app.route('/AdminDashboard', methods=['GET'])
@login_required 
def AdminDashboard():
    return render_template("AdminDashboard.html")


#add mentor
@csrf.exempt
@app.route('/mentor/create', methods = ['GET','POST'])
def create_mentor():
    if request.method == 'GET':
        return render_template('AddMentors.html')
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        expertise = request.form.get('expert')
        email = request.form.get('email')
        password = request.form.get('password')
        availability = request.form.get('availability')
        language_pref = request.form.get('language_pref')


        #check existence
        mentor = Mentor.query.filter_by(email = email).first()
        if mentor:
            flash("Mentor already exists", "danger")
            return redirect(url_for('create_mentor'))
        # hashpassword
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_mentor = Mentor(username=username,fullname=name,expertise=expertise,availability=availability,email=email, password=hashed_password,language_pref=language_pref)
        db.session.add(new_mentor)
        db.session.commit()
        return redirect(url_for('view_mentor'))

#update mentor
@csrf.exempt
@app.route('/mentor/<int:id>/update', methods=['GET', 'POST'])
def update_mentor(id):
    mentor = Mentor.query.get_or_404(id)
    if request.method == 'GET':
        return render_template('updateMentor.html', mentor=mentor)
    if request.method == 'POST':
        #check existence
        if mentor: 
            mentor.name = request.form.get('name')
            mentor.expertise = request.form.get('expertise')  # fix name mismatch too
            mentor.availability = request.form.get('availability')
            mentor.email = request.form.get('email')
            db.session.commit()
            return redirect(url_for('view_mentor'))
        flash('Mentor is not exist with the give id', 'danger')
        return redirect(url_for('update_mentor', id=id))

#delete mentor
@csrf.exempt
@app.route('/delete_mentor/<int:id>/delete', methods=['GET', 'POST'])
def delete_mentor(id):
    mentor = Mentor.query.get(id)
    if mentor is None:
        return jsonify({"error": "Mentor not found"}), 404

    try:
        # 1. Find fallback admin user
        fallback_admin = User.query.filter_by(role='admin').first()
        if fallback_admin is None:
            return jsonify({"error": "No admin user available to transfer ownership"}), 500

        # 2. Transfer ownership of quizzes created by mentor
        mentor_quizzes = Quiz.query.filter_by(created_by_mentor_id=mentor.id).all()
        for quiz in mentor_quizzes:
            quiz.created_by_user_id = fallback_admin.id
            quiz.created_by_mentor_id = None
            db.session.add(quiz)

        # 3. Delete all related messages
        received_messages = Messages.query.filter_by(receiver_id=mentor.id).all()
        for message in received_messages:
            db.session.delete(message)

        sent_messages = MentorMessages.query.filter_by(sender_id=mentor.id).all()
        for message in sent_messages:
            db.session.delete(message)

        # 4. Now delete mentor
        db.session.delete(mentor)
        db.session.commit()

        flash('Mentor deleted successfully. Their quizzes have been transferred to admin.', 'success')
        return redirect(url_for('view_mentor'))

    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({"error": str(e)}), 500

#view mentor
@app.route('/mentor/view', methods=['GET', 'POST']) # left 
def view_mentor():
    mentors = Mentor.query.all()
    user = User.query.filter_by(email = current_user.email).first()
    return render_template('viewMentor.html', mentors = mentors , user=user)

#add user
@csrf.exempt
@app.route('/user/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        qualification = request.form.get('qualification')
        language_pref = request.form.get('language_pref')
        interest = request.form.get('interest')
        date_of_birth = request.form.get('date_of_birth')
        password = request.form.get('password')

        #check existence
        user = User.query.filter_by(email=email).first()
        if user != None:
            flash("User is already exist",'info')
            return redirect(url_for('add_user'))
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            username = username,
            fullname=fullname,
            email=email,
            password=hashed_password,
            qualification = qualification,
            language_pref=language_pref,
            interest=interest,
            date_of_birth=date_of_birth,
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('view_users'))
    return render_template('create_user.html')

#update user
@csrf.exempt
@app.route('/user/<int:id>/update', methods=['GET','POST'])
def update_user(id):
    if request.method == 'POST':
        user = User.query.filter_by(id=id).first()
        if user:
            user.username = request.form.get('username')
            user.fullname = request.form.get('fullname')
            user.email = request.form.get('email')
            user.qualification = request.form.get('qualification')
            user.language_pref = request.form.get('language_pref')
            user.interest = request.form.get('interest')
            user.date_of_birth = request.form.get('date_of_birth')
            db.session.commit()
            flash("User is updated successfully")
            if current_user.role in ['mentor','admin']:
                return redirect(url_for('view_users'))
            else:
                return redirect(url_for('dashboard', id = current_user.id))
        flash("User is not exist with this id")
        return redirect(url_for('view_users'))
    user = User.query.filter_by(id=id).first()
    return render_template('update_user.html', user=user)

#delete user
@app.route('/delete/<int:id>/user', methods=['GET'])
@login_required
@role_required(['admin','mentor'])
def delete_user(id):
    user = User.query.get_or_404(id)
    badge = Badge.query.filter_by(id=id).first()
    quiz_attempt = QuizAttempt.query.filter_by(id=id).first()
    message = Messages.query.filter_by(id=id).first()

    if badge:
        db.session.delete(badge)
    if quiz_attempt:
        db.session.delete(quiz_attempt)
    if message:
        db.session.delete(message)

    db.session.delete(user)
    db.session.commit()

    flash('User deleted successfully.', 'success')
    return redirect(url_for('view_users'))

#view user
@app.route('/user/view', methods=['GET', 'POST'])
def view_users():
    users = User.query.filter(User.role != 'admin').all()
    return render_template('view_users.html', users=users)

# List All Quizzes
@csrf.exempt
@login_required
@app.route('/quizzes')
def quiz_list():
    course_id = request.args.get('course_id', type=int)
    courses = Course.query.all()
    if course_id:
        quizzes = Quiz.query.filter_by(course_id=course_id).all()
    else:
        quizzes = Quiz.query.all()
    user = User.query.filter_by(email = current_user.email).first()
    mentor = Mentor.query.filter_by(email=current_user.email).first()
    return render_template('quiz_list.html', quizzes=quizzes, courses=courses,user=user,mentor=mentor)

# Create Quiz
@csrf.exempt
@login_required
@app.route('/quiz/create', methods=['GET', 'POST'])
def create_quiz():
    if session.get('role') not in ['mentor', 'admin']:
        flash('Only mentors or admins can create quizzes.', 'error')
        return redirect(url_for('login'))  # Or quiz list, as appropriate
    
    if request.method == 'POST':
        title = request.form.get('title')
        course_id = request.form.get('course_id',type=int)
        description = request.form.get('description')
        time_limit = request.form.get('time_limit', type=int)
        language = request.form.get('language', 'en')
        
        if not title or not course_id:
            flash('Title and course are required.', 'error')
            return redirect(url_for('quiz.create_quiz'))
        
        # Translate title if not in English
        if language != 'en':
            try:
                response = request.post(
                    'https://libretranslate.com/translate',
                    json={'q': title, 'source': 'en', 'target': language}
                )
                title = response.json()['translatedText']
            except:
                flash('Translation failed, using original title.', 'warning')
        
        quiz = Quiz(
            title=title,
            description=description,
            time_limit=time_limit,
            course_id=course_id,
            created_by=current_user.id,  # Uses User.id
            created_at=datetime.utcnow(),
            language=language
        )

        if current_user.role=="admin":
            quiz.created_by_user_id=current_user.id
        else:
            quiz.created_by_mentor_id = current_user.id
        db.session.add(quiz)
        db.session.commit()
        
        #Handle questions and options
        questions_data = []
        i = 0
        while f'questions[{i}][text]' in request.form:
            text = request.form.get(f'questions[{i}][text]')
            options = request.form.getlist(f'questions[{i}][options][]')
            correct_idx = request.form.get(f'questions[{i}][correct]', type=int)

            if not text or len(options) < 2 or correct_idx is None or not (0 <= correct_idx < len(options)):
                flash('Invalid question or option data.', 'error')
                db.session.rollback()
                return redirect(url_for('quiz.create_quiz'))
            
            # Translate question and options
            if language != 'en':
                try:
                    text_response = request.post(
                        'https://libretranslate.com/translate',
                        json={'q': text, 'source': 'en', 'target': language}
                    )
                    text = text_response.json()['translatedText']
                    translated_options = []
                    for opt in options:
                        opt_response = request.post(
                            'https://libretranslate.com/translate',
                            json={'q': opt, 'source': 'en', 'target': language}
                        )
                        translated_options.append(opt_response.json()['translatedText'])
                    options = translated_options
                except:
                    flash('Translation failed for question, using original text.', 'warning')
           
            questions_data.append({
                'text': text,
                'options': options,
                'correct': correct_idx
            })
            i += 1
        
        if not questions_data:
            flash('At least one question is required.', 'error')
            db.session.rollback()
            return redirect(url_for('quiz.create_quiz'))
        
        for q_data in questions_data:
            question = Question(text=q_data['text'], quiz_id=quiz.id)
            db.session.add(question)
            db.session.commit()
            for idx, option_text in enumerate(q_data['options']):
                is_correct = idx == int(q_data['correct'])
                option = Option(text=option_text, is_correct=is_correct, question_id=question.id)
                db.session.add(option)
            db.session.commit()
        
        flash('Quiz created successfully!', 'success')
        return redirect(url_for('quiz.quiz_list'))
    
    courses = Course.query.all()
    return render_template('create_quiz.html', courses=courses)

# update Quiz
@csrf.exempt
@app.route('/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    if current_user.role not in ['admin', 'mentor']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    # Ensure only the creator or admin can edit
    if current_user.role == 'mentor' and quiz.created_by_mentor_id != current_user.id:
        flash('You can only edit quizzes you created.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.form
        
        # Validate required fields
        errors = []
        if not data.get('title'):
            errors.append('Quiz title is required.')
        if not data.get('description'):
            errors.append('Quiz description is required.')
        if not data.get('time_limit') or not data.get('time_limit').isdigit():
            errors.append('Valid time limit (in minutes) is required.')
        
        # Validate questions and options
        question_texts = data.getlist('question_text[]')
        option_texts = [data.getlist(f'options[{i}][]') for i in range(len(question_texts))]
        correct_options = data.getlist('correct_option[]')
        
        # Ensure correct_options length matches question_texts
        if len(correct_options) != len(question_texts):
            errors.append('Each question must have a selected correct option.')
        
        for i, q_text in enumerate(question_texts):
            if not q_text.strip():
                errors.append(f'Question {i+1} text is required.')
            if len(option_texts[i]) < 2:
                errors.append(f'Question {i+1} must have at least 2 options.')
            for j, opt in enumerate(option_texts[i]):
                if not opt.strip():
                    errors.append(f'Option {j+1} for Question {i+1} is required.')
            if i < len(correct_options):
                if not correct_options[i].strip() or not correct_options[i].isdigit() or int(correct_options[i]) >= len(option_texts[i]):
                    errors.append(f'Valid correct option for Question {i+1} is required.')
            else:
                errors.append(f'Correct option for Question {i+1} is missing.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('edit_quiz.html', quiz=quiz, courses=Course.query.all())
        
        # Update quiz details
        quiz.title = data['title']
        quiz.description = data['description']
        quiz.time_limit = int(data['time_limit'])
        quiz.language = data.get('language', quiz.language)
        quiz.course_id = int(data['course_id'])
        
        # Delete existing questions and options
        Question.query.filter_by(quiz_id=quiz.id).delete()
        
        # Add updated questions and options
        for i, q_text in enumerate(question_texts):
            question = Question(text=q_text, quiz_id=quiz.id)
            db.session.add(question)
            db.session.flush()  # Get question.id
            
            for j, opt_text in enumerate(option_texts[i]):
                is_correct = (j == int(correct_options[i]))
                option = Option(text=opt_text, is_correct=is_correct, question_id=question.id)
                db.session.add(option)
        
        db.session.commit()
        flash('Quiz updated successfully!', 'success')
        return redirect(url_for('list_quizzes'))
    
    # GET: Render edit form with pre-filled data
    courses = Course.query.all()
    return render_template('edit_quiz.html', quiz=quiz, courses=courses)

# view all quizzes
@app.route('/quizzes')
@login_required
def list_quizzes():
    quizzes = Quiz.query.all()
    return render_template('quiz_list.html', quizzes=quizzes)

# Delete Quiz
@csrf.exempt
@login_required
@role_required(['mentor', 'admin'])
@app.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
def delete_quiz(quiz_id):
    # if current_user.role not in ['mentor', 'admin']:
    #     flash('Only mentors or admins can delete quizzes.', 'error')
    #     return redirect(url_for('quiz_list'))
    
    quiz = Quiz.query.get_or_404(quiz_id)

    # if current_user.role in ['mentor', 'admin']:
    #     flash('You can only delete your own quizzes.', 'error')
    #     return redirect(url_for('quiz_list'))
    
    # Optional: Add confirmation check
    if request.form.get('confirm') != 'yes':
        flash('Please confirm deletion.', 'error')
        return redirect(url_for('quiz.quiz_detail', quiz_id=quiz_id))
    
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted successfully!', 'success')
    return redirect(url_for('quiz_list'))

# View Quiz Details
@csrf.exempt
@login_required
@app.route('/quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz_detail.html', quiz=quiz)

# Attempt Quiz
@csrf.exempt
@login_required
@app.route('/quiz/<int:quiz_id>/attempt', methods=['GET', 'POST'])
def attempt_quiz(quiz_id):
    if current_user.role not in ['student']:
        flash('Only students can attempt quizzes.', 'error')
        return redirect(url_for('quiz.quiz_list'))
    quiz = Quiz.query.get_or_404(quiz_id)

    if request.method == 'POST':
        #check time limit
        if quiz.time_limit:
            attempt_start = datetime.utcnow()
            if 'start_time' in request.form:
                start_time = datetime.fromisoformat(request.form['start_time'])
                if (datetime.utcnow() - start_time).seconds / 60 > quiz.time_limit:
                    flash('Time limit exceeded.', 'error')
                    return redirect(url_for('quiz.quiz_detail', quiz_id=quiz_id))
                
        attempt = QuizAttempt(
            user_id=current_user.id,
            quiz_id=quiz.id,
            course_id = quiz.course_id,
            attempted_at=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.commit()
        
        #checking total socres
        score = 0
        total_questions = quiz.questions.count()
        answers = request.form
        for question in quiz.questions:
            answer_key = f'answers[{question.id}]'
            if answer_key not in answers:
                flash('Please answer all questions.', 'error')
                db.session.delete(attempt)
                db.session.commit()
                return redirect(url_for('attempt_quiz', quiz_id=quiz_id))
            
            selected_option_id = int(answers[answer_key])
            selected_option = Option.query.get_or_404(selected_option_id)

            if selected_option.question_id != question.id:
                flash('Invalid option selected.', 'error')
                db.session.delete(attempt)
                db.session.commit()
                return redirect(url_for('attempt_quiz', quiz_id=quiz_id))
            if selected_option.is_correct:
                 score += 1

            answer = Answer(
    attempt_id=attempt.id,
    user_id=attempt.user_id,
    quiz_id=attempt.quiz_id,
    question_id=question.id,
    selected_option_id=selected_option_id
)
            db.session.add(answer)
        attempt.score = (score / total_questions * 100) if total_questions > 0 else 0
        db.session.commit()
        
        # Update or create Progress
        progress = Progress.query.filter_by(user_id=current_user.id, course_id=quiz.course_id).first()
        if not progress:
            progress = Progress(
    user_id=attempt.user_id,
    quiz_id=attempt.quiz_id,
    course_id=quiz.course_id,
    score=attempt.score,                
    completion_percentage=100.0,         
    created_at=datetime.utcnow()
)
            db.session.add(progress)
            db.session.commit()
        
        # Update completion percentage (example: average quiz scores)
        quiz_attempts = QuizAttempt.query.filter_by(user_id=current_user.id, course_id=quiz.course_id).all()
        if quiz_attempts:
            avg_score = sum(a.score for a in quiz_attempts) / len(quiz_attempts)
            progress.completion_percentage = min(avg_score, 100.0)

        # Award badge if score is high
        if attempt.score >= 80:
            badge = Badge.query.filter_by(name='Quiz Master').first()
            if not badge:
                badge = Badge(
                    name='Quiz Master',
                    description='Scored 80% or higher in a quiz',
                    created_at=datetime.utcnow()
                )
                db.session.add(badge)
                db.session.commit()
            if badge not in progress.badges:
                progress.badges.append(badge)

        db.session.commit()
        flash(f'Quiz completed! Your score: {score}/{total_questions} ({attempt.score:.2f}%', 'success')
        return redirect(url_for('quiz_result', attempt_id=attempt.id))
    
    return render_template('attempt_quiz.html', quiz=quiz, start_time=datetime.utcnow().isoformat())

# View Quiz Result
@csrf.exempt
@login_required
@app.route('/quiz/attempt/<int:attempt_id>')
def quiz_result(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.user_id != current_user.id:
        flash('You can only view your own quiz results.', 'error')
        return redirect(url_for('quiz.quiz_list'))
    
    # Fetch detailed results
    results = []
    for answer in attempt.answers:
        question = answer.question
        selected_option = answer.selected_option
        correct_option = next((opt for opt in question.options if opt.is_correct), None)
        results.append({
            'question_text': question.text,
            'selected_option': selected_option.text,
            'correct_option': correct_option.text if correct_option else None,
            'is_correct': selected_option.is_correct
        })
    
    return render_template('quiz_result.html', attempt=attempt, results=results)
    
# List User Quiz Attempts
@app.route('/quiz/attempts')
@login_required
def user_attempts():
    """List all quiz attempts for the current user."""
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    return render_template('user_attempts.html', attempts=attempts)


#view all courses
@csrf.exempt
@app.route('/all_courses', methods=['GET', 'POST'])
@login_required
def all_course():
    courses = Course.query.all()
    print("Current role:", current_user.role)
    user = User.query.filter_by(email=current_user.email).first()
    mentor = Mentor.query.filter_by(email=current_user.email).first()
    if current_user.role.strip().lower() == 'student':
        return render_template('user_view_courses.html', courses=courses, user=user)

    return render_template('view_courses.html', courses=courses,user=user,mentor=mentor)

# Add course
@csrf.exempt
@app.route('/course/create', methods=['GET', 'POST'])
def create_course():
    if request.method == 'GET':
        return render_template('AddCourse.html')

    if request.method == 'POST':
        course_name = request.form['name']
        existing = Course.query.filter_by(name=course_name).first()
        if existing:
            return '<h1>Course already exists</h1>'

        name = request.form['name']
        description = request.form['description']
        level = request.form['level']
        language = request.form['language']
        category = request.form['category']

        new_course = Course(name=name, description=description, category=category, language=language, level=level)
        db.session.add(new_course)
        db.session.commit()

        module_titles = request.form.getlist('module_titles[]')

        for i, title in enumerate(module_titles):
            module = Module(title=title, course_id=new_course.id)
            db.session.add(module)
            db.session.flush()  # So we can access module.id before commit

            # Fetch submodules for this module
            submodule_names = request.form.getlist(f'submodule_names_{i}[]')
            submodule_videos = request.files.getlist(f'submodule_videos_{i}[]')

            for j in range(len(submodule_names)):
                sub_name = submodule_names[j]
                video_file = submodule_videos[j]

                if video_file:
                    filename = secure_filename(video_file.filename)
                    video_path = os.path.join(UPLOAD_FOLDER, filename)
                    module.video_path = filename
                    video_file.save(video_path)
                    submodule = SubModule(name=sub_name, video_path=video_path, module_id=module.id)
                    db.session.add(submodule)

        db.session.commit()
        return redirect(url_for('all_course'))

#update
@csrf.exempt
@app.route('/course/<int:id>/update', methods=['GET','POST'])
def update_course(id):
    course = Course.query.get_or_404(id)
    if request.method == 'GET':
        # the below line is used to get the courses that the student is already enrolled in.
        return render_template('updateCourse.html', course=course)
    if request.method == 'POST':
        # Update course details
        course.name = request.form['name']
        course.description = request.form['description']
        course.category = request.form['category']
        course.language = request.form['language']
        course.level = request.form['level']
        db.session.commit()

        # Delete existing modules
        Module.query.filter_by(course_id=course.id).delete()

        # Handle new modules
        module_titles = request.form.getlist('module_titles[]')
        module_videos = request.files.getlist('module_videos[]')

        for i in range(len(module_titles)):
            title = module_titles[i]
            video_file = module_videos[i]
            filename = secure_filename(video_file.filename)
            video_path = os.path.join(UPLOAD_FOLDER, filename)
            video_file.save(video_path)

            module = Module(title=title, video_path=video_path, course_id=course.id)
            db.session.add(module)

        db.session.commit()  # Commit all modules at once
        return redirect(url_for('all_course'))

#delete
@csrf.exempt
@app.route('/course/<int:id>/delete', methods=['GET', 'POST'])
def delete_course(id):
    Course.query.filter_by(id = id).delete()
    Module.query.filter_by(course_id=id).delete()
    Progress.query.filter_by(id = id).delete()
    SubModule.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for('all_course'))
    
#view Course
@app.route('/course/<int:id>/view', methods=['GET'])
def view_course(id):
    course = Course.query.get_or_404(id)
    
    # Load modules and submodules
    course_data = []
    for module in course.modules:
        submodules = module.submodules  # directly access submodules from the module
        course_data.append({
            'module': module,
            'submodules': submodules
        })
    return render_template('aboutCourse.html', course=course, modules=course_data)

#learn course
@app.route('/user/<int:id>/learn', methods=['GET', 'POST'])
def learnCourse(id):
    course = Course.query.get_or_404(id)
    modules = course.modules  # All related modules
    user = User.query.filter_by(email=current_user.email).first()
    video_urls = []
    for module in modules:
        video_urls.append(module.submodules)
    print(video_urls)
    return render_template('learn.html', course=course, modules=modules, video_urls=video_urls, user=user)


#chat with mentor
@app.route('/chat_with_mentor/<int:mentor_id>', methods=['GET', 'POST'])
@login_required
def chat_with_mentor(mentor_id):
    if current_user.role != 'student':
        flash("Only students can message mentors.", "danger")
        return redirect(url_for('LandingPage'))

    mentor = Mentor.query.get_or_404(mentor_id)
    form = MessageForm()

    if form.validate_on_submit():
        content = form.content.data
        message = Messages(
            sender_id=current_user.id,
            receiver_id=mentor.id,
            content=content,
            timestamp=datetime.utcnow()
        )
        try:
            db.session.add(message)
            db.session.commit()

            socketio.emit('new_message', {
                'sender': current_user.username,
                'content': content,
                'timestamp': message.timestamp.isoformat(),
                'sender_id': current_user.id
            }, room=f'mentor_{mentor.id}')

            flash("Message sent successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("Failed to send message. Please try again.", "danger")
            print(f"Error sending message: {e}")

        return redirect(url_for('chat_with_mentor', mentor_id=mentor.id))

    # Fetch both student-to-mentor and mentor-to-student messages
    student_messages = Messages.query.filter_by(sender_id=current_user.id, receiver_id=mentor.id).all()
    mentor_messages = MentorMessages.query.filter_by(sender_id=mentor.id, receiver_id=current_user.id).all()
    all_messages = student_messages + mentor_messages
    all_messages.sort(key=lambda x: x.timestamp)

    return render_template('chat_with_mentor.html', form=form, mentor=mentor, messages=all_messages)

# chat with student
@app.route('/mentor/reply_to_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def reply_to_student(student_id):
    # Restrict to mentors only
    if current_user.role != 'mentor':
        flash("Only mentors can reply to students.", "danger")
        return redirect(url_for('LandingPage'))

    student = User.query.get_or_404(student_id)
    form = MessageForm()

    if form.validate_on_submit():
        content = form.content.data
        message = MentorMessages(
            sender_id=current_user.id,  # Mentor's ID
            receiver_id=student.id,     # Student's ID
            content=content,
            timestamp=datetime.utcnow()
        )
        try:
            db.session.add(message)
            db.session.commit()

            # Emit the message to the student's WebSocket room
            socketio.emit('new_message', {
                'sender': current_user.username,
                'content': content,
                'timestamp': message.timestamp.isoformat(),
                'sender_id': current_user.id
            }, room=f'student_{student.id}')

            flash("Reply sent successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("Failed to send reply. Please try again.", "danger")
            print(f"Error sending reply: {e}")

        return redirect(url_for('reply_to_student', student_id=student.id))

    # Fetch previous messages (both student-to-mentor and mentor-to-student)
    student_messages = Messages.query.filter_by(sender_id=student.id, receiver_id=current_user.id).all()
    mentor_messages = MentorMessages.query.filter_by(sender_id=current_user.id, receiver_id=student.id).all()
    # Combine and sort messages by timestamp
    all_messages = student_messages + mentor_messages
    all_messages.sort(key=lambda x: x.timestamp)

    return render_template('reply_to_student.html', form=form, student=student, messages=all_messages)

# WebSocket event to handle mentor joining their room
@socketio.on('join')
def on_join(data):
    user_id = data['user_id']
    role = data['role']
    if role == 'mentor':
        room = f'mentor_{user_id}'
    elif role == 'student':
        room = f'student_{user_id}'
    else:
        return
    join_room(room)
    print(f'{role.capitalize()} {user_id} joined room {room}')

# accessing the video's URL
@app.route('/static/<int:id>/uploads', methods=['GET','POST'])
def video_url(id):
    sub_module = SubModule.query.filter_by(id = id).first()
    return render_template('learn.html', sub_module=sub_module)

# Route to serve the chatbot interface
@app.route('/chat')
def chat():
    return render_template('chat.html')

#logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# forgetPassword
@app.route('/forgetpassword', methods=['GET', 'POST'])
def forgetpassword():
    form = forgetPasswordForm()
    if request.method =='POST'and form.validate_on_submit():
        email = form.email.data
        user_check = User.query.filter_by(email=email).first()

        if not user_check:
            flash("Email not found", "danger")
            return redirect(url_for('forgetpassword'))
        # written the logic for sending email.
        else:
            otp = str(random.randint(100000, 999999))
            session['reset_email'] = email
            session['otp'] = otp
            msg = Message(subject='OTP verification email', recipients = [email])
            
            try:
                # msg.html = render_template('otp_email.html', otp=otp)
                # Thread(target=send_async_email, args=(app, msg)).start()
                # # mail.send(msg)
                # print("Email sending initiated")
                # flash("OTP send to you emial", "info")
                # return redirect(url_for('requestResetPassword'))

                msg.html = render_template('otp_email.html', otp=otp)
                print("Attempting to send email synchronously")
                mail.send(msg)  # Synchronous sending
                print("Email sent successfully")
                flash("OTP sent to your email", "info")
                return redirect(url_for('requestResetPassword'))
            
            except Exception as e:
                print(f"Error preparing email: {str(e)}")
                traceback.print_exc()
                flash("Email send error", "danger")
                return redirect(url_for('forgetpassword'))
    return render_template("forgetpassword.html", form=form)

# requestResetPassword
@app.route('/requestResetPassword', methods=['GET', 'POST'])
def requestResetPassword():
    form = requestResetPasswordForm()
    if request.method == 'POST' and form.validate_on_submit():
        input_otp = form.otp.data
        newpwd = form.newpwd.data
        confirm = form.confirmpwd.data

        # Get OTP and email from session
        session_otp = session.get('otp')
        reset_email = session.get('reset_email')

        if not session_otp or not reset_email:
            flash("Session expired. Please try again.", "danger")
            return redirect(url_for('forgetpassword'))

        if input_otp != session_otp:
            flash("Invalid OTP.", "danger")
            return redirect(url_for('requestResetPassword'))

        if newpwd != confirm:
            flash("Passwords do not match.", "warning")
            return redirect(url_for('requestResetPassword'))

        # Find user again just to be sure
        user = User.query.filter_by(email=reset_email).first()
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for('forgetpassword'))

        # Hash and update new password
        hashed_password = bcrypt.generate_password_hash(newpwd).decode('utf-8')
        user.password = hashed_password
        db.session.commit()

        # Clear session after successful reset
        session.pop('otp', None)
        session.pop('reset_email', None)

        flash("Password reset successful. Please log in.", "success")
        return redirect(url_for('login'))

    return render_template("requestResetPassword.html", form=form)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(debug=True)
