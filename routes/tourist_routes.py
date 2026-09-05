from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from functools import wraps
from models import db, User, TouristProfile, Itinerary, Zone, POI, LocationPing, Alert, SOSEvent, Incident
from services.geo_service import find_current_zone, get_nearest_pois, haversine_distance
from services.ai_engine import AIRiskScoringEngine, AISafetyAssistant
from services.qr_service import generate_qr_base64

tourist_bp = Blueprint('tourist', __name__, url_prefix='/tourist')

def tourist_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_tourist:
            flash("Authority accounts cannot access tourist view. Please use the Authority Dashboard.", "warning")
            return redirect(url_for('authority.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@tourist_bp.route('/')
@tourist_required
def home():
    profile = current_user.profile
    # Fetch recent active SOS if any
    active_sos = SOSEvent.query.filter_by(tourist_id=current_user.id).filter(SOSEvent.status != 'resolved').order_by(SOSEvent.timestamp.desc()).first()
    
    # Fetch latest location ping
    latest_ping = LocationPing.query.filter_by(tourist_id=current_user.id).order_by(LocationPing.timestamp.desc()).first()
    lat = latest_ping.lat if latest_ping else 26.9205
    lng = latest_ping.lng if latest_ping else 75.8245

    zones = Zone.query.all()
    current_zone = find_current_zone(lat, lng, zones)

    # Calculate live AI risk score
    all_incidents = Incident.query.all()
    risk_data = AIRiskScoringEngine.calculate_risk_score(
        current_zone=current_zone,
        lat=lat,
        lng=lng,
        recent_incidents=all_incidents
    )

    # Active alerts count
    unread_alerts = Alert.query.filter_by(tourist_id=current_user.id, dismissed=False).count()

    return render_template(
        'tourist/index.html',
        profile=profile,
        active_sos=active_sos,
        latest_ping=latest_ping,
        current_zone=current_zone,
        risk_data=risk_data,
        unread_alerts=unread_alerts
    )


@tourist_bp.route('/profile', methods=['GET', 'POST'])
@tourist_required
def profile():
    profile = current_user.profile
    if not profile:
        profile = TouristProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()

    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name).strip()
        current_user.phone = request.form.get('phone', current_user.phone).strip()

        profile.nationality = request.form.get('nationality', profile.nationality).strip()
        profile.id_number = request.form.get('id_number', profile.id_number).strip()
        profile.blood_group = request.form.get('blood_group', profile.blood_group).strip()
        profile.allergies = request.form.get('allergies', profile.allergies).strip()
        profile.medical_conditions = request.form.get('medical_conditions', profile.medical_conditions).strip()
        profile.emergency_contact_name = request.form.get('emergency_contact_name', profile.emergency_contact_name).strip()
        profile.emergency_contact_phone = request.form.get('emergency_contact_phone', profile.emergency_contact_phone).strip()
        profile.emergency_contact_relation = request.form.get('emergency_contact_relation', profile.emergency_contact_relation).strip()
        profile.accommodation_address = request.form.get('accommodation_address', profile.accommodation_address).strip()

        trip_start = request.form.get('trip_start')
        trip_end = request.form.get('trip_end')
        if trip_start:
            try:
                profile.trip_start = datetime.strptime(trip_start, '%Y-%m-%d').date()
            except ValueError:
                pass
        if trip_end:
            try:
                profile.trip_end = datetime.strptime(trip_end, '%Y-%m-%d').date()
            except ValueError:
                pass

        db.session.commit()
        flash("Your Safety Profile has been updated successfully!", "success")
        return redirect(url_for('tourist.profile'))

    return render_template('tourist/profile.html', profile=profile)


@tourist_bp.route('/digital-id')
@tourist_required
def digital_id():
    profile = current_user.profile
    if not profile:
        return redirect(url_for('tourist.profile'))

    verify_url = request.host_url.rstrip('/') + url_for('public.verify_id', digital_id_code=profile.digital_id_code)
    qr_data_uri = generate_qr_base64(verify_url)

    # Get current risk status
    latest_ping = LocationPing.query.filter_by(tourist_id=current_user.id).order_by(LocationPing.timestamp.desc()).first()
    lat = latest_ping.lat if latest_ping else 26.9205
    lng = latest_ping.lng if latest_ping else 75.8245
    current_zone = find_current_zone(lat, lng, Zone.query.all())
    risk = AIRiskScoringEngine.calculate_risk_score(current_zone, lat, lng)

    return render_template(
        'tourist/digital_id.html',
        profile=profile,
        verify_url=verify_url,
        qr_data_uri=qr_data_uri,
        risk=risk
    )


@tourist_bp.route('/alerts')
@tourist_required
def alerts():
    alerts_list = Alert.query.filter_by(tourist_id=current_user.id).order_by(Alert.timestamp.desc()).all()
    return render_template('tourist/alerts.html', alerts=alerts_list)


@tourist_bp.route('/alerts/<int:alert_id>/dismiss', methods=['POST'])
@tourist_required
def dismiss_alert(alert_id):
    alert = Alert.query.filter_by(id=alert_id, tourist_id=current_user.id).first()
    if alert:
        alert.dismissed = True
        db.session.commit()
    return redirect(url_for('tourist.alerts'))


@tourist_bp.route('/report', methods=['GET', 'POST'])
@tourist_required
def report_incident():
    if request.method == 'POST':
        incident_type = request.form.get('type', 'other')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        address = request.form.get('address', '').strip()
        lat = request.form.get('lat', type=float)
        lng = request.form.get('lng', type=float)
        anonymous = bool(request.form.get('anonymous'))

        if not title or not description:
            flash("Please provide an incident title and detailed description.", "danger")
            return redirect(url_for('tourist.report_incident'))

        # Fallback coordinates if empty
        if lat is None or lng is None:
            latest_ping = LocationPing.query.filter_by(tourist_id=current_user.id).order_by(LocationPing.timestamp.desc()).first()
            lat = latest_ping.lat if latest_ping else 26.9205
            lng = latest_ping.lng if latest_ping else 75.8245

        incident = Incident(
            tourist_id=current_user.id,
            type=incident_type,
            title=title,
            description=description,
            address=address,
            lat=lat,
            lng=lng,
            anonymous=anonymous,
            status='submitted',
            timestamp=datetime.utcnow()
        )
        db.session.add(incident)
        db.session.commit()
        flash("Incident report submitted. Safety officers in this sector have been notified.", "success")
        return redirect(url_for('tourist.report_incident'))

    my_reports = Incident.query.filter_by(tourist_id=current_user.id).order_by(Incident.timestamp.desc()).all()
    return render_template('tourist/report.html', my_reports=my_reports)


@tourist_bp.route('/resources')
@tourist_required
def resources():
    pois = POI.query.all()
    latest_ping = LocationPing.query.filter_by(tourist_id=current_user.id).order_by(LocationPing.timestamp.desc()).first()
    lat = latest_ping.lat if latest_ping else 26.9205
    lng = latest_ping.lng if latest_ping else 75.8245
    nearest_pois = get_nearest_pois(lat, lng, pois, limit=10)
    return render_template('tourist/resources.html', nearest_pois=nearest_pois)


# ==================== JSON REST APIs for Mobile UI ====================

@tourist_bp.route('/api/location/ping', methods=['POST'])
@tourist_required
def location_ping():
    data = request.get_json() or {}
    lat = data.get('lat')
    lng = data.get('lng')
    accuracy = data.get('accuracy', 10.0)

    if lat is None or lng is None:
        return jsonify({'error': 'Latitude and Longitude required'}), 400

    ping = LocationPing(
        tourist_id=current_user.id,
        lat=lat,
        lng=lng,
        accuracy=accuracy,
        timestamp=datetime.utcnow()
    )
    db.session.add(ping)

    # Detect Zone
    zones = Zone.query.all()
    current_zone = find_current_zone(lat, lng, zones)

    # Check if this enters a Caution or Restricted Zone and generate alert if not already sent recently
    triggered_alert = None
    if current_zone and current_zone.risk_level in ['caution', 'restricted']:
        recent_alert = Alert.query.filter_by(tourist_id=current_user.id, title=f"Zone Alert: {current_zone.name}").first()
        if not recent_alert:
            severity = 'danger' if current_zone.risk_level == 'restricted' else 'caution'
            advice = (
                "Turn back or seek official escort. Hazardous terrain/curfew active." 
                if current_zone.risk_level == 'restricted' 
                else "Avoid unlit alleys. Keep bag closed and phone secure."
            )
            triggered_alert = Alert(
                tourist_id=current_user.id,
                type="zone_alert",
                severity=severity,
                title=f"Zone Alert: {current_zone.name}",
                message=f"You entered a {current_zone.risk_level.upper()} zone: {current_zone.description}",
                suggested_action=advice,
                timestamp=datetime.utcnow()
            )
            db.session.add(triggered_alert)

    db.session.commit()

    # Calculate live risk score
    all_incidents = Incident.query.all()
    risk = AIRiskScoringEngine.calculate_risk_score(current_zone, lat, lng, all_incidents)

    return jsonify({
        'success': True,
        'current_zone': current_zone.to_dict() if current_zone else None,
        'risk': risk,
        'new_alert': triggered_alert.to_dict() if triggered_alert else None
    })


@tourist_bp.route('/api/sos/trigger', methods=['POST'])
@tourist_required
def trigger_sos():
    data = request.get_json() or {}
    lat = data.get('lat')
    lng = data.get('lng')
    voice_note_text = data.get('voice_note_text', '').strip()

    if lat is None or lng is None:
        latest = LocationPing.query.filter_by(tourist_id=current_user.id).order_by(LocationPing.timestamp.desc()).first()
        lat = latest.lat if latest else 26.9205
        lng = latest.lng if latest else 75.8245

    # Check for existing active SOS
    existing = SOSEvent.query.filter_by(tourist_id=current_user.id).filter(SOSEvent.status != 'resolved').first()
    if existing:
        if voice_note_text:
            existing.voice_note_text = voice_note_text
            db.session.commit()
        return jsonify({
            'success': True,
            'sos_id': existing.id,
            'status': existing.status,
            'message': 'SOS already active.'
        })

    profile = current_user.profile
    sos = SOSEvent(
        tourist_id=current_user.id,
        lat=lat,
        lng=lng,
        timestamp=datetime.utcnow(),
        status='active',
        notes=f"SOS beacon triggered from Tourist Web App. Medical Profile attached.",
        voice_note_text=voice_note_text
    )
    db.session.add(sos)

    # Also generate high-priority local alert
    sos_alert = Alert(
        tourist_id=current_user.id,
        type="emergency",
        severity="danger",
        title="EMERGENCY SOS TRANSMITTED",
        message="Your live coordinates & medical profile have been dispatched to Regional Command.",
        suggested_action="Remain calm. Move to an illuminated public space if safe.",
        timestamp=datetime.utcnow()
    )
    db.session.add(sos_alert)
    db.session.commit()

    return jsonify({
        'success': True,
        'sos_id': sos.id,
        'status': sos.status,
        'simulated_sms': {
            'recipient': profile.emergency_contact_phone if profile else 'Configured Contact',
            'contact_name': profile.emergency_contact_name if profile else 'Emergency Contact',
            'message': f"EMERGENCY ALERT: SafeTrail SOS triggered by {current_user.name} at coordinates {lat:.4f}, {lng:.4f}. Live tracking link sent to authorities."
        }
    })


@tourist_bp.route('/api/sos/status', methods=['GET'])
@tourist_required
def get_sos_status():
    active_sos = SOSEvent.query.filter_by(tourist_id=current_user.id).order_by(SOSEvent.timestamp.desc()).first()
    if not active_sos:
        return jsonify({'active': False})
    return jsonify({
        'active': active_sos.status != 'resolved',
        'sos': active_sos.to_dict()
    })


@tourist_bp.route('/api/sos/update-note', methods=['POST'])
@tourist_required
def update_sos_note():
    data = request.get_json() or {}
    text = data.get('voice_note_text', '').strip()
    active_sos = SOSEvent.query.filter_by(tourist_id=current_user.id).filter(SOSEvent.status != 'resolved').first()
    if active_sos:
        active_sos.voice_note_text = text
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'No active SOS found'}), 404


@tourist_bp.route('/api/ai/chat', methods=['POST'])
@tourist_required
def ai_chat():
    data = request.get_json() or {}
    message = data.get('message', '')

    profile = current_user.profile
    latest_ping = LocationPing.query.filter_by(tourist_id=current_user.id).order_by(LocationPing.timestamp.desc()).first()
    lat = latest_ping.lat if latest_ping else 26.9205
    lng = latest_ping.lng if latest_ping else 75.8245

    zones = Zone.query.all()
    current_zone = find_current_zone(lat, lng, zones)
    all_incidents = Incident.query.all()
    risk = AIRiskScoringEngine.calculate_risk_score(current_zone, lat, lng, all_incidents)

    pois = POI.query.all()
    hospitals = [p for p in get_nearest_pois(lat, lng, pois) if p['poi']['type'] == 'hospital']
    police_stations = [p for p in get_nearest_pois(lat, lng, pois) if p['poi']['type'] == 'police']
    embassies = [p for p in get_nearest_pois(lat, lng, pois) if p['poi']['type'] == 'embassy']

    tourist_context = {
        'name': current_user.name,
        'zone_name': current_zone.name if current_zone else 'Jaipur Central District',
        'risk_level': risk['level'],
        'risk_score': risk['score'],
        'emergency_contact': f"{profile.emergency_contact_name} ({profile.emergency_contact_phone})" if profile and profile.emergency_contact_name else "Local Police (112)",
        'nearest_hospital': hospitals[0]['poi'] if hospitals else None,
        'nearest_police': police_stations[0]['poi'] if police_stations else None,
        'nearest_embassy': embassies[0]['poi'] if embassies else None
    }

    reply = AISafetyAssistant.answer_query(message, tourist_context)
    return jsonify({'success': True, 'reply': reply})
