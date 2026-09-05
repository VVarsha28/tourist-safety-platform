from flask import Blueprint, render_template, abort
from datetime import date
from models import TouristProfile, LocationPing, Zone
from services.geo_service import find_current_zone
from services.ai_engine import AIRiskScoringEngine

public_bp = Blueprint('public', __name__)

@public_bp.route('/verify/<digital_id_code>')
def verify_id(digital_id_code):
    profile = TouristProfile.query.filter_by(digital_id_code=digital_id_code).first_or_404()

    # Check validity
    today = date.today()
    is_valid = True
    if profile.trip_start and profile.trip_end:
        is_valid = (profile.trip_start <= today <= profile.trip_end)
    elif profile.trip_end:
        is_valid = (today <= profile.trip_end)

    # Fetch latest risk status
    latest_ping = LocationPing.query.filter_by(tourist_id=profile.user_id).order_by(LocationPing.timestamp.desc()).first()
    lat = latest_ping.lat if latest_ping else None
    lng = latest_ping.lng if latest_ping else None
    current_zone = None
    if lat and lng:
        current_zone = find_current_zone(lat, lng, Zone.query.all())

    risk = AIRiskScoringEngine.calculate_risk_score(current_zone, lat, lng)

    return render_template(
        'verify.html',
        profile=profile,
        is_valid=is_valid,
        current_zone=current_zone,
        risk=risk,
        verified_date=today.strftime('%B %d, %Y')
    )
