from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from functools import wraps
from models import db, User, TouristProfile, Zone, POI, LocationPing, Alert, SOSEvent, Incident
from services.geo_service import find_current_zone
from services.ai_engine import AIRiskScoringEngine

authority_bp = Blueprint('authority', __name__, url_prefix='/authority')

def authority_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authority:
            flash("You need authority administrative credentials to access the command center.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@authority_bp.route('/dashboard')
@authority_required
def dashboard():
    zones = Zone.query.all()
    pois = POI.query.all()
    active_sos_count = SOSEvent.query.filter(SOSEvent.status != 'resolved').count()
    active_tourists_count = User.query.filter_by(role='tourist').count()
    pending_incidents_count = Incident.query.filter(Incident.status != 'resolved').count()

    return render_template(
        'authority/dashboard.html',
        zones=zones,
        pois=pois,
        active_sos_count=active_sos_count,
        active_tourists_count=active_tourists_count,
        pending_incidents_count=pending_incidents_count
    )


# ==================== Telemetry & Command API ====================

@authority_bp.route('/api/telemetry')
@authority_required
def get_telemetry():
    """Live streaming feed of all active tourists, SOS beacons, and system state."""
    zones = Zone.query.all()
    pois = POI.query.all()
    all_incidents = Incident.query.all()

    # Get latest ping for each tourist
    tourists = User.query.filter_by(role='tourist').all()
    tourist_data = []

    for t in tourists:
        latest_ping = LocationPing.query.filter_by(tourist_id=t.id).order_by(LocationPing.timestamp.desc()).first()
        active_sos = SOSEvent.query.filter_by(tourist_id=t.id).filter(SOSEvent.status != 'resolved').first()
        profile = t.profile

        if latest_ping:
            current_zone = find_current_zone(latest_ping.lat, latest_ping.lng, zones)
            risk = AIRiskScoringEngine.calculate_risk_score(current_zone, latest_ping.lat, latest_ping.lng, all_incidents)
            tourist_data.append({
                'id': t.id,
                'name': t.name,
                'digital_id': profile.digital_id_code if profile else 'N/A',
                'nationality': profile.nationality if profile else 'Unknown',
                'lat': latest_ping.lat,
                'lng': latest_ping.lng,
                'timestamp': latest_ping.timestamp.strftime('%H:%M:%S'),
                'zone_name': current_zone.name if current_zone else 'Unzoned Sector',
                'risk_score': risk['score'],
                'risk_level': risk['level'],
                'risk_color': risk['color'],
                'has_active_sos': active_sos is not None,
                'sos_id': active_sos.id if active_sos else None,
                'sos_status': active_sos.status if active_sos else None
            })

    # Active and recent SOS Events
    sos_events = SOSEvent.query.order_by(SOSEvent.timestamp.desc()).limit(15).all()
    sos_data = [s.to_dict() for s in sos_events]

    # Incidents
    incidents = Incident.query.order_by(Incident.timestamp.desc()).all()
    incident_data = [i.to_dict() for i in incidents]

    # Analytics calculation
    incident_type_counts = {}
    for inc in incidents:
        t = inc.type.replace('_', ' ').capitalize()
        incident_type_counts[t] = incident_type_counts.get(t, 0) + 1

    zone_incident_counts = {}
    for inc in incidents:
        if inc.lat and inc.lng:
            z = find_current_zone(inc.lat, inc.lng, zones)
            z_name = z.name if z else 'Unzoned Area'
        else:
            z_name = 'General'
        zone_incident_counts[z_name] = zone_incident_counts.get(z_name, 0) + 1

    return jsonify({
        'tourists': tourist_data,
        'sos_events': sos_data,
        'incidents': incident_data,
        'zones': [z.to_dict() for z in zones],
        'pois': [p.to_dict() for p in pois],
        'analytics': {
            'total_tourists': len(tourists),
            'active_sos': sum(1 for s in sos_data if s['status'] != 'resolved'),
            'incident_types': incident_type_counts,
            'zone_incidents': zone_incident_counts
        }
    })


@authority_bp.route('/api/sos/<int:sos_id>/update-status', methods=['POST'])
@authority_required
def update_sos_status(sos_id):
    sos = SOSEvent.query.get_or_404(sos_id)
    data = request.get_json() or {}
    new_status = data.get('status')
    notes = data.get('notes', '')

    if new_status in ['acknowledged', 'dispatched', 'resolved']:
        sos.status = new_status
        sos.responder_id = current_user.id
        if notes:
            sos.notes = (sos.notes + "\n" if sos.notes else "") + f"[{datetime.utcnow().strftime('%H:%M')}] {current_user.name}: {notes}"
        if new_status == 'resolved':
            sos.resolved_at = datetime.utcnow()
        
        # Create alert for tourist
        status_titles = {
            'acknowledged': "SOS Alert Acknowledged by Command",
            'dispatched': "Emergency Response Unit Dispatched",
            'resolved': "SOS Event Resolved"
        }
        status_msgs = {
            'acknowledged': f"Regional safety officers have received your coordinates and assigned responders.",
            'dispatched': f"Emergency vehicle / tourist police squad is en route to your location. Keep phone active.",
            'resolved': f"This emergency event has been officially logged and marked resolved."
        }
        alert = Alert(
            tourist_id=sos.tourist_id,
            type="sos_update",
            severity="danger" if new_status != 'resolved' else 'info',
            title=status_titles[new_status],
            message=status_msgs[new_status],
            suggested_action="Follow responder instructions." if new_status != 'resolved' else "Stay safe.",
            timestamp=datetime.utcnow()
        )
        db.session.add(alert)
        db.session.commit()

        return jsonify({'success': True, 'sos': sos.to_dict()})
    
    return jsonify({'error': 'Invalid status'}), 400


@authority_bp.route('/api/incident/<int:incident_id>/update-status', methods=['POST'])
@authority_required
def update_incident_status(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    data = request.get_json() or {}
    new_status = data.get('status')
    authority_notes = data.get('authority_notes', '')

    if new_status in ['submitted', 'under_review', 'resolved']:
        incident.status = new_status
        if authority_notes:
            incident.authority_notes = authority_notes
        db.session.commit()
        return jsonify({'success': True, 'incident': incident.to_dict()})
    
    return jsonify({'error': 'Invalid incident status'}), 400


@authority_bp.route('/api/tourist/<int:tourist_id>')
@authority_required
def get_tourist_details(tourist_id):
    tourist = User.query.filter_by(id=tourist_id, role='tourist').first_or_404()
    profile = tourist.profile
    latest_ping = LocationPing.query.filter_by(tourist_id=tourist.id).order_by(LocationPing.timestamp.desc()).first()
    pings = LocationPing.query.filter_by(tourist_id=tourist.id).order_by(LocationPing.timestamp.desc()).limit(20).all()
    
    current_zone = None
    if latest_ping:
        current_zone = find_current_zone(latest_ping.lat, latest_ping.lng, Zone.query.all())

    risk = AIRiskScoringEngine.calculate_risk_score(
        current_zone, 
        latest_ping.lat if latest_ping else None, 
        latest_ping.lng if latest_ping else None,
        Incident.query.all()
    )

    return jsonify({
        'user': tourist.to_dict(),
        'profile': profile.to_dict() if profile else {},
        'current_location': latest_ping.to_dict() if latest_ping else None,
        'location_trail': [p.to_dict() for p in pings],
        'current_zone': current_zone.to_dict() if current_zone else None,
        'risk': risk
    })


@authority_bp.route('/api/lookup')
@authority_required
def lookup_tourist():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'results': []})

    profiles = TouristProfile.query.join(User).filter(
        (TouristProfile.digital_id_code.ilike(f"%{query}%")) |
        (User.name.ilike(f"%{query}%")) |
        (TouristProfile.id_number.ilike(f"%{query}%"))
    ).limit(10).all()

    results = []
    for p in profiles:
        results.append({
            'user_id': p.user_id,
            'name': p.user.name,
            'digital_id': p.digital_id_code,
            'nationality': p.nationality,
            'masked_id': p.masked_id_number,
            'blood_group': p.blood_group,
            'phone': p.user.phone
        })

    return jsonify({'results': results})
