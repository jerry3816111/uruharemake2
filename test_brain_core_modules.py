import unittest
import time
from uruha_runtime import RuntimeState, RuntimeConfig, RuntimeEvent, BlackboardEntry
from uruha_psyche import Psyche, PsycheConfig

class TestRuntimeState(unittest.TestCase):
    def test_drive_accumulation(self):
        config = RuntimeConfig(
            drive_boredom_gain_per_second=1.0,
            drive_social_gain_per_second=2.0,
            internal_urge_boredom_threshold=10.0,
            internal_urge_social_threshold=10.0
        )
        state = RuntimeState(config=config)
        state.last_drive_update_timestamp = time.time() - 5
        
        # Should not trigger threshold yet
        triggered = state.update_drives()
        self.assertFalse(triggered)
        self.assertAlmostEqual(state.boredom, 5.0, places=4)
        self.assertAlmostEqual(state.social_need, 10.0, places=4)
        
        # Update again after another 5 seconds
        state.last_drive_update_timestamp = time.time() - 5
        triggered = state.update_drives()
        self.assertTrue(triggered)
        self.assertAlmostEqual(state.boredom, 10.0, places=4)
        self.assertAlmostEqual(state.social_need, 20.0, places=4)

    def test_sleep_mode_behavior(self):
        config = RuntimeConfig(proactive_sleep_after_ignores=2)
        state = RuntimeState(config=config)
        
        state.register_proactive_output()
        self.assertFalse(state.proactive_sleep_mode)
        self.assertEqual(state.consecutive_proactive_count, 1)
        
        state.register_proactive_output()
        self.assertTrue(state.proactive_sleep_mode)
        self.assertEqual(state.consecutive_proactive_count, 2)
        
        # In sleep mode, social_need should stay 0
        state.social_need = 50.0
        state.last_drive_update_timestamp = time.time() - 10
        state.update_drives()
        self.assertEqual(state.social_need, 0.0)
        
        # User input should wake up
        state.register_user_input()
        self.assertFalse(state.proactive_sleep_mode)
        self.assertEqual(state.consecutive_proactive_count, 0)

    def test_prediction_buffer(self):
        state = RuntimeState()
        state.set_prediction("test_intent", 0.5, "source_intent")
        self.assertEqual(state.prediction_buffer["expected_intent"], "test_intent")
        self.assertEqual(state.prediction_buffer["expected_valence"], 0.5)
        self.assertEqual(state.prediction_buffer["source_plan_intent"], "source_intent")
        
        state.remember_prediction_error({"error": 0.1})
        self.assertEqual(state.last_prediction_error["error"], 0.1)

class TestPsyche(unittest.TestCase):
    def test_smoothing_behavior(self):
        config = PsycheConfig(mood_step_limit=10, trust_step_limit=10, soft_zone=50)
        psyche = Psyche(config=config)
        
        # Normal adjust
        psyche.adjust(mood_delta=5, trust_delta=5)
        self.assertEqual(psyche.mood, 5)
        self.assertEqual(psyche.trust, 55)
        
        # Soft zone behavior (overshoot reduction)
        # Reset to 90
        psyche.force_adjust(mood_delta=-psyche.mood + 90)
        self.assertEqual(psyche.mood, 90)

        # mood = 90. offset = 90. overshoot = (90-50)/50 = 0.8
        # magnitude = 10 * (1 - 0.45 * 0.8) = 10 * 0.64 = 6.4
        # applied = 6
        psyche.adjust(mood_delta=10, trust_delta=0)
        self.assertEqual(psyche.mood, 96) 

    def test_trust_lock(self):
        psyche = Psyche()
        psyche.force_adjust(trust_delta=-psyche.trust + 50) # trust = 50
        psyche.lock_trust(turns=2)
        
        # Positive trust delta should be ignored (set to 0 or negative)
        psyche.adjust(mood_delta=0, trust_delta=10)
        self.assertEqual(psyche.trust, 50)
        self.assertEqual(psyche.state.trust_lock_turns, 1)
        
        # Negative trust delta should still work
        psyche.adjust(mood_delta=0, trust_delta=-10)
        # delta = -10, magnitude = min(10, 6) = 6.
        self.assertEqual(psyche.trust, 44)
        self.assertEqual(psyche.state.trust_lock_turns, 0)

    def test_force_adjust(self):
        psyche = Psyche()
        psyche.force_adjust(mood_delta=20, trust_delta=-20, trust_lock_turns=5)
        # Initial 0, 50. -> 20, 30.
        self.assertEqual(psyche.mood, 20)
        self.assertEqual(psyche.trust, 30)
        self.assertEqual(psyche.state.trust_lock_turns, 5)

if __name__ == "__main__":
    unittest.main()
