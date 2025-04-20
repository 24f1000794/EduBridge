from datetime import datetime
import os
import random
from flask_mail import Mail,Message 
from flask import Flask, jsonify
from flask import render_template, redirect, request, url_for,session,flash
from flask_login import current_user,login_required,LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
from config import Config
from models import db, User
from forms.userform import RegistrationForm, LoginForm,forgetPasswordForm,requestResetPasswordForm,mentorRegistration
from werkzeug.utils import secure_filename
from models.user import User, Course,Mentor,Progress,Module,Message,Quiz,Question,Option,QuizAttempt,Answer,Badge




load_dotenv() #load environmental variable

app = Flask(__name__)
app.config.from_object(Config) # load database configuration
db.init_app(app) #initialize the DB
csrf = CSRFProtect(app) # enable CSRF protection
bcrypt = Bcrypt(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

UPLOAD_FOLDER = 'static/uploads/' 

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
        role = form.role.data
        date_of_birth = form.date_of_birth.data

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Check if username already exists
        exist_user = User.query.filter_by(username=username).first()
        if exist_user:
            flash("Username already exists. Try another one", "danger")
            return redirect(url_for('register'))  

        # Check for missing fields
        if not username or not password or not fullname or not email:
            flash("Please fill all required fields.", "warning")
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
            role=role
        )
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login')) 
    # Handle validation errors
    flash("Form validation failed. Please check the details.", "danger")
    return render_template("registration.html", form=form) 

@app.route('/mentor/register', methods=['GET', 'POST'])
def mentor_register():
    return render_template('mentor_register.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'GET':
        return render_template("login.html", form=form)
    if request.method == 'POST' and form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        # Check if user exists
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['username'] = user.username
            if user.role == 'student':
                return redirect(url_for('dashboard'))
            elif user.role == 'mentor':
                return redirect(url_for('mentor_dashboard'))
            else:
                return redirect(url_for('AdminDashboard'))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for('login'))
        
      # If form fails validation (e.g., CSRF), this part will be reached
    flash("Login form validation failed. Please try again.", "danger")
    return render_template("login.html", form=form)

@app.route('/dashboard')
# @login_required
def dashboard():
    if 'username' in session:
        return f"Welcome, {session['username']}! <a href='/logout'>Logout</a>"
    else:
        flash("You must log in first.", "warning")
        return redirect(url_for('login'))


@app.route('/AdminDashboard', methods=['GET'])
def AdminDashboard():
    return render_template("AdminDashboard.html")


#add mentor
@csrf.exempt
@app.route('/mentor/create', methods = ['GET','POST'])
def create_mentor():
    if request.method == 'GET':
        return render_template('AddMentors.html')
    if request.method == 'POST':
        name = request.form.get('name')
        expertise = request.form.get('expert')
        availability = request.form.get('availability')
        email = request.form.get('email')

        #check existence
        mentor = Mentor.query.filter_by(email = email).first()
        if mentor:
            flash("Mentor already exists", "danger")
            return redirect(url_for('create_mentor'))
        new_mentor = Mentor(name=name,expertise=expertise,availability=availability,email=email)
        db.session.add(new_mentor)
        db.session.commit()
        return redirect(url_for('AdminDashboard'))

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
            return redirect(url_for('AdminDashboard'))
        flash('Mentor is not exist with the give id', 'danger')
        return redirect(url_for('update_mentor', id=id))

#delete mentor
@csrf.exempt
@app.route('/delete_mentor/<int:mentor_id>/delete', methods=['GET','POST'])
def delete_mentor(mentor_id):
    mentor = Mentor.query.get(mentor_id)
    if not mentor:
        return jsonify({"error": "Mentor not found"}), 404

    try:
        Message.query.filter_by(receiver_id=mentor.id).delete()
        db.session.delete(mentor)
        db.session.commit()
        return jsonify({"message": "Mentor deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

#view mentor
@app.route('/mentor/view', methods=['GET', 'POST'])  
def view_mentor():
    return render_template('viewMentor.html')


# List All Quizzes
@csrf.exempt
@app.route('/quizzes')
def quiz_list():
    course_id = request.args.get('course_id', type=int)
    if course_id:
        quizzes = Quiz.query.filter_by(course_id=course_id).all()
    else:
        quizzes = Quiz.query.all()
    courses = Course.query.all()
    return render_template('quiz_list.html', quizzes=quizzes, courses=courses)

# Create Quiz
@csrf.exempt
@app.route('/quiz/create', methods=['GET', 'POST'])
@login_required
def create_quiz():
    if current_user.role not in ['mentor', 'admin']:
        flash('Only mentors or admins can create quizzes.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        course_id = request.form.get('course_id')
        language = request.form.get('language', 'en')
        
        if not title or not course_id:
            flash('Title and course are required.', 'error')
            return redirect(url_for('create_quiz'))
        
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
        
        questions_data = []
        i = 0
        while f'questions[{i}][text]' in request.form:
            text = request.form.get(f'questions[{i}][text]')
            options = [
                request.form.get(f'questions[{i}][options][{j}]') for j in range(4)
            ]
            correct = request.form.get(f'questions[{i}][correct]')
            if not text or not all(options) or not correct or not (0 <= int(correct) <= 3):
                flash('Invalid question or option data.', 'error')
                return redirect(url_for('create_quiz'))
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
                'correct': correct
            })
            i += 1
        
        if not questions_data:
            flash('At least one question is required.', 'error')
            return redirect(url_for('create_quiz'))
        
        quiz = Quiz(
            title=title,
            course_id=course_id,
            created_by=current_user.id,  # Uses User.id
            created_at=datetime.utcnow(),
            language=language
        )
        db.session.add(quiz)
        db.session.commit()
        
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
        return redirect(url_for('quiz_list'))
    
    courses = Course.query.all()
    return render_template('create_quiz.html', courses=courses)

# View Quiz Details
@app.route('/quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    # Cache quiz data for offline access
    quiz_data = {
        'id': quiz.id,
        'title': quiz.title,
        'course': quiz.course.name,
        'questions': len(quiz.questions),
        'level': quiz.course.level or 'Intermediate',
        'estimated_time': len(quiz.questions) * 1  # 1 minute per question
    }
    return render_template('quiz_detail.html', quiz=quiz, quiz_data=quiz_data)

# Attempt Quiz
@app.route('/quiz/<int:quiz_id>/attempt', methods=['GET', 'POST'])
@login_required
def attempt_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        answers = request.form
        attempt = QuizAttempt(
            user_id=current_user.id,
            quiz_id=quiz.id,
            attempted_at=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.commit()
        
        score = 0
        total_questions = len(quiz.questions)
        for question in quiz.questions:
            answer_key = f'answers[{question.id}]'
            if answer_key not in answers:
                flash('Please answer all questions.', 'error')
                db.session.delete(attempt)
                db.session.commit()
                return redirect(url_for('attempt_quiz', quiz_id=quiz_id))
            selected_option_id = int(answers[answer_key])
            selected_option = Option.query.get_or_404(selected_option_id)
            if selected_option.is_correct:
                score += 1
            answer = Answer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option_id=selected_option_id
            )
            db.session.add(answer)
        attempt.score = score
        db.session.commit()
        
        # Award badge if score is high
        if score >= total_questions * 0.8:  # 80% or higher
            progress = Progress.query.filter_by(
                user_id=current_user.id,
                course_id=quiz.course_id
            ).first()
            if progress:
                progress.badges = 'Quiz Master'
            else:
                progress = Progress(
                    user_id=current_user.id,
                    course_id=quiz.course_id,
                    badges='Quiz Master'
                )
                db.session.add(progress)
            db.session.commit()
        
        flash(f'Quiz completed! Your score: {score}/{total_questions}', 'success')
        return redirect(url_for('quiz_result', attempt_id=attempt.id))
    
    return render_template('attempt_quiz.html', quiz=quiz)

# Edit Quiz
@app.route('/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    if current_user.role not in ['mentor', 'admin']:
        flash('Only mentors or admins can edit quizzes.', 'error')
        return redirect(url_for('dashboard'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.created_by != current_user.id:
        flash('You can only edit your own quizzes.', 'error')
        return redirect(url_for('quiz_list'))
    
    if request.method == 'POST':
        quiz.title = request.form.get('title')
        quiz.course_id = request.form.get('course_id')
        language = request.form.get('language', quiz.language or 'en')
        
        if not quiz.title or not quiz.course_id:
            flash('Title and course are required.', 'error')
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
        
        # Translate title if language changed
        if language != (quiz.language or 'en'):
            try:
                response = requests.post(
                    'https://libretranslate.com/translate',
                    json={'q': quiz.title, 'source': 'en', 'target': language}
                )
                quiz.title = response.json()['translatedText']
            except:
                flash('Translation failed, using original title.', 'warning')
        
        # Delete existing questions and options
        for question in quiz.questions:
            db.session.delete(question)
        db.session.commit()
        
        # Add new questions
        questions_data = []
        i = 0
        while f'questions[{i}][text]' in request.form:
            text = request.form.get(f'questions[{i}][text]')
            options = [
                request.form.get(f'questions[{i}][options][{j}]') for j in range(4)
            ]
            correct = request.form.get(f'questions[{i}][correct]')
            if not text or not all(options) or not correct or not (0 <= int(correct) <= 3):
                flash('Invalid question or option data.', 'error')
                return redirect(url_for('edit_quiz', quiz_id=quiz_id))
            # Translate question and options
            if language != (quiz.language or 'en'):
                try:
                    text_response = requests.post(
                        'https://libretranslate.com/translate',
                        json={'q': text, 'source': 'en', 'target': language}
                    )
                    text = text_response.json()['translatedText']
                    translated_options = []
                    for opt in options:
                        opt_response = requests.post(
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
                'correct': correct
            })
            i += 1
        
        if not questions_data:
            flash('At least one question is required.', 'error')
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
        
        for q_data in questions_data:
            question = Question(text=q_data['text'], quiz_id=quiz.id)
            db.session.add(question)
            db.session.commit()
            for idx, option_text in enumerate(q_data['options']):
                is_correct = idx == int(q_data['correct'])
                option = Option(text=option_text, is_correct=is_correct, question_id=question.id)
                db.session.add(option)
            db.session.commit()
        
        quiz.language = language
        db.session.commit()
        flash('Quiz updated successfully!', 'success')
        return redirect(url_for('quiz_list'))
    
    courses = Course.query.all()
    return render_template('edit_quiz.html', quiz=quiz, courses=courses)

# Delete Quiz
@app.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    if current_user.role not in ['mentor', 'admin']:
        flash('Only mentors or admins can delete quizzes.', 'error')
        return redirect(url_for('dashboard'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.created_by != current_user.id:
        flash('You can only delete your own quizzes.', 'error')
        return redirect(url_for('quiz_list'))
    
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted successfully!', 'success')
    return redirect(url_for('quiz_list'))

# View Quiz Result
@app.route('/quiz/attempt/<int:attempt_id>')
@login_required
def quiz_result(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.user_id != current_user.id:
        flash('You can only view your own quiz results.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('quiz_result.html', attempt=attempt)

# Add course
#create
@csrf.exempt
@app.route('/course/create', methods=['GET', 'POST'])
def create_course():
    if request.method == 'GET':
        return render_template('AddCourse.html')
    
    if request.method == 'POST':
        # check if course already exists
        course_name = request.form['name']
        existing = Course.query.filter_by(name=course_name).first()
        if existing:
            return '<h1>Course already exists</h1>'

        # Create the course
        name = request.form['name']
        description = request.form['description']
        level = request.form['level']
        language = request.form['language']

        new_course = Course(name=name, description=description, level=level, language=language)
        db.session.add(new_course)
        db.session.commit()

        # Save modules
        module_titles = request.form.getlist('module_titles[]')
        module_videos = request.files.getlist('module_videos[]')

        for i in range(len(module_titles)):
            title = module_titles[i]
            video_file = module_videos[i]

            if video_file:
                filename = secure_filename(video_file.filename)
                video_path = os.path.join(UPLOAD_FOLDER, filename)
                video_file.save(video_path)

                # Save module in DB
                module = Module(title=title, video_path=video_path, course_id=new_course.id)
                db.session.add(module)

        db.session.commit()
        return redirect(url_for('AdminDashboard'))

#update
@csrf.exempt
@app.route('/course/<int:id>/update', methods=['GET','POST'])
def update_course(id):
    course = Course.query.get_or_404(id)
    if request.method == 'GET':
        # the below line is used to get the courses that the student is already enrolled in.
        return render_template('updateCourse.html', course=course)
    else:
        if course:
           course.name = request.form['name']
           course.description = request.form['description']
           course.category  = request.form['level']
        #    course.content_url = request.form['content']
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
            db.session.commit()
            return redirect(url_for('AdminDashboard'))
        return '<h1> Course is not exist with given id </h1><a href=/student/create>Go back</a>'

#delete
@csrf.exempt
@app.route('/course/<int:id>/delete', methods=['GET', 'POST'])
def delete_user(id):
    Course.query.filter_by(id = id).delete()
    Module.query.filter_by(course_id=id).delete()
    Progress.query.filter_by(id = id).delete()
    db.session.commit()
    return redirect(url_for('AdminDashboard'))
    
#view Course
@csrf.exempt
@app.route('/course/<int:id>/view', methods=['GET', 'POST'])
def view_student(id):
    details_s = Course.query.get_or_404(id)
    return render_template('aboutCourse.html', course = details_s)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

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
            msg = Message(
                subject = "OTP for verification",
                recipients = [email]
            )
            
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
    app.run(debug=True)




# https://www.freecodecamp.org/news/setup-email-verification-in-flask-app/