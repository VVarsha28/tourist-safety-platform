from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
import uuid
from datetime import date, timedelta
from models import db, User, TouristProfile

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_authority:
            return redirect(url_for('authority.dashboard'))
        return redirect(url_for('tourist.home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")
            if user.is_authority:
                return redirect(url_for('authority.dashboard'))
            return redirect(url_for('tourist.home'))
        else:
            flash("Invalid email or password. Please check your credentials.", "danger")

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('tourist.home'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        nationality = request.form.get('nationality', 'Unknown').strip()
        id_number = request.form.get('id_number', '').strip()
        blood_group = request.form.get('blood_group', 'Unknown').strip()
        emergency_name = request.form.get('emergency_contact_name', '').strip()
        emergency_phone = request.form.get('emergency_contact_phone', '').strip()
        emergency_relation = request.form.get('emergency_contact_relation', 'Family').strip()

        if not name or not email or not password:
            flash("Please fill in all required fields (Name, Email, Password).", "danger")
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for('auth.login'))

        # Create user
        user = User(
            name=name,
            email=email,
            role='tourist',
            phone=phone
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Generate unique Digital Tourist ID
        random_suffix = str(uuid.uuid4().hex[:6]).upper()
        country_code = nationality[:3].upper() if len(nationality) >= 3 else "TRV"
        digital_id_code = f"ST-2026-{country_code}-{random_suffix}"

        # Create Profile
        profile = TouristProfile(
            user_id=user.id,
            nationality=nationality,
            id_number=id_number,
            blood_group=blood_group,
            emergency_contact_name=emergency_name,
            emergency_contact_phone=emergency_phone,
            emergency_contact_relation=emergency_relation,
            trip_start=date.today(),
            trip_end=date.today() + timedelta(days=14),
            digital_id_code=digital_id_code
        )
        db.session.add(profile)
        db.session.commit()

        login_user(user)
        flash(f"Account created successfully! Your Digital Tourist ID is {digital_id_code}.", "success")
        return redirect(url_for('tourist.home'))

    return render_template('register.html')


@auth_bp.route('/demo-login/<demo_type>')
def demo_login(demo_type):
    """Fast one-click login switcher for seamless live hackathon demos."""
    mapping = {
        'authority': 'authority@safetrail.gov',
        'elena': 'elena@demo.com',    # Caution Zone
        'carlos': 'carlos@demo.com',  # Active SOS
        'aarav': 'aarav@demo.com'     # Safe Zone
    }

    target_email = mapping.get(demo_type.lower())
    if not target_email:
        flash("Invalid demo account selection.", "danger")
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=target_email).first()
    if not user:
        flash("Demo database has not been seeded yet. Please seed database first.", "warning")
        return redirect(url_for('auth.login'))

    login_user(user)
    if user.is_authority:
        flash("Logged in to Authority Operations Command Center.", "info")
        return redirect(url_for('authority.dashboard'))
    else:
        flash(f"Switched to Tourist Account: {user.name}", "info")
        return redirect(url_for('tourist.home'))


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('auth.login'))
