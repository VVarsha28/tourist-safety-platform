from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, default='tourist')  # 'tourist' or 'authority'
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    profile = db.relationship('TouristProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    location_pings = db.relationship('LocationPing', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sos_events = db.relationship('SOSEvent', backref='user', lazy='dynamic', foreign_keys='SOSEvent.tourist_id', cascade='all, delete-orphan')
    incidents = db.relationship('Incident', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_authority(self):
        return self.role == 'authority'

    @property
    def is_tourist(self):
        return self.role == 'tourist'

    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'name': self.name,
            'email': self.email,
            'phone': self.phone
        }


class TouristProfile(db.Model):
    __tablename__ = 'tourist_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    nationality = db.Column(db.String(60), default='Unknown')
    id_number = db.Column(db.String(60), default='')  # Passport / National ID
    blood_group = db.Column(db.String(10), default='Unknown')
    allergies = db.Column(db.String(255), default='None reported')
    medical_conditions = db.Column(db.String(255), default='None reported')
    emergency_contact_name = db.Column(db.String(100), default='')
    emergency_contact_phone = db.Column(db.String(30), default='')
    emergency_contact_relation = db.Column(db.String(50), default='Emergency Contact')
    photo_url = db.Column(db.String(255), default='/static/img/default-avatar.png')
    trip_start = db.Column(db.Date, nullable=True)
    trip_end = db.Column(db.Date, nullable=True)
    accommodation_address = db.Column(db.String(255), default='')
    digital_id_code = db.Column(db.String(40), unique=True, index=True)

    itineraries = db.relationship('Itinerary', backref='profile', cascade='all, delete-orphan')

    @property
    def masked_id_number(self):
        if not self.id_number:
            return 'N/A'
        val = str(self.id_number).strip()
        if len(val) <= 4:
            return '****'
        return '*' * (len(val) - 4) + val[-4:]

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.user.name if self.user else '',
            'nationality': self.nationality,
            'masked_id_number': self.masked_id_number,
            'blood_group': self.blood_group,
            'allergies': self.allergies,
            'medical_conditions': self.medical_conditions,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone,
            'emergency_contact_relation': self.emergency_contact_relation,
            'photo_url': self.photo_url,
            'trip_start': self.trip_start.strftime('%Y-%m-%d') if self.trip_start else None,
            'trip_end': self.trip_end.strftime('%Y-%m-%d') if self.trip_end else None,
            'accommodation_address': self.accommodation_address,
            'digital_id_code': self.digital_id_code
        }


class Itinerary(db.Model):
    __tablename__ = 'itineraries'

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('tourist_profiles.id'), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    planned_date = db.Column(db.Date, nullable=False)
    accommodation = db.Column(db.String(200), default='')

    def to_dict(self):
        return {
            'id': self.id,
            'city': self.city,
            'planned_date': self.planned_date.strftime('%Y-%m-%d') if self.planned_date else '',
            'accommodation': self.accommodation
        }


class Zone(db.Model):
    __tablename__ = 'zones'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)  # 'safe', 'caution', 'restricted'
    boundary_type = db.Column(db.String(20), default='polygon')  # 'polygon' or 'circle'
    coordinates_json = db.Column(db.Text, nullable=False)  # JSON string
    description = db.Column(db.Text, default='')
    safe_hours_start = db.Column(db.Integer, default=6)   # 6 AM
    safe_hours_end = db.Column(db.Integer, default=21)    # 9 PM (21:00)
    center_lat = db.Column(db.Float, nullable=True)
    center_lng = db.Column(db.Float, nullable=True)
    radius_meters = db.Column(db.Float, nullable=True)

    def get_coordinates(self):
        try:
            return json.loads(self.coordinates_json)
        except Exception:
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'risk_level': self.risk_level,
            'boundary_type': self.boundary_type,
            'coordinates': self.get_coordinates(),
            'description': self.description,
            'safe_hours_start': self.safe_hours_start,
            'safe_hours_end': self.safe_hours_end,
            'center_lat': self.center_lat,
            'center_lng': self.center_lng,
            'radius_meters': self.radius_meters
        }


class POI(db.Model):
    __tablename__ = 'pois'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(30), nullable=False)  # 'police', 'hospital', 'embassy', 'helpline'
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(40), default='')
    address = db.Column(db.String(255), default='')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'lat': self.lat,
            'lng': self.lng,
            'phone': self.phone,
            'address': self.address
        }


class LocationPing(db.Model):
    __tablename__ = 'location_pings'

    id = db.Column(db.Integer, primary_key=True)
    tourist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    accuracy = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tourist_id': self.tourist_id,
            'lat': self.lat,
            'lng': self.lng,
            'timestamp': self.timestamp.isoformat()
        }


class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    tourist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(50), default='zone_alert')  # 'zone_alert', 'night_curfew', 'weather', 'itinerary_deviation'
    severity = db.Column(db.String(20), default='caution')  # 'info', 'caution', 'danger'
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    suggested_action = db.Column(db.Text, default='')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    dismissed = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tourist_id': self.tourist_id,
            'tourist_name': self.user.name if self.user else 'Unknown',
            'type': self.type,
            'severity': self.severity,
            'title': self.title,
            'message': self.message,
            'suggested_action': self.suggested_action,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'dismissed': self.dismissed
        }


class SOSEvent(db.Model):
    __tablename__ = 'sos_events'

    id = db.Column(db.Integer, primary_key=True)
    tourist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(20), default='active', index=True)  # 'active', 'acknowledged', 'dispatched', 'resolved'
    notes = db.Column(db.Text, default='')
    voice_note_text = db.Column(db.Text, default='')
    resolved_at = db.Column(db.DateTime, nullable=True)
    responder_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    responder = db.relationship('User', foreign_keys=[responder_id])

    def to_dict(self):
        profile = self.user.profile if self.user else None
        return {
            'id': self.id,
            'tourist_id': self.tourist_id,
            'tourist_name': self.user.name if self.user else 'Unknown',
            'tourist_phone': self.user.phone if self.user else '',
            'nationality': profile.nationality if profile else 'Unknown',
            'blood_group': profile.blood_group if profile else 'Unknown',
            'allergies': profile.allergies if profile else 'None',
            'medical_conditions': profile.medical_conditions if profile else 'None',
            'emergency_contact_name': profile.emergency_contact_name if profile else '',
            'emergency_contact_phone': profile.emergency_contact_phone if profile else '',
            'emergency_contact_relation': profile.emergency_contact_relation if profile else '',
            'digital_id_code': profile.digital_id_code if profile else '',
            'photo_url': profile.photo_url if profile else '',
            'lat': self.lat,
            'lng': self.lng,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'notes': self.notes,
            'voice_note_text': self.voice_note_text,
            'resolved_at': self.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if self.resolved_at else None,
            'responder_name': self.responder.name if self.responder else None
        }


class Incident(db.Model):
    __tablename__ = 'incidents'

    id = db.Column(db.Integer, primary_key=True)
    tourist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    type = db.Column(db.String(40), nullable=False)  # 'theft', 'harassment', 'scam', 'lost_item', 'hazard', 'other'
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    address = db.Column(db.String(255), default='')
    photo_url = db.Column(db.String(255), nullable=True)
    anonymous = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='submitted', index=True)  # 'submitted', 'under_review', 'resolved'
    authority_notes = db.Column(db.Text, default='')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tourist_id': None if self.anonymous else self.tourist_id,
            'reporter_name': 'Anonymous' if self.anonymous else (self.user.name if self.user else 'Guest'),
            'reporter_phone': 'Hidden' if self.anonymous else (self.user.phone if self.user else ''),
            'type': self.type,
            'title': self.title,
            'description': self.description,
            'lat': self.lat,
            'lng': self.lng,
            'address': self.address,
            'photo_url': self.photo_url,
            'anonymous': self.anonymous,
            'status': self.status,
            'authority_notes': self.authority_notes,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
