from app.models import Candle
from app.patterns import detect_setup, ema


def mk(prices, vols=None, t0=0):
    vols = vols or [1000] * len(prices)
    out = []
    for i, (p, v) in enumerate(zip(prices, vols)):
        out.append(Candle(t=t0 + i * 60, o=p, h=p * 1.004, l=p * 0.996, c=p * 1.002, v=v))
    return out


def test_ema_length_and_smoothing():
    e = ema([1, 2, 3, 4, 5], 3)
    assert len(e) == 5 and e[-1] < 5 and e[-1] > e[0]


def test_too_few_candles():
    assert detect_setup(mk([5] * 5)).pattern == "none"


def test_bull_flag_detected():
    base = [5.0] * 15
    pole = [5.1, 5.3, 5.5, 5.7, 5.9]                 # +18% impulse on volume
    pullback = [5.85, 5.8, 5.78]                     # shallow, light volume
    prices = base + pole + pullback
    vols = [1000] * 15 + [20000] * 5 + [4000] * 3
    s = detect_setup(mk(prices, vols))
    assert s.pattern == "bull_flag"
    assert s.entry and s.stop and s.target and s.scale_out
    assert s.stop < s.entry < s.scale_out < s.target
    assert abs((s.target - s.entry) - 2 * (s.entry - s.stop)) < 0.02


def test_flat_top_detected():
    prices = [4.0] * 10 + [4.5, 4.4, 4.5, 4.42, 4.5, 4.45, 4.48, 4.5, 4.47]
    cs = mk(prices)
    for c in cs[10:]:
        c.h = 4.52  # repeated tests of the same ceiling
    s = detect_setup(cs)
    assert s.pattern == "flat_top"
    assert s.entry and s.stop and s.stop < s.entry
