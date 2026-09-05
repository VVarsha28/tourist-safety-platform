from datetime import datetime, date, timedelta
import json
from app import create_app
from models import db, User, TouristProfile, Itinerary, Zone, POI, LocationPing, Alert, SOSEvent, Incident

def seed_database():
    app = create_app()
    with app.app_context():
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()

        print("Seeding Zones...")
        # 1. Safe Zone: City Palace Heritage Corridor
        palace_coords = [
            [26.9280, 75.8210],
            [26.9280, 75.8270],
            [26.9230, 75.8270],
            [26.9230, 75.8210]
        ]
        zone_safe = Zone(
            name="City Palace & Heritage Corridor",
            risk_level="safe",
            boundary_type="polygon",
            coordinates_json=json.dumps(palace_coords),
            description="High-security UNESCO heritage sector with continuous tourist police patrolling, 24/7 CCTV surveillance, and verified tourist assistance booths.",
            safe_hours_start=6,
            safe_hours_end=22,
            center_lat=26.9255,
            center_lng=26.8240,
            radius_meters=450
        )

        # 2. Caution Zone: Johari & Bapu Bazaar Markets
        bazaar_coords = [
            [26.9230, 75.8210],
            [26.9230, 75.8290],
            [26.9170, 75.8290],
            [26.9170, 75.8210]
        ]
        zone_caution = Zone(
            name="Johari & Bapu Bazaar Commercial Sector",
            risk_level="caution",
            boundary_type="polygon",
            coordinates_json=json.dumps(bazaar_coords),
            description="Dense market thoroughfares with frequent unregistered gemstone touts and congestion. Heightened vigilance required after 9:00 PM.",
            safe_hours_start=6,
            safe_hours_end=21,
            center_lat=26.9200,
            center_lng=75.8250,
            radius_meters=600
        )

        # 3. Restricted Zone: Northern Nahargarh Mountain Pass
        mountain_coords = [
            [26.9450, 75.8450],
            [26.9450, 75.8600],
            [26.9350, 75.8600],
            [26.9350, 75.8450]
        ]
        zone_restricted = Zone(
            name="Nahargarh Mountain Pass & Bypass",
            risk_level="restricted",
            boundary_type="polygon",
            coordinates_json=json.dumps(mountain_coords),
            description="Steep mountain hairpin curves with poor lighting, isolated cellular reception, and rocky terrain. Restricted transit after dusk.",
            safe_hours_start=7,
            safe_hours_end=18,
            center_lat=26.9400,
            center_lng=75.8520,
            radius_meters=900
        )

        db.session.add_all([zone_safe, zone_caution, zone_restricted])
        db.session.commit()

        print("Seeding POIs (Hospitals, Police, Embassies)...")
        pois = [
            POI(
                name="SMS Government Super-Specialty Hospital",
                type="hospital",
                lat=26.8972,
                lng=75.8164,
                phone="+91 141 2518200",
                address="JLN Marg, Ashok Nagar, Jaipur"
            ),
            POI(
                name="Kotwali Central Police & Tourist Safety HQ",
                type="police",
                lat=26.9248,
                lng=75.8239,
                phone="+91 141 2603515",
                address="Near Badi Chaupar, Old City, Jaipur"
            ),
            POI(
                name="Tourist Police Help Desk (Hawa Mahal)",
                type="police",
                lat=26.9239,
                lng=75.8267,
                phone="1363",
                address="Hawa Mahal Rd, Badi Choupad"
            ),
            POI(
                name="Santokba Durlabhji Memorial Hospital",
                type="hospital",
                lat=26.8890,
                lng=75.8080,
                phone="+91 141 2566251",
                address="Bhawani Singh Rd, Jaipur"
            ),
            POI(
                name="International Travelers Consular Liaison",
                type="embassy",
                lat=26.9050,
                lng=75.7950,
                phone="+91 11 2419 8000",
                address="Civil Lines VIP Enclave, Jaipur"
            )
        ]
        db.session.add_all(pois)
        db.session.commit()

        print("Seeding Users & Profiles...")
        # 1. Authority User
        authority_user = User(
            name="Commander Vikram Singh",
            email="authority@safetrail.gov",
            role="authority",
            phone="+91 141 2200112"
        )
        authority_user.set_password("admin123")
        db.session.add(authority_user)

        # 2. Tourist Elena Rostova (In Caution Zone)
        tourist_elena = User(
            name="Elena Rostova",
            email="elena@demo.com",
            role="tourist",
            phone="+34 654 998 123"
        )
        tourist_elena.set_password("tourist123")
        db.session.add(tourist_elena)
        db.session.flush()

        profile_elena = TouristProfile(
            user_id=tourist_elena.id,
            nationality="Spain",
            id_number="ESP-88294109",
            blood_group="O+",
            allergies="Penicillin, Peanuts",
            medical_conditions="Mild Asthma (carries inhaler)",
            emergency_contact_name="Marco Rostova",
            emergency_contact_phone="+34 612 345 678",
            emergency_contact_relation="Brother",
            photo_url="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&h=150&fit=crop&crop=face",
            trip_start=date.today() - timedelta(days=2),
            trip_end=date.today() + timedelta(days=5),
            accommodation_address="Haveli Heritage Resort, Room 204, Amber Road",
            digital_id_code="ST-2026-ESP-4109"
        )
        db.session.add(profile_elena)

        # 3. Tourist Carlos Mendez (Active SOS)
        tourist_carlos = User(
            name="Carlos Mendez",
            email="carlos@demo.com",
            role="tourist",
            phone="+52 55 8920 1199"
        )
        tourist_carlos.set_password("tourist123")
        db.session.add(tourist_carlos)
        db.session.flush()

        profile_carlos = TouristProfile(
            user_id=tourist_carlos.id,
            nationality="Mexico",
            id_number="MEX-77102934",
            blood_group="A-",
            allergies="Bee stings, Aspirin",
            medical_conditions="Hypoglycemia",
            emergency_contact_name="Sofia Mendez",
            emergency_contact_phone="+52 55 1234 5678",
            emergency_contact_relation="Spouse",
            photo_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face",
            trip_start=date.today() - timedelta(days=1),
            trip_end=date.today() + timedelta(days=7),
            accommodation_address="Jaipur Marriott Hotel, Ashram Marg",
            digital_id_code="ST-2026-MEX-2934"
        )
        db.session.add(profile_carlos)

        # 4. Tourist Aarav Sharma (Safe Zone)
        tourist_aarav = User(
            name="Aarav Sharma",
            email="aarav@demo.com",
            role="tourist",
            phone="+1 416 780 9102"
        )
        tourist_aarav.set_password("tourist123")
        db.session.add(tourist_aarav)
        db.session.flush()

        profile_aarav = TouristProfile(
            user_id=tourist_aarav.id,
            nationality="Canada",
            id_number="CAN-90218844",
            blood_group="B+",
            allergies="None reported",
            medical_conditions="None",
            emergency_contact_name="Rohan Sharma",
            emergency_contact_phone="+1 416 555 0192",
            emergency_contact_relation="Father",
            photo_url="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&h=150&fit=crop&crop=face",
            trip_start=date.today() - timedelta(days=3),
            trip_end=date.today() + timedelta(days=4),
            accommodation_address="ITC Rajputana Luxury Collection, Station Road",
            digital_id_code="ST-2026-CAN-8844"
        )
        db.session.add(profile_aarav)
        db.session.commit()

        print("Seeding Location Pings & Alerts...")
        # Elena's location (Caution Zone)
        ping_elena = LocationPing(
            tourist_id=tourist_elena.id,
            lat=26.9205,
            lng=75.8245,
            accuracy=12.0,
            timestamp=datetime.utcnow() - timedelta(minutes=3)
        )
        alert_elena = Alert(
            tourist_id=tourist_elena.id,
            type="zone_alert",
            severity="caution",
            title="Caution Zone Entered: Johari Bazaar",
            message="You have entered Johari & Bapu Bazaar Commercial Sector. Keep your purse and phone securely zipped. Beware of unsolicited gem deals.",
            suggested_action="Stick to illuminated streets and avoid secluded alleyways after 9:00 PM.",
            timestamp=datetime.utcnow() - timedelta(minutes=2)
        )

        # Carlos location (Restricted Zone + Active SOS)
        ping_carlos = LocationPing(
            tourist_id=tourist_carlos.id,
            lat=26.9405,
            lng=75.8510,
            accuracy=8.0,
            timestamp=datetime.utcnow() - timedelta(minutes=5)
        )
        sos_carlos = SOSEvent(
            tourist_id=tourist_carlos.id,
            lat=26.9405,
            lng=75.8510,
            timestamp=datetime.utcnow() - timedelta(minutes=4),
            status="active",
            notes="Active SOS beacon dispatched. High elevation detected.",
            voice_note_text="Twisted my ankle on the steep descent near Nahargarh pass. Battery at 11%, need immediate assistance."
        )

        # Aarav location (Safe Zone)
        ping_aarav = LocationPing(
            tourist_id=tourist_aarav.id,
            lat=26.9255,
            lng=75.8240,
            accuracy=5.0,
            timestamp=datetime.utcnow() - timedelta(minutes=1)
        )

        db.session.add_all([ping_elena, alert_elena, ping_carlos, sos_carlos, ping_aarav])
        db.session.commit()

        print("Seeding Incidents...")
        incidents = [
            Incident(
                tourist_id=tourist_elena.id,
                type="theft",
                title="Snatched Handbag near City Palace Gate",
                description="Motorbike rider snatched tourist shoulder bag near outer palace gate. Contained hotel keys and glasses.",
                lat=26.9260,
                lng=75.8220,
                address="City Palace Outer Gate 2, Jantar Mantar Lane",
                photo_url=None,
                anonymous=False,
                status="resolved",
                authority_notes="Patrol Unit 4 intercepted motorbike at Tripoliya Gate; bag recovered and returned to owner.",
                timestamp=datetime.utcnow() - timedelta(hours=6)
            ),
            Incident(
                tourist_id=tourist_carlos.id,
                type="scam",
                title="Fake Tour Guide Touting Unofficial Tickets",
                description="Individual claiming to be government heritage officer attempted to sell fake combo passes for 2,000 INR.",
                lat=26.9235,
                lng=75.8270,
                address="Badi Chaupar Crossing, Hawa Mahal Entrance",
                photo_url=None,
                anonymous=False,
                status="under_review",
                authority_notes="CCTV footage dispatched to Kotwali Tourist Police unit for identification.",
                timestamp=datetime.utcnow() - timedelta(hours=2)
            ),
            Incident(
                tourist_id=None,
                type="hazard",
                title="Damaged Pedestrian Pavement & Open Cable Trench",
                description="Deep unbarricaded trench with exposed wire next to pedestrian crosswalk. Tripping hazard in low light.",
                lat=26.9180,
                lng=75.8230,
                address="Johari Bazaar South End",
                photo_url=None,
                anonymous=True,
                status="submitted",
                authority_notes="",
                timestamp=datetime.utcnow() - timedelta(minutes=45)
            )
        ]
        db.session.add_all(incidents)
        db.session.commit()

        print("Database seeded successfully with realistic demo data!")

if __name__ == '__main__':
    seed_database()
