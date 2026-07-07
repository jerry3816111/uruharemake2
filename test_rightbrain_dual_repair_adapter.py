import unittest

from uruha_brain_mac import RightBrain, _normalize_right_brain_adapter_path


class FakePeftModel:
    def __init__(self):
        self.calls = []

    def set_adapter(self, adapter_name):
        self.calls.append(adapter_name)


class RightBrainDualRepairAdapterTest(unittest.TestCase):
    def _rightbrain_with_fake_model(self):
        rightbrain = RightBrain(load_model=False)
        rightbrain.model = FakePeftModel()
        rightbrain.compat_adapter_dir = "/tmp/surface"
        rightbrain.surface_adapter_name = "surface"
        rightbrain.repair_adapter_name = "repair"
        rightbrain.repair_adapter_loaded = True
        rightbrain._active_model_adapter_name = "surface"
        return rightbrain

    def test_empty_adapter_path_stays_empty(self):
        self.assertEqual(_normalize_right_brain_adapter_path("", ""), "")
        self.assertEqual(_normalize_right_brain_adapter_path(None, ""), "")
        self.assertEqual(_normalize_right_brain_adapter_path("base-only", "x"), "")

    def test_repair_generation_switches_back_to_surface_adapter(self):
        rightbrain = self._rightbrain_with_fake_model()

        def fake_generate(messages, generation_kwargs):
            self.assertEqual(rightbrain._active_model_adapter_name, "repair")
            return "修正した。"

        rightbrain._generate_model_text = fake_generate
        reply = rightbrain._run_model_surface_generation(
            [{"role": "user", "content": "{}"}],
            {"do_sample": False},
            adapter_name="repair",
        )

        self.assertEqual(reply, "修正した。")
        self.assertEqual(rightbrain._active_model_adapter_name, "surface")
        self.assertEqual(rightbrain.model.calls, ["repair", "surface"])

    def test_repair_uses_surface_adapter_when_no_repair_adapter_loaded(self):
        rightbrain = self._rightbrain_with_fake_model()
        rightbrain.repair_adapter_loaded = False

        self.assertEqual(rightbrain._adapter_for_generation("repair"), "surface")


if __name__ == "__main__":
    unittest.main()
