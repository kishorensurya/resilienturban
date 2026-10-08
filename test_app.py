"""
ResilientUrban - Comprehensive End-to-End Test Suite
Tests all endpoints, simulations, ML predictions, routing, reports, SOS triage, and logins.
"""

import unittest
import json
from app import app

class ResilientUrbanTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_pages(self):
        # Index page
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"RESILIENTURBAN", res.data)
        self.assertIn(b"8431535534", res.data)
        self.assertIn(b"civora@gmail.com", res.data)

        # Login page
        res_login = self.client.get('/login')
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"ACCESS PORTAL", res_login.data)
        self.assertIn(b"8431535534", res_login.data)

    def test_login_api(self):
        # Admin login
        res = self.client.post('/api/login', json={'username': 'admin', 'password': 'admin123', 'role': 'ADMIN'})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'SUCCESS')

        # Citizen login
        res2 = self.client.post('/api/login', json={'username': 'citizen', 'password': 'citizen123', 'role': 'CITIZEN'})
        self.assertEqual(res2.status_code, 200)

    def test_register_api(self):
        import random
        rnd = random.randint(1000, 9999)
        res = self.client.post('/api/register', json={
            'full_name': f'Citizen Test {rnd}',
            'username': f'user_{rnd}',
            'email': f'user_{rnd}@gmail.com',
            'phone': '9845012345',
            'password': 'password123',
            'role': 'CITIZEN'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'SUCCESS')

    def test_dashboard_api(self):
        res = self.client.get('/api/dashboard')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['hazard'], 'urban_flood')
        self.assertIn('kpis', data)
        self.assertIn('zones', data)
        self.assertIn('roads', data)

    def test_routing_and_blockage(self):
        # Unblocked route
        self.client.post('/api/roads/block', json={'road_id': 'R-MAIN', 'blocked': False, 'flood_depth_cm': 0.0})
        res = self.client.get('/api/route')
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'SUCCESS')
        self.assertIn('80 Feet Road', data['roads_used'][0])

        # Block Main Road (75 cm flood depth)
        self.client.post('/api/roads/block', json={'road_id': 'R-MAIN', 'blocked': True, 'flood_depth_cm': 75.0})
        res_alt = self.client.get('/api/route')
        data_alt = json.loads(res_alt.data)
        self.assertEqual(data_alt['status'], 'SUCCESS')
        self.assertFalse(any('80 Feet Road' in r for r in data_alt['roads_used']))
        self.assertIn('Hosur Arterial Road', data_alt['roads_used'][0])

    def test_citizen_report_with_confidence(self):
        res = self.client.post('/api/reports', json={
            'type': 'Waterlogging',
            'description': 'Water rising to curb near 4th cross',
            'ward': 'Ward 12',
            'evidence': True
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('REP-', data['report_code'])
        self.assertGreaterEqual(data['confidence'], 40.0)

    def test_sos_request_triage(self):
        res = self.client.post('/api/help-requests', json={
            'type': 'Serious injury',
            'num_people': 1,
            'description': 'Severe leg fracture near culvert water surge',
            'ward': 'Ward 12'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['priority'], 'CRITICAL')
        self.assertIn('#', data['request_code'])

    def test_resource_matching(self):
        res = self.client.post('/api/match-resource', json={
            'type': 'Serious injury',
            'latitude': 12.9352,
            'longitude': 77.6245
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        best = data['best_match']
        self.assertEqual(best['resource']['resource_id'], 'A-07')
        self.assertGreaterEqual(best['match_score'], 80.0)

    def test_simulation_workflow(self):
        # Step through critical simulation steps
        self.client.post('/api/simulation/reset')
        
        # Step 1
        s1 = self.client.post('/api/simulation/step', json={'step': 1})
        self.assertEqual(s1.status_code, 200)
        
        # Step 7 (Main Road blocked)
        s7 = self.client.post('/api/simulation/step', json={'step': 7})
        self.assertEqual(s7.status_code, 200)
        d7 = json.loads(s7.data)
        self.assertEqual(d7['status']['main_road']['blocked'], 1)
        
        # Step 12 (A-07 matched)
        s12 = self.client.post('/api/simulation/step', json={'step': 12})
        self.assertEqual(s12.status_code, 200)
        d12 = json.loads(s12.data)
        self.assertEqual(d12['status']['help_request']['assigned_resource'], 'Medical Response Unit A-07')

        # Step 18 (Resolved)
        s18 = self.client.post('/api/simulation/step', json={'step': 18})
        self.assertEqual(s18.status_code, 200)
        d18 = json.loads(s18.data)
        self.assertEqual(d18['status']['help_request']['status'], 'RESOLVED')

        # Reset back to clean baseline
        self.client.post('/api/simulation/reset')

    def test_live_weather(self):
        res = self.client.get('/api/weather/live?lat=12.9352&lon=77.6245')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('rain_mm_hr', data)

        res_sync = self.client.post('/api/weather/sync', json={'city': 'Bengaluru (Koramangala/HSR)'})
        self.assertEqual(res_sync.status_code, 200)
        d_sync = json.loads(res_sync.data)
        self.assertEqual(d_sync['status'], 'SYNCED')

    def test_citizen_and_receipt_and_apk(self):
        # 1. Citizen Portal
        res_cit = self.client.get('/citizen')
        self.assertEqual(res_cit.status_code, 200)
        self.assertIn(b"Citizen Flood Safety", res_cit.data)
        self.assertIn(b"TRIGGER RESCUE SOS", res_cit.data)
        self.assertIn(b"8431535534", res_cit.data)

        # 2. Admin Portal
        res_admin = self.client.get('/admin')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"MUNICIPAL COMMAND HUD", res_admin.data)

        # 3. Printable Receipt Page
        res_receipt = self.client.get('/receipt/1027')
        self.assertEqual(res_receipt.status_code, 200)
        self.assertIn(b"Official Citizen Rescue Acknowledgment", res_receipt.data)
        self.assertIn(b"St. John", res_receipt.data)
        self.assertIn(b"8431535534", res_receipt.data)

        res_receipt2 = self.client.get('/receipt/ACK-2026-X884')
        self.assertEqual(res_receipt2.status_code, 200)
        self.assertIn(b"ACK-2026-X884", res_receipt2.data)

        # 4. APK Download
        res_apk = self.client.get('/download/resilient-urban.apk')
        self.assertEqual(res_apk.status_code, 200)
        self.assertEqual(res_apk.mimetype, 'application/vnd.android.package-archive')
        self.assertGreater(len(res_apk.data), 1000)

        # 5. Manifest.json
        res_manifest = self.client.get('/manifest.json')
        self.assertEqual(res_manifest.status_code, 200)
        m_data = json.loads(res_manifest.data)
        self.assertEqual(m_data['short_name'], 'ResilientUrban')

    def test_sos_telephony_and_receipt_trigger(self):
        res = self.client.post('/api/sos/trigger', json={
            'name': 'Ramesh Kumar',
            'phone': '9845012345',
            'family_name': 'Sunita Kumar',
            'family_phone': '8431535534',
            'type': 'Serious injury',
            'landmark': 'Koramangala 4th block low basin',
            'latitude': 12.9352,
            'longitude': 77.6245
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'SUCCESS')
        self.assertIn('receipt', data)
        self.assertIn('sms', data)
        self.assertIn('call_script', data)
        self.assertIn('ACK-', data['receipt']['ack_code'])
        self.assertEqual(data['receipt']['responder_phone'], '8431535534')

        # Check in acknowledgments feed API
        res_acks = self.client.get('/api/acknowledgments')
        self.assertEqual(res_acks.status_code, 200)
        acks_data = json.loads(res_acks.data)
        self.assertGreaterEqual(len(acks_data['acknowledgments']), 1)

        # Check in comms feed API
        res_comms = self.client.get('/api/comms/logs')
        self.assertEqual(res_comms.status_code, 200)
        comms_data = json.loads(res_comms.data)
        self.assertGreaterEqual(len(comms_data['logs']), 1)

    def test_randomized_stress_test_simulation(self):
        res = self.client.post('/api/simulation/randomize', json={
            'rainfall_mm_hr': 140.0,
            'water_level_cm': 125.0,
            'drainage_stress_percent': 95.0
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'RANDOMIZED_CALCULATION_COMPLETE')
        self.assertTrue(data['road_status']['main_road_blocked'])
        self.assertIn('calculated_risk', data)
        self.assertIn('dijkstra_reroute', data)

if __name__ == '__main__':
    unittest.main()
