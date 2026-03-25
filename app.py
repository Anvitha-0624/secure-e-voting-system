from flask import Flask, render_template, request, redirect, session, url_for
from models import db, User, Vote
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import smtplib
import random

def send_otp_email(receiver_email, otp):
    sender_email = "as0964603@gmail.com"
    sender_password = "ukya abdq deyf lscf"

    subject = "Secure Voting OTP"
    body = f"""
    Your OTP for Secure Voting System is: {otp}

    This OTP is valid for 2 minutes.
    Do not share this with anyone.
    """

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()
    
app = Flask(__name__)
app.secret_key = "secret123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voting.db'
db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template("home.html")

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']

        # 🔎 Check existing user
        existing_user = User.query.filter_by(phone=phone).first() \
                        or User.query.filter_by(email=email).first()

        if existing_user:
            return render_template("already_voted.html")

        # ✅ Save new user
        new_user = User(
            phone=phone,
            email=email,
            password=password
        )

        db.session.add(new_user)
        db.session.commit()

        # 🟢 Go to login page
        return redirect('/login')

    return render_template("register.html")
# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(phone=phone, email=email, password=password).first()

        if not user:
            return "Invalid credentials"

        if user.has_voted:
            return redirect(url_for('already_voted'))

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        user.otp = otp
        user.otp_time = datetime.now()
        db.session.commit()

        # Send OTP to email
        send_otp_email(user.email, otp)

        session['user_id'] = user.id

        return redirect(url_for('otp'))

    return render_template("login.html")

# ---------------- OTP ----------------
@app.route('/otp', methods=['GET', 'POST'])
def otp():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        entered_otp = request.form.get("otp")

        # Check expiry (2 minutes)
        if datetime.now() > user.otp_time + timedelta(minutes=2):
            return "OTP Expired. Please login again."

        if entered_otp == user.otp:
            return redirect(url_for('vote_page'))
        else:
            return "Invalid OTP"

    return render_template('otp.html')
#---------votepage---------------
@app.route('/vote', methods=['GET'])
def vote_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    existing_vote = Vote.query.filter_by(user_id=session['user_id']).first()
    if existing_vote:
        return redirect(url_for('already_voted'))

    return render_template('vote.html')
# ---------------- VOTE ----------------
@app.route('/submit_vote', methods=['POST'])
def submit_vote():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    candidate = request.form.get('party')
    print("selected condidate:",candidate)
    user_id = session['user_id']

    existing_vote = Vote.query.filter_by(user_id=user_id).first()
    if existing_vote:
        return redirect(url_for('already_voted'))

    if candidate:
        new_vote = Vote(candidate=candidate, user_id=user_id)
        db.session.add(new_vote)

        # ✅ ADD THIS LINE (IMPORTANT)
        user = User.query.get(user_id)
        user.has_voted = True

        db.session.commit()
        return redirect(url_for('success'))

    return redirect(url_for('vote_page'))
# ---------------- STATUS PAGES ----------------
@app.route('/success')
def success():
    return render_template("success.html")

@app.route('/already_voted')
def already_voted():
    return render_template('already_voted.html')


# ------------------ ADMIN LOGIN ------------------
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin1!"

@app.route('/admin', methods=['GET', 'POST'])
def admin():

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:

            votes_A = Vote.query.filter_by(candidate='BVP').count()
            votes_B = Vote.query.filter_by(candidate='JPP').count()
            votes_C = Vote.query.filter_by(candidate='LSP').count()

            return render_template(
                "admin_dashboard.html",
                votes_A=votes_A,
                votes_B=votes_B,
                votes_C=votes_C
            )
        else:
            return "Invalid Email or Password"

    return render_template("admin_login.html")

if __name__ == "__main__":
    app.run(debug=True)