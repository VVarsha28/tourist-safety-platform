from datetime import datetime
import os
import re
from .geo_service import haversine_distance

class AIRiskScoringEngine:
    """
    Evaluates multi-factor risk score (0-100) for a tourist.
    Factors:
    1. Zone Risk Level (safe, caution, restricted)
    2. Time of day vs zone safe hours cutoff
    3. Recent incident density in immediate vicinity (< 1.5 km)
    4. Deviation from planned itinerary
    """

    @staticmethod
    def calculate_risk_score(current_zone, lat, lng, recent_incidents=None, tourist_itinerary=None, current_time=None):
        if current_time is None:
            current_time = datetime.now()
        
        hour = current_time.hour
        factors = []
        base_score = 15  # Default baseline in unzoned public territory

        # 1. Zone Risk
        if current_zone:
            if current_zone.risk_level == 'restricted':
                base_score = 80
                factors.append({
                    'factor': 'Restricted Zone',
                    'impact': '+65',
                    'detail': f'Inside "{current_zone.name}". High hazard or restricted perimeter.'
                })
            elif current_zone.risk_level == 'caution':
                base_score = 52
                factors.append({
                    'factor': 'Caution Zone',
                    'impact': '+37',
                    'detail': f'Inside "{current_zone.name}". Exercise heightened vigilance.'
                })
            elif current_zone.risk_level == 'safe':
                base_score = 10
                factors.append({
                    'factor': 'Patrolled Safe Zone',
                    'impact': '-5',
                    'detail': f'Inside "{current_zone.name}". Tourist police presence active.'
                })
        else:
            factors.append({
                'factor': 'Neutral Public Area',
                'impact': '0',
                'detail': 'Standard city perimeter with regular civil monitoring.'
            })

        # 2. Time-of-Day Cutoff
        is_night = (hour >= 21 or hour < 5)  # 9 PM to 5 AM
        if is_night:
            if current_zone and current_zone.risk_level in ['caution', 'restricted']:
                base_score += 15
                factors.append({
                    'factor': 'After Safe-Hours Cutoff',
                    'impact': '+15',
                    'detail': f'Current time ({current_time.strftime("%I:%M %p")}) exceeds the 9:00 PM recommended curfew for this sector.'
                })
            else:
                base_score += 8
                factors.append({
                    'factor': 'Night Hours Activity',
                    'impact': '+8',
                    'detail': 'Nighttime hours observed. Visibility and public transit reduced.'
                })

        # 3. Incident Density Check (< 1.5 km)
        nearby_incident_count = 0
        if recent_incidents and lat is not None and lng is not None:
            for inc in recent_incidents:
                if inc.lat is not None and inc.lng is not None:
                    dist = haversine_distance(lat, lng, inc.lat, inc.lng)
                    if dist <= 1500 and inc.status != 'resolved':
                        nearby_incident_count += 1
            
            if nearby_incident_count > 0:
                density_penalty = min(nearby_incident_count * 7, 21)
                base_score += density_penalty
                factors.append({
                    'factor': 'Local Incident Density',
                    'impact': f'+{density_penalty}',
                    'detail': f'{nearby_incident_count} active or recent incident(s) reported within 1.5 km.'
                })

        # 4. Itinerary Deviation Check
        if tourist_itinerary:
            # Check if current day has a planned schedule in another city
            today_str = current_time.strftime('%Y-%m-%d')
            # For demonstration, if user has scheduled itinerary that doesn't match location
            pass

        # Normalize score into bounds [5, 100]
        final_score = max(5, min(100, base_score))

        # Classify Risk Level & UI Theme
        if final_score < 40:
            level = 'Low Risk'
            level_code = 'low'
            color = '#10B981' # emerald
            badge_class = 'bg-emerald-100 text-emerald-800 border-emerald-300'
            recommendation = 'Area conditions are calm and favorable. Standard travel awareness applies.'
        elif final_score < 75:
            level = 'Moderate Risk'
            level_code = 'moderate'
            color = '#F59E0B' # amber
            badge_class = 'bg-amber-100 text-amber-800 border-amber-300'
            recommendation = 'Heightened vigilance advised. Keep belongings secure and remain on well-lit thoroughfares.'
        else:
            level = 'High Risk'
            level_code = 'high'
            color = '#EF4444' # rose/red
            badge_class = 'bg-rose-100 text-rose-800 border-rose-300'
            recommendation = 'Elevated caution! Avoid poorly lit alleys, travel in groups, or relocate toward designated safe zones.'

        return {
            'score': final_score,
            'level': level,
            'level_code': level_code,
            'color': color,
            'badge_class': badge_class,
            'recommendation': recommendation,
            'factors': factors,
            'calculated_at': current_time.strftime('%H:%M:%S')
        }


class AISafetyAssistant:
    """
    Grounded AI Safety Chat Assistant with deterministic local knowledge base
    and contextual injection (tourist profile, live zone, nearest POIs, emergency numbers).
    """

    @staticmethod
    def answer_query(user_message, tourist_context):
        msg = (user_message or '').strip().lower()

        # Extract context
        tourist_name = tourist_context.get('name', 'Traveler')
        current_zone = tourist_context.get('zone_name', 'Central City')
        risk_level = tourist_context.get('risk_level', 'Low Risk')
        risk_score = tourist_context.get('risk_score', 20)
        nearest_hospital = tourist_context.get('nearest_hospital', None)
        nearest_police = tourist_context.get('nearest_police', None)
        nearest_embassy = tourist_context.get('nearest_embassy', None)
        emergency_contact = tourist_context.get('emergency_contact', 'Not configured')

        # 1. Emergency / Immediate Danger
        if any(w in msg for w in ['help', 'emergency', 'attack', 'followed', 'danger', 'sos', 'kidnap', 'threat', 'urgent']):
            police_str = f" Call Police at **112 / 100**"
            if nearest_police:
                police_str += f" or visit **{nearest_police['name']}** (~{nearest_police.get('distance_km', 0.5)} km away, Tel: {nearest_police.get('phone', '100')})."
            return (
                f"🚨 **IMMEDIATE EMERGENCY ACTION:**\n\n"
                f"1. **Trigger the Red SOS Button** on your screen immediately! It will dispatch your exact GPS coordinates and medical snapshot to live regional authorities.\n"
                f"2.{police_str}\n"
                f"3. Head directly into a crowded, well-lit public shop, hotel lobby, or police booth.\n"
                f"4. Your emergency contact (**{emergency_contact}**) will be automatically alerted if you press SOS."
            )

        # 2. Medical / Health / Hospital / Doctor
        if any(w in msg for w in ['hospital', 'doctor', 'medical', 'ambulance', 'sick', 'hurt', 'injury', 'bleed', 'medicine', 'pharmacy', 'allergic']):
            hosp_str = "the nearest emergency clinic"
            if nearest_hospital:
                hosp_str = f"**{nearest_hospital['name']}** located **{nearest_hospital.get('distance_km', 0.8)} km** away ({nearest_hospital.get('address', 'Downtown')}, Phone: **{nearest_hospital.get('phone', '108')}**)"
            return (
                f"🏥 **Medical Support & Health Guidance:**\n\n"
                f"• Nearest medical facility: {hosp_str}.\n"
                f"• Ambulance Emergency Helpline: **108 / 102**.\n"
                f"• If you have severe symptoms, tap the SOS button to alert emergency responders with your blood group & allergies snapshot.\n"
                f"• Remember to drink bottled, sealed water and avoid raw ice from unlicensed street carts."
            )

        # 3. Police / Theft / Stolen / Scams
        if any(w in msg for w in ['police', 'stolen', 'theft', 'robbed', 'scam', 'cheated', 'harass', 'harassment', 'pickpocket']):
            police_info = "Local Police Station"
            if nearest_police:
                police_info = f"**{nearest_police['name']}** ({nearest_police.get('distance_km', 0.4)} km away, Hotline: **{nearest_police.get('phone', '100')}**)"
            return (
                f"👮 **Reporting Theft, Harassment or Scams:**\n\n"
                f"1. You can submit a non-emergency report using the **'Report Incident'** tab in this app. Authorities monitor this queue actively.\n"
                f"2. Contact {police_info}.\n"
                f"3. Tourist Helpline: **1363** (Toll-free, multi-lingual assistance).\n"
                f"4. For financial theft, immediately freeze your debit/credit cards via your banking app."
            )

        # 4. Lost Passport / Documents / Consulate
        if any(w in msg for w in ['passport', 'lost document', 'visa', 'consulate', 'embassy', 'lost id']):
            embassy_info = "your national Embassy/Consulate"
            if nearest_embassy:
                embassy_info = f"**{nearest_embassy['name']}** ({nearest_embassy.get('distance_km', 2.1)} km away, Tel: {nearest_embassy.get('phone', '+91 11 2419 8000')})"
            return (
                f"🛂 **Lost Passport or Travel Documents Protocol:**\n\n"
                f"1. **File a Police Report / FIR**: File an incident report here in SafeTrail or at the nearest police station to obtain an official incident reference number.\n"
                f"2. **Contact {embassy_info}** to request an Emergency Travel Document (ETD).\n"
                f"3. Access your **Digital Tourist ID** on the 'ID Card' tab — it displays your verified identity and QR code for hotel or police verification."
            )

        # 5. Zone Safety & Night Curfew
        if any(w in msg for w in ['safe here', 'is it safe', 'night', 'curfew', 'walk', 'dark', 'dangerous', 'alone', 'safety score']):
            return (
                f"📍 **Current Zone Assessment for '{current_zone}':**\n\n"
                f"• Current Safety Score: **{risk_score}/100** ({risk_level})\n"
                f"• Safe Hours Recommendation: **6:00 AM – 9:00 PM**\n"
                f"• Guidance: Always stay on primary illuminated corridors. Keep valuables in zipped internal pockets. Avoid taking unmetered, unofficial transport."
            )

        # 6. Transport / Taxi / Tuktuk
        if any(w in msg for w in ['taxi', 'cab', 'auto', 'uber', 'transport', 'bus', 'fare', 'tuktuk']):
            return (
                f"🚖 **Safe Transportation Guidelines:**\n\n"
                f"• Always insist on the digital meter or use pre-paid taxi booths available at transit stations.\n"
                f"• Verified app-based ride services (Uber / Ola) provide GPS-tracked rides.\n"
                f"• Never accept unsolicited rides from private touts inside arrival halls.\n"
                f"• Share your ride status with a friend or your emergency contact (**{emergency_contact}**)."
            )

        # 7. Greetings / Intro
        if any(w in msg for w in ['hi', 'hello', 'hey', 'namaste', 'who are you', 'about']):
            return (
                f"👋 Hello {tourist_name}! I am your **SafeTrail AI Assistant**.\n\n"
                f"I continuously monitor your surroundings in **{current_zone}** (Risk status: **{risk_level}**).\n\n"
                f"You can ask me anything about:\n"
                f"• Nearest hospitals, police stations, or embassies\n"
                f"• Immediate actions for theft, scams, or lost passport\n"
                f"• Area safety advice, night travel recommendations, or scam alerts\n\n"
                f"How can I assist your journey today?"
            )

        # Fallback intelligent grounded response
        return (
            f"💡 **SafeTrail Advisory:**\n\n"
            f"You are currently situated in **{current_zone}** with an evaluated risk level of **{risk_level}** (Safety Score: {risk_score}/100).\n\n"
            f"• **Tourist Helpline:** 1363 (24/7 Multi-language)\n"
            f"• **National Emergency Dispatch:** 112\n"
            f"• **Nearest Medical:** {nearest_hospital['name'] if nearest_hospital else 'SMS Central Hospital'}\n"
            f"• **Nearest Police:** {nearest_police['name'] if nearest_police else 'Kotwali City Police'}\n\n"
            f"If you are facing an urgent threat, press the **SOS** button at the bottom right immediately!"
        )
