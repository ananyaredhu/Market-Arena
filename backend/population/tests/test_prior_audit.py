import pytest

from backend.population.packs import load_pack
from scripts.prior_audit import scaled, with_known_brand


@pytest.fixture
def pack():
    return load_pack("saas")


def test_scaling_one_class_leaves_the_others_and_the_pack_untouched(pack):
    before = pack.model_dump()
    spec = scaled(pack, "alpha", 1.25)
    assert pack.model_dump() == before
    s0, s1 = pack.segments[0].priors, spec.segments[0].priors
    assert s1.alpha == pytest.approx((s0.alpha[0] * 1.25, s0.alpha[1] * 1.25))
    assert s1.budget == s0.budget and s1.w == s0.w and s1.brand == s0.brand


def test_feature_weights_and_brand_stay_within_zero_to_one(pack):
    for cls in ("w", "brand"):
        spec = scaled(pack, cls, 5.0)
        for seg in spec.segments:
            ranges = list(seg.priors.w.values()) if cls == "w" else list(seg.priors.brand.values())
            assert all(0 <= lo <= hi <= 1 for lo, hi in ranges)


def test_a_known_product_gets_a_brand_score_in_every_segment(pack):
    spec = with_known_brand(pack, 0.3)
    assert all(s.priors.brand["you"] == (0.3, 0.3) for s in spec.segments)
    assert all("you" not in s.priors.brand for s in pack.segments)
