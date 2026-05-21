import unittest
from unittest.mock import MagicMock
import time
from datetime import datetime, timezone, timedelta

# Import modules from our project
import config
# Set test configs before importing other modules
config.LARK_APP_ID = "test_app_id"
config.LARK_APP_SECRET = "test_app_secret"
config.LARK_BASE_TOKEN = "test_base_token"
config.TABLE_TIKTOK_ID = "test_tiktok_table"
config.TABLE_TVV_ID = "test_tvv_table"

from assigner import (
    check_tvv_availability,
    assign_m0_lead_to_tvv,
    assign_t0_leads_to_tts,
    get_today_range,
    tz_vietnam
)
from lark_client import LarkClient

class TestLeadAssignment(unittest.TestCase):
    
    def setUp(self):
        # Create a mock Lark client
        self.client = MagicMock(spec=LarkClient)
        
    def test_today_range(self):
        start, end = get_today_range()
        self.assertTrue(start < end)
        # Ensure it represents roughly 24 hours
        diff_hours = (end - start) / (1000 * 60 * 60)
        self.assertAlmostEqual(diff_hours, 24.0, delta=0.1)

    def test_check_tvv_availability(self):
        # TVV is busy if they have a callback within 30 minutes of the target callback time.
        target_time = 1716200000000 # 2026-05-20 approx.
        cooldown_ms = 30 * 60 * 1000
        
        # Test case 1: No previous assignments today -> Should be Free
        self.assertTrue(check_tvv_availability("user_1", target_time, []))
        
        # Test case 2: Previous assignment with callback at the exact same time -> Should be Busy
        assignments = [
            {"assigned_user_id": "user_1", "callback_time": target_time, "assigned_time": int(time.time() * 1000)}
        ]
        self.assertFalse(check_tvv_availability("user_1", target_time, assignments))
        
        # Test case 3: Previous assignment is far away (e.g. 40 minutes before) -> Should be Free
        assignments = [
            {"assigned_user_id": "user_1", "callback_time": target_time - (40 * 60 * 1000), "assigned_time": int(time.time() * 1000)}
        ]
        self.assertTrue(check_tvv_availability("user_1", target_time, assignments))
        
        # Test case 4: Previous assignment is close (e.g. 20 minutes after) -> Should be Busy
        assignments = [
            {"assigned_user_id": "user_1", "callback_time": target_time + (20 * 60 * 1000), "assigned_time": int(time.time() * 1000)}
        ]
        self.assertFalse(check_tvv_availability("user_1", target_time, assignments))

        # Test case 5: Different user has a conflict -> User 1 should still be Free
        assignments = [
            {"assigned_user_id": "user_2", "callback_time": target_time, "assigned_time": int(time.time() * 1000)}
        ]
        self.assertTrue(check_tvv_availability("user_1", target_time, assignments))

    def test_assign_m0_lead_to_tvv_scenario_1_same_region_priority(self):
        """Scenario 1: Northern lead, active TVVs in North and South. Should pick North."""
        lead_id = "lead_001"
        lead_record = {
            "record_id": lead_id,
            "fields": {
                config.FIELD_TIKTOK_STATUS: "M0",
                config.FIELD_TIKTOK_REGION: "Miền Bắc",
                config.FIELD_TIKTOK_CALLBACK_TIME: 1716200000000
            }
        }
        self.client.get_record.return_value = lead_record
        
        # TVVs: TVV 1 (North), TVV 2 (South)
        tvvs_records = [
            {
                "record_id": "rec_tvv_1",
                "fields": {
                    config.FIELD_TVV_ROLE: "TVV",
                    config.FIELD_TVV_ACTIVE: True,
                    config.FIELD_TVV_REGION: "Miền Bắc",
                    config.FIELD_TVV_USER: [{"id": "user_north", "name": "TVV North"}]
                }
            },
            {
                "record_id": "rec_tvv_2",
                "fields": {
                    config.FIELD_TVV_ROLE: "TVV",
                    config.FIELD_TVV_ACTIVE: True,
                    config.FIELD_TVV_REGION: "Miền Nam",
                    config.FIELD_TVV_USER: [{"id": "user_south", "name": "TVV South"}]
                }
            }
        ]
        self.client.list_records.side_effect = lambda table_id: tvvs_records if table_id == config.TABLE_TVV_ID else []
        
        # Act
        selected = assign_m0_lead_to_tvv(self.client, lead_id)
        
        # Assert
        self.assertIsNotNone(selected)
        self.assertEqual(selected["user_id"], "user_north")
        self.assertEqual(selected["name"], "TVV North")
        self.client.update_record.assert_called_once()
        
    def test_assign_m0_lead_to_tvv_scenario_2_round_robin_fairness(self):
        """Scenario 2: Both TVVs in North, but TVV 1 has 1 assignment today, TVV 2 has 0. Pick TVV 2."""
        lead_id = "lead_002"
        lead_record = {
            "record_id": lead_id,
            "fields": {
                config.FIELD_TIKTOK_STATUS: "M0",
                config.FIELD_TIKTOK_REGION: "Miền Bắc",
                config.FIELD_TIKTOK_CALLBACK_TIME: 1716200000000
            }
        }
        self.client.get_record.return_value = lead_record
        
        tvvs_records = [
            {
                "record_id": "rec_tvv_1",
                "fields": {
                    config.FIELD_TVV_ROLE: "TVV",
                    config.FIELD_TVV_ACTIVE: True,
                    config.FIELD_TVV_REGION: "Miền Bắc",
                    config.FIELD_TVV_USER: [{"id": "user_n1", "name": "North 1"}]
                }
            },
            {
                "record_id": "rec_tvv_2",
                "fields": {
                    config.FIELD_TVV_ROLE: "TVV",
                    config.FIELD_TVV_ACTIVE: True,
                    config.FIELD_TVV_REGION: "Miền Bắc",
                    config.FIELD_TVV_USER: [{"id": "user_n2", "name": "North 2"}]
                }
            }
        ]
        
        # Mock today's assignments: user_n1 already has 1 assignment today
        start_ms, _ = get_today_range()
        today_assignments_records = [
            {
                "record_id": "prev_lead",
                "fields": {
                    config.FIELD_TIKTOK_ASSIGNED_USER: [{"id": "user_n1"}],
                    config.FIELD_TIKTOK_ASSIGNED_TIME: start_ms + 1000,
                    config.FIELD_TIKTOK_CALLBACK_TIME: start_ms + 10000
                }
            }
        ]
        
        def mock_list_records(table_id):
            if table_id == config.TABLE_TVV_ID:
                return tvvs_records
            elif table_id == config.TABLE_TIKTOK_ID:
                return today_assignments_records
            return []
            
        self.client.list_records.side_effect = mock_list_records
        
        # Act
        selected = assign_m0_lead_to_tvv(self.client, lead_id)
        
        # Assert
        self.assertIsNotNone(selected)
        self.assertEqual(selected["user_id"], "user_n2")  # Should pick user_n2 because they have 0 assignments
        
    def test_assign_m0_lead_to_tvv_scenario_3_overflow_to_other_region(self):
        """Scenario 3: North TVVs have both reached the daily limit (2 assignments). Should overflow to South TVV."""
        lead_id = "lead_003"
        lead_record = {
            "record_id": lead_id,
            "fields": {
                config.FIELD_TIKTOK_STATUS: "M0",
                config.FIELD_TIKTOK_REGION: "Miền Bắc",
                config.FIELD_TIKTOK_CALLBACK_TIME: 1716200000000
            }
        }
        self.client.get_record.return_value = lead_record
        
        tvvs_records = [
            {
                "record_id": "rec_tvv_1",
                "fields": {
                    config.FIELD_TVV_ROLE: "TVV",
                    config.FIELD_TVV_ACTIVE: True,
                    config.FIELD_TVV_REGION: "Miền Bắc",
                    config.FIELD_TVV_USER: [{"id": "user_n1", "name": "North 1"}]
                }
            },
            {
                "record_id": "rec_tvv_2",
                "fields": {
                    config.FIELD_TVV_ROLE: "TVV",
                    config.FIELD_TVV_ACTIVE: True,
                    config.FIELD_TVV_REGION: "Miền Nam",
                    config.FIELD_TVV_USER: [{"id": "user_s1", "name": "South 1"}]
                }
            }
        ]
        
        # Mock today's assignments: North 1 (user_n1) already has 2 assignments today
        start_ms, _ = get_today_range()
        today_assignments_records = [
            {
                "record_id": "l1",
                "fields": {
                    config.FIELD_TIKTOK_ASSIGNED_USER: [{"id": "user_n1"}],
                    config.FIELD_TIKTOK_ASSIGNED_TIME: start_ms + 1000,
                    config.FIELD_TIKTOK_CALLBACK_TIME: start_ms + 10000
                }
            },
            {
                "record_id": "l2",
                "fields": {
                    config.FIELD_TIKTOK_ASSIGNED_USER: [{"id": "user_n1"}],
                    config.FIELD_TIKTOK_ASSIGNED_TIME: start_ms + 2000,
                    config.FIELD_TIKTOK_CALLBACK_TIME: start_ms + 20000
                }
            }
        ]
        
        def mock_list_records(table_id):
            if table_id == config.TABLE_TVV_ID:
                return tvvs_records
            elif table_id == config.TABLE_TIKTOK_ID:
                return today_assignments_records
            return []
            
        self.client.list_records.side_effect = mock_list_records
        
        # Act
        selected = assign_m0_lead_to_tvv(self.client, lead_id)
        
        # Assert
        self.assertIsNotNone(selected)
        self.assertEqual(selected["user_id"], "user_s1")  # Should overflow to South TVV (user_s1)

    def test_assign_t0_leads_to_tts(self):
        """Test daily 8 AM T0 lead distribution to active TTS."""
        tvvs_records = [
            {
                "record_id": "rec_tts_1",
                "fields": {
                    config.FIELD_TVV_ROLE: "TTS",
                    config.FIELD_TVV_ACTIVE: True,
                    config.FIELD_TVV_USER: [{"id": "tts_1", "name": "TTS 1"}]
                }
            },
            {
                "record_id": "rec_tts_2",
                "fields": {
                    config.FIELD_TVV_ROLE: "TTS",
                    config.FIELD_TVV_ACTIVE: True,
                    config.FIELD_TVV_USER: [{"id": "tts_2", "name": "TTS 2"}]
                }
            }
        ]
        
        t0_leads = [
            {"record_id": "lead_t0_1", "fields": {config.FIELD_TIKTOK_STATUS: "T0"}},
            {"record_id": "lead_t0_2", "fields": {config.FIELD_TIKTOK_STATUS: "T0"}},
            {"record_id": "lead_t0_3", "fields": {config.FIELD_TIKTOK_STATUS: "T0"}}
        ]
        
        def mock_list_records(table_id):
            if table_id == config.TABLE_TVV_ID:
                return tvvs_records
            elif table_id == config.TABLE_TIKTOK_ID:
                return t0_leads
            return []
            
        self.client.list_records.side_effect = mock_list_records
        
        # Act
        assigned_count = assign_t0_leads_to_tts(self.client)
        
        # Assert
        self.assertEqual(assigned_count, 3)
        self.client.batch_update_records.assert_called_once()
        updates = self.client.batch_update_records.call_args[0][1]
        self.assertEqual(len(updates), 3)
        
        # Check distribution (TTS 1 -> tts_1, TTS 2 -> tts_2, TTS 1 -> tts_1 due to round robin)
        self.assertEqual(updates[0]["fields"][config.FIELD_TIKTOK_ASSIGNED_USER][0]["id"], "tts_1")
        self.assertEqual(updates[1]["fields"][config.FIELD_TIKTOK_ASSIGNED_USER][0]["id"], "tts_2")
        self.assertEqual(updates[2]["fields"][config.FIELD_TIKTOK_ASSIGNED_USER][0]["id"], "tts_1")

if __name__ == "__main__":
    unittest.main()
