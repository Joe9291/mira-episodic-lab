"""Pilot variants (protocol section 7: base plus at most three, each committed before it runs).

v0 (base, pilot run 38956502610): instruction with one example value per answer type;
   E3a asked once per pair.
v1 (reason: base pilot analysis, docs/PILOT_M2.md): models copied the instruction's
   example values (up to 45% of answers) and answered A/B questions almost always with
   "A" (all three arms, so it is a position preference, not missing evidence). v1 removes
   every example value from the instruction and asks every E3a pair in both A/B orders;
   all other items are identical to v0.
"""
VARIANTS = {
    "v0": {"instruction": "v0", "order_both": False},
    "v1": {"instruction": "v1", "order_both": True},
}
