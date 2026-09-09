"""
Automated Test Suite for IELTS Master Hub.
Verifies database integrity, route availability, API endpoints, and user authentication.
"""

import unittest
import json
import uuid
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
from database import init_db, get_dashboard_summary

class IELTSAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        init_db()

    def test_routes_status_200(self):
        routes = [
            '/',
            '/reading',
            '/listening',
            '/writing',
            '/speaking',
            '/vocabulary',
            '/grammar',
            '/calculator',
            '/history',
            '/login',
            '/register'
        ]
        for r in routes:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 200, f"Route {r} failed with status {res.status_code}")

    def test_user_registration_and_login_flow(self):
        unique_name = f"user_{uuid.uuid4().hex[:6]}"
        unique_email = f"{unique_name}@test.com"

        # 1. Registration Success
        res = self.client.post('/register', data={
            'username': unique_name,
            'email': unique_email,
            'password': 'password123',
            'confirm_password': 'password123',
            'target_band': '8.0'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(unique_name.encode(), res.data)

        # 2. Duplicate Registration Rejection (after logout)
        self.client.get('/logout')
        dup_res = self.client.post('/register', data={
            'username': unique_name,
            'email': f"another_{unique_email}",
            'password': 'password123',
            'confirm_password': 'password123',
            'target_band': '8.0'
        })
        self.assertEqual(dup_res.status_code, 200)
        self.assertIn('đã được sử dụng'.encode(), dup_res.data)

        # 3. Password Mismatch Rejection
        mismatch_res = self.client.post('/register', data={
            'username': f"diff_{unique_name}",
            'email': f"diff_{unique_email}",
            'password': 'password123',
            'confirm_password': 'different_password',
            'target_band': '7.0'
        })
        self.assertEqual(mismatch_res.status_code, 200)
        self.assertIn('không trùng khớp'.encode(), mismatch_res.data)

        # 4. Logout
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b'Log in', logout_res.data)

        # 5. Login Failure with wrong password
        fail_login = self.client.post('/login', data={
            'identifier': unique_name,
            'password': 'wrong_password'
        })
        self.assertEqual(fail_login.status_code, 200)
        self.assertIn('không chính xác'.encode(), fail_login.data)

        # 6. Login Success with Username
        success_login = self.client.post('/login', data={
            'identifier': unique_name,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(success_login.status_code, 200)
        self.assertIn(unique_name.encode(), success_login.data)

        # 7. Login Success with Email
        self.client.get('/logout')
        email_login = self.client.post('/login', data={
            'identifier': unique_email,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(email_login.status_code, 200)
        self.assertIn(unique_name.encode(), email_login.data)

    def test_calculator_api(self):
        payload = {
            "listening_raw": 35,
            "reading_raw": 33,
            "reading_type": "academic",
            "writing_band": 7.0,
            "speaking_band": 7.5
        }
        res = self.client.post('/api/calculator/calculate', json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['listening_band'], 8.0)
        self.assertEqual(data['reading_band'], 7.5)
        # Average: (8.0 + 7.5 + 7.0 + 7.5) / 4 = 7.5
        self.assertEqual(data['overall_band'], 7.5)

    def test_reading_grading_api(self):
        payload = {
            "test_id": "read-01",
            "answers": {
                "q1": "FALSE",
                "q2": "TRUE",
                "q4": "The pervasive surveillance of citizens' daily activities",
                "q5": "power grid"
            },
            "time_spent": 120
        }
        res = self.client.post('/api/tests/reading/grade', json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('score', data)
        self.assertIn('band_score', data)
        self.assertGreaterEqual(data['score'], 4)

    def test_writing_evaluation_api(self):
        sample_essay = (
            "In recent decades, environmental degradation has emerged as an unprecedented global crisis. "
            "Governments must enforce stringent environmental policies to mitigate carbon emissions. "
            "Furthermore, individual citizens also bear significant responsibility for conservation. "
            "In conclusion, collaborative efforts are paramount to sustainable progress."
        )
        payload = {
            "prompt_id": "write-t2-01",
            "prompt_title": "AI and Teachers",
            "task_type": "task2",
            "essay_text": sample_essay
        }
        res = self.client.post('/api/writing/evaluate', json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('evaluation', data)
        self.assertIn('overall_band', data['evaluation'])

    def test_vocabulary_toggle(self):
        res = self.client.post('/api/vocabulary/toggle-mastery', json={"word_id": "v01"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('is_mastered', data)

    def test_vocabulary_online_lookup_api(self):
        # 1. Look up 'deserve'
        res = self.client.get('/api/vocabulary/deserve')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        vocab = data.get('data', {})
        self.assertEqual(vocab.get('word'), 'deserve')
        self.assertTrue(bool(vocab.get('meaning_vi')))
        self.assertTrue(bool(vocab.get('audio')))
        self.assertTrue(bool(vocab.get('ielts_example')))
        self.assertTrue(bool(vocab.get('band')))

        # 2. Second lookup should hit cache
        res2 = self.client.get('/api/vocabulary/deserve')
        self.assertEqual(res2.status_code, 200)
        vocab2 = res2.get_json().get('data', {})
        self.assertTrue(vocab2.get('cached'))

    def test_vocabulary_topics_and_categories(self):
        # 1. Test GET /vocabulary page
        res = self.client.get('/vocabulary')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Chủ đề', html)
        self.assertIn('11 bộ', html)
        self.assertIn('Environment & Climate Change', html)
        self.assertIn('Technology, AI & The Digital Era', html)

        # 2. Test topic words query
        curated_words = ['mitigate', 'algorithmic', 'pedagogical', 'deterrent']
        for w in curated_words:
            lookup = self.client.get(f'/api/vocabulary/{w}')
            self.assertEqual(lookup.status_code, 200)
            data = lookup.get_json().get('data', {})
            self.assertEqual(data.get('word'), w)
            self.assertTrue(data.get('cached'))
            self.assertTrue(bool(data.get('topic')))
            self.assertTrue(bool(data.get('meaning_vi')))

if __name__ == '__main__':
    unittest.main()

