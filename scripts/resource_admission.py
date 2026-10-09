"""Require measured process headroom before loading a local worker."""
from dataclasses import dataclass
import math

MIN_AVAILABLE = 600 * 1024**2
MAX_TREE_RSS = 7 * 1024**3


@dataclass(frozen=True)
class ResourcePolicy:
    expected_rss_bytes: int
    min_available_bytes: int = MIN_AVAILABLE
    max_tree_rss_bytes: int = MAX_TREE_RSS
    max_seconds: float = 3600
    stable_seconds: float = 10
    admission_seconds: float = 60
    poll_seconds: float = 1

    def __post_init__(self):
        if (type(self.expected_rss_bytes) is not int or self.expected_rss_bytes <= 0
                or type(self.min_available_bytes) is not int or self.min_available_bytes < MIN_AVAILABLE
                or type(self.max_tree_rss_bytes) is not int
                or not self.expected_rss_bytes <= self.max_tree_rss_bytes <= MAX_TREE_RSS):
            raise ValueError('Explicit process estimate and unchanged or stricter RAM guards required')
        for value in [self.max_seconds,self.stable_seconds,self.admission_seconds,self.poll_seconds]:
            if type(value) not in [int,float] or not math.isfinite(value) or value <= 0:
                raise ValueError('Finite positive sampling and execution budgets required')
        if (self.max_seconds > 3600 or self.admission_seconds > 600 or self.stable_seconds > self.admission_seconds
                or not .01 <= self.poll_seconds <= min(10,self.stable_seconds)):
            raise ValueError('Bounded admission and unchanged or stricter time guard required')

    @property
    def required_available_bytes(self):
        return self.expected_rss_bytes + self.min_available_bytes


class Admission:
    """A low sample resets readiness; expiry never starts a new worker."""
    def __init__(self,policy,started):
        if (not isinstance(policy,ResourcePolicy) or type(started) not in [int,float]
                or not math.isfinite(started) or started<0):
            raise ValueError('Explicit resource policy and finite nonnegative start clock required')
        self.policy=policy;self.started=started;self.previous=started;self.ready_since=None

    def observe(self,elapsed,available):
        if (type(elapsed) not in [int,float] or not math.isfinite(elapsed) or elapsed < self.previous
                or type(available) is not int or available < 0):
            raise ValueError('Monotonic clock and complete nonnegative RAM sample required')
        self.previous=elapsed
        if elapsed-self.started >= self.policy.admission_seconds:
            return 'deferred'
        if available < self.policy.required_available_bytes:
            self.ready_since=None
            return 'waiting_resources'
        if self.ready_since is None:self.ready_since=elapsed
        return 'ready' if elapsed-self.ready_since >= self.policy.stable_seconds else 'waiting_resources'
