from scamshield.ratelimit import SlidingWindowLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_blocks_after_limit_and_recovers():
    clock = Clock()
    limiter = SlidingWindowLimiter(2, 60, clock=clock)
    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    clock.t = 61
    assert limiter.allow("a")


def test_keys_are_independent():
    limiter = SlidingWindowLimiter(1, 60, clock=Clock())
    assert limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("a")
