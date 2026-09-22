# The P-series families, as the round-head (B1) variant.  Barrel is what
# gets soldered into the fixture PCB; length and stroke decide where the
# board under test ends up.
#                 barrel  tip   length  stroke
PINS = {
    "P50": (0.68, 0.90, 16.4, 2.65),
    "P75": (1.02, 1.30, 16.6, 2.65),
    "P100": (1.36, 1.80, 33.4, 6.35),
    "P125": (2.02, 2.50, 33.4, 6.35),
    "P160": (2.36, 3.00, 44.5, 4.00),
}


def get(key):
    # "P75-B1" and friends still resolve; the head does not matter here
    key = str(key).upper().split("-")[0]
    if key not in PINS:
        raise KeyError("unknown pogo pin %r, one of %s"
                       % (key, ", ".join(PINS)))
    return dict(zip(("barrel", "tip", "length", "stroke"), PINS[key]))
