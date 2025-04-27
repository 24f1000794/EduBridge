
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, ValidationError, validators,SubmitField,SelectField,SelectMultipleField,EmailField


class RegistrationForm(FlaskForm):
    username = StringField('Username', [validators.DataRequired(), validators.Length(min=4, max=150)])
    fullname = StringField('Fullname', [validators.DataRequired(), validators.Length(min=4, max=150)])
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    password = PasswordField('Password', [validators.DataRequired(), validators.Length(min=6)])
    qualification = StringField('Qualification', [validators.DataRequired()])
    language_pref = SelectField(
    "Preferred Language",
    choices=[('hindi', 'Hindi'), ('english', 'English')],
    validators=[validators.DataRequired()]
)

    interest = SelectMultipleField(
    "Subject of Interest",
    choices=[
        ('physics', 'Physics'),
        ('chemistry', 'Chemistry'),
        ('maths', 'Maths'),
        ('computer science', 'Computer Science')
    ],
    validators=[validators.DataRequired()]
)
    date_of_birth = StringField('Date of Birth', [validators.DataRequired()])
    
    submit = SubmitField('Submit')

    def validate_confirm_password(self, field):
        if field.data != self.password.data:
            raise ValidationError('Passwords must match.')
    

class LoginForm(FlaskForm):
    username = StringField('Username', [validators.DataRequired(), validators.Length(min=4, max=150)])
    password = PasswordField('Password', [validators.DataRequired(), validators.Length(min=6)])
    submit = SubmitField('Submit')


class mentorRegistration(FlaskForm):
    username = StringField('Username', [validators.DataRequired(), validators.Length(min=4, max=150)])
    mentor_name = StringField('Mentor Name', [validators.DataRequired(), validators.Length(min=4, max=20)])
    email = EmailField('Email', [validators.DataRequired(), validators.Email()])
    password = PasswordField('Password', [validators.DataRequired(), validators.Length(min=6)])
    expertise = StringField('Expertise' , [validators.DataRequired()])
    availiable = SelectMultipleField('Available Time', choices=[
    ('morning', 'Morning'),
    ('afternoon', 'Afternoon'),
    ('evening', 'Evening'),
    ('midnight', 'Midnight')
])
    language_pref = SelectField(
    "Preferred Language",
    choices=[('hindi', 'Hindi'), ('english', 'English')],
    validators=[validators.DataRequired()]
    )
    submit = SubmitField('Submit')

class forgetPasswordForm(FlaskForm):
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    submit = SubmitField('Submit')

class requestResetPasswordForm(FlaskForm):
    otp = StringField('OTP', [validators.DataRequired()])
    newpwd = StringField('New Password', [validators.data_required(), validators.length(min=6, max=8)])
    confirmpwd = StringField('Confirm New Password', [validators.data_required(), validators.length(min=6)])
    submit = SubmitField('Submit')

    def validate_confirm_password(self, field):
        if field.data != self.password.data:
            raise ValidationError('Passwords must match.')
    

# Form for sending messages
class MessageForm(FlaskForm):
    content = TextAreaField('Message', validators=[validators.DataRequired()])
    submit = SubmitField('Send')
