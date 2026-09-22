import uuid

# Fixed namespace: the same UUIDs every run, so the schematic symbols and
# the board footprints stay linked across regenerations.
NS = uuid.UUID("6f2b1c40-9a1e-5d3a-8c77-2f1d5a6b3e90")
NAME = "fakir"


def uid(*parts):
    return str(uuid.uuid5(NS, NAME + "|" + "|".join(parts)))
