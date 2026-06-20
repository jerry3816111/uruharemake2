import datetime
import time
from dataclasses import dataclass, field

@dataclass
class RuntimeConfig:
    drive_boredom_gain_per_second: float = 0.1
    drive_social_gain_per_second: float = 0.1
    internal_urge_boredom_threshold: float = 60.0
    internal_urge_social_threshold: float = 60.0
    proactive_sleep_after_ignores: int = 3

@dataclass
class BlackboardEntry:
    stage: str
    label: str
    payload: dict
    salience: float = 0.5
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@dataclass(order=True)
class RuntimeEvent:
    priority: int
    seq: int
    event_type: str = field(compare=False)
    payload: dict = field(default_factory=dict, compare=False)
    created_at: float = field(default_factory=time.time, compare=False)

@dataclass
class RuntimeState:
    config: RuntimeConfig = field(default_factory=RuntimeConfig)
    cycle_index: int = 0
    autonomous_tick_index: int = 0
    last_user_input: str = ""
    current_focus: str = ""
    active_goal: str = ""
    open_loops: list = field(default_factory=list)
    latent_goal_stack: list = field(default_factory=list)
    working_memory: list = field(default_factory=list)
    blackboard: list = field(default_factory=list)
    last_route: dict = field(default_factory=dict)
    last_attention_frame: dict = field(default_factory=dict)
    last_appraisal: dict = field(default_factory=dict)
    last_internal_monologue: str = ""
    last_candidates: list = field(default_factory=list)
    last_selected_plan: dict = field(default_factory=dict)
    planner_tick_trace: list = field(default_factory=list)
    planner_tick_count: int = 0
    self_correction_applied: bool = False
    last_speech_plan: dict = field(default_factory=dict)
    last_self_monitor: dict = field(default_factory=dict)
    last_reply: str = ""
    last_memory_writes: list = field(default_factory=list)
    last_memory_before: dict = field(default_factory=dict)
    last_memory_after: dict = field(default_factory=dict)
    last_memory_diff: dict = field(default_factory=dict)
    last_psyche_before: dict = field(default_factory=dict)
    last_psyche_after: dict = field(default_factory=dict)
    last_state_diff: dict = field(default_factory=dict)
    last_autonomous_result: dict = field(default_factory=dict)
    pending_proactive_turn: dict = field(default_factory=dict)
    last_proactive_delivery: dict = field(default_factory=dict)
    proactive_delivery_keys: list = field(default_factory=list)
    autonomous_traces: list = field(default_factory=list)
    turn_traces: list = field(default_factory=list)
    boredom: float = 0.0
    social_need: float = 0.0
    consecutive_proactive_count: int = 0
    proactive_sleep_mode: bool = False
    last_interaction_timestamp: float = field(default_factory=time.time)
    last_drive_update_timestamp: float = field(default_factory=time.time)
    prediction_buffer: dict = field(
        default_factory=lambda: {
            "expected_intent": "",
            "expected_valence": 0.0,
            "source_plan_intent": "",
            "updated_at": 0.0,
        }
    )
    last_prediction_error: dict = field(default_factory=dict)

    def touch_interaction(self, when=None, reset_drives=False):
        now = float(when if when is not None else time.time())
        self.last_interaction_timestamp = now
        self.last_drive_update_timestamp = now
        if reset_drives:
            self.boredom = 0.0
            self.social_need = 0.0

    def register_user_input(self, when=None):
        self.touch_interaction(when=when, reset_drives=True)
        self.consecutive_proactive_count = 0
        self.proactive_sleep_mode = False
        self.proactive_delivery_keys = []

    def register_proactive_output(self, when=None, delivery_key=""):
        self.touch_interaction(when=when, reset_drives=True)
        self.consecutive_proactive_count += 1
        key = str(delivery_key or "").strip()
        if key and key not in self.proactive_delivery_keys:
            self.proactive_delivery_keys = [*self.proactive_delivery_keys, key][-8:]
        if self.consecutive_proactive_count >= self.config.proactive_sleep_after_ignores:
            self.proactive_sleep_mode = True
            self.social_need = 0.0

    def update_drives(self, current_time=None):
        now = float(current_time if current_time is not None else time.time())
        delta_time = max(0.0, now - float(self.last_drive_update_timestamp or now))
        if delta_time <= 0.0:
            return False
        self.boredom = min(100.0, float(self.boredom) + (delta_time * self.config.drive_boredom_gain_per_second))
        self.last_drive_update_timestamp = now
        if self.proactive_sleep_mode:
            self.social_need = 0.0
            return False
        self.social_need = min(100.0, float(self.social_need) + (delta_time * self.config.drive_social_gain_per_second))
        return bool(
            self.boredom >= self.config.internal_urge_boredom_threshold
            and self.social_need >= self.config.internal_urge_social_threshold
        )

    def reset_drives(self, when=None):
        self.touch_interaction(when=when, reset_drives=True)

    def set_prediction(self, expected_intent, expected_valence, source_plan_intent="", updated_at=None):
        self.prediction_buffer = {
            "expected_intent": str(expected_intent or "").strip(),
            "expected_valence": max(-1.0, min(1.0, float(expected_valence or 0.0))),
            "source_plan_intent": str(source_plan_intent or "").strip(),
            "updated_at": float(updated_at if updated_at is not None else time.time()),
        }

    def remember_prediction_error(self, payload):
        self.last_prediction_error = dict(payload or {})
