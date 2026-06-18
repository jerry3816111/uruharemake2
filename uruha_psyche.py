import math
import time
from dataclasses import dataclass, field

@dataclass
class PsycheConfig:
    mood_step_limit: int = 6
    trust_step_limit: int = 6
    soft_zone: int = 58

@dataclass
class PsycheState:
    mood: int = 0         # -100 to 100
    trust: int = 50       # 0 to 100
    trust_lock_turns: int = 0
    last_updated: float = field(default_factory=time.time)

class Psyche:
    def __init__(self, config: PsycheConfig = None, initial_mood=0, initial_trust=50):
        self.config = config or PsycheConfig()
        self.state = PsycheState(mood=initial_mood, trust=initial_trust)

    @property
    def mood(self):
        return self.state.mood

    @mood.setter
    def mood(self, value):
        self.state.mood = value

    @property
    def trust(self):
        return self.state.trust

    @trust.setter
    def trust(self, value):
        self.state.trust = value

    @property
    def trust_lock_turns(self):
        return self.state.trust_lock_turns

    @trust_lock_turns.setter
    def trust_lock_turns(self, value):
        self.state.trust_lock_turns = value

    def _smooth_delta(self, current, delta, step_limit, center=0):
        delta = int(round(delta or 0))
        if delta == 0:
            return 0

        magnitude = min(abs(delta), step_limit)
        offset = current - center
        if abs(offset) >= self.config.soft_zone and offset * delta > 0:
            overshoot = min(1.0, (abs(offset) - self.config.soft_zone) / max(1.0, 100 - self.config.soft_zone))
            magnitude = max(1.0, magnitude * (1.0 - 0.45 * overshoot))
        elif offset * delta < 0:
            magnitude = min(step_limit, magnitude * 1.1)

        applied = int(round(magnitude))
        if applied <= 0:
            applied = 1
        return applied if delta > 0 else -applied

    def adjust(self, mood_delta, trust_delta):
        if self.state.trust_lock_turns > 0:
            trust_delta = min(0, int(round(trust_delta or 0)))
        
        mood_step = self._smooth_delta(self.mood, mood_delta, self.config.mood_step_limit, center=0)
        trust_step = self._smooth_delta(self.trust, trust_delta, self.config.trust_step_limit, center=50)
        
        self.mood = max(-100, min(100, self.mood + mood_step))
        self.trust = max(0, min(100, self.trust + trust_step))
        self.state.last_updated = time.time()
        
        if self.state.trust_lock_turns > 0:
            self.state.trust_lock_turns = max(0, self.state.trust_lock_turns - 1)

    def force_adjust(self, mood_delta=0, trust_delta=0, trust_lock_turns=0):
        self.mood = max(-100, min(100, self.mood + int(round(mood_delta or 0))))
        self.trust = max(0, min(100, self.trust + int(round(trust_delta or 0))))
        if trust_lock_turns:
            self.state.trust_lock_turns = max(self.state.trust_lock_turns, int(trust_lock_turns))
        self.state.last_updated = time.time()

    def lock_trust(self, turns=2):
        self.state.trust_lock_turns = max(self.state.trust_lock_turns, int(turns))

    def get_state(self):
        return {
            "mood": self.mood,
            "trust": self.trust,
            "trust_lock_turns": self.state.trust_lock_turns,
        }

    def decay(self, idle_seconds):
        # 模擬時間沖淡一切：情緒會緩慢回歸 0
        decay_factor = math.exp(-idle_seconds / 3600.0) # 1 小時衰減
        self.mood = int(self.mood * decay_factor)
        # 信任度回歸 50 (中性)
        trust_gap = self.trust - 50
        self.trust = 50 + int(trust_gap * decay_factor)
        self.state.last_updated = time.time()
