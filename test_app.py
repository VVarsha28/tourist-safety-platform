import unittest
from app import create_app
from models import db, User, TouristProfile, SOSEvent, Incident, Alert, Zone

class SafeTrailTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_public_and_login_page(self):
        """Test public index and login pages."""
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'SafeTrail Portal', res.data)
        self.assertIn(b'Fast Demo Profiles', res.data)

    def test_02_demo_login_authority(self):
        """Test one-click demo login for Authority Command."""
        res = self.client.get('/demo-login/authority', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Jaipur Regional Safety Operations Center', res.data)

    def test_03_authority_telemetry_api(self):
        """Test authority telemetry API returns tourists, SOS, and zones."""
        self.client.get('/demo-login/authority')
        res = self.client.get('/authority/api/telemetry')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('tourists', data)
        self.assertIn('sos_events', data)
        self.assertIn('zones', data)
        self.assertIn('analytics', data)
        self.assertGreater(len(data['tourists']), 0)
        self.assertGreater(len(data['zones']), 0)

    def test_04_tourist_home_and_ai_score(self):
        """Test tourist dashboard and AI risk score computation."""
        res = self.client.get('/demo-login/elena', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Elena Rostova', res.data)
        self.assertIn(b'Safety Score', res.data)

    def test_05_location_ping_and_zone_alert(self):
        """Test location ping triggering zone entry and live risk evaluation."""
        self.client.get('/demo-login/elena')
        res = self.client.post('/tourist/api/location/ping', json={
            'lat': 26.9205,
            'lng': 75.8245
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIsNotNone(data['current_zone'])
        self.assertEqual(data['current_zone']['risk_level'], 'caution')
        self.assertGreaterEqual(data['risk']['score'], 40)

    def test_06_ai_chat_assistant(self):
        """Test AI Safety Assistant contextual answers."""
        self.client.get('/demo-login/elena')
        res = self.client.post('/tourist/api/ai/chat', json={
            'message': 'Where is the nearest hospital?'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('hospital', data['reply'].lower())

        res2 = self.client.post('/tourist/api/ai/chat', json={
            'message': 'What should I do if I lose my passport?'
        })
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertIn('passport', data2['reply'].lower())

    def test_07_digital_id_and_public_qr_verification(self):
        """Test Digital ID page and public QR verification endpoint."""
        self.client.get('/demo-login/elena')
        res = self.client.get('/tourist/digital-id')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'DIGITAL TOURIST ID', res.data)
        self.assertIn(b'ST-2026-ESP-4109', res.data)

        # Public verification page (no auth needed)
        self.client.get('/logout')
        res_verify = self.client.get('/verify/ST-2026-ESP-4109')
        self.assertEqual(res_verify.status_code, 200)
        self.assertIn(b'SafeTrail Verified Tourist', res_verify.data)
        self.assertIn(b'Elena Rostova', res_verify.data)
        self.assertIn(b'****4109', res_verify.data)

    def test_08_sos_lifecycle(self):
        """Test SOS triggering and Authority response workflow."""
        self.client.get('/demo-login/elena')
        res_trigger = self.client.post('/tourist/api/sos/trigger', json={
            'lat': 26.9215,
            'lng': 75.8250,
            'voice_note_text': 'Need medical assistance at Johari Market'
        })
        self.assertEqual(res_trigger.status_code, 200)
        sos_id = res_trigger.get_json()['sos_id']

        # Authority acknowledges
        self.client.get('/demo-login/authority')
        res_ack = self.client.post(f'/authority/api/sos/{sos_id}/update-status', json={
            'status': 'acknowledged',
            'notes': 'Unit 2 alerted'
        })
        self.assertEqual(res_ack.status_code, 200)
        self.assertEqual(res_ack.get_json()['sos']['status'], 'acknowledged')

        # Authority dispatches
        res_disp = self.client.post(f'/authority/api/sos/{sos_id}/update-status', json={
            'status': 'dispatched',
            'notes': 'Patrol vehicle en route'
        })
        self.assertEqual(res_disp.status_code, 200)
        self.assertEqual(res_disp.get_json()['sos']['status'], 'dispatched')

        # Authority resolves
        res_res = self.client.post(f'/authority/api/sos/{sos_id}/update-status', json={
            'status': 'resolved',
            'notes': 'Tourist safely reached'
        })
        self.assertEqual(res_res.status_code, 200)
        self.assertEqual(res_res.get_json()['sos']['status'], 'resolved')

if __name__ == '__main__':
    unittest.main()
