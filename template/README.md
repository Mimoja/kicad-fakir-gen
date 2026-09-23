# @@FIXTURE_NAME@@ -- test fixture for @@SOURCE_NAME@@

This PCB has holes to solder in the pogo pins needed to test @@SOURCE_NAME@@'s test points
and a 3d printed holder to go with it

## Rebuild

```sh
./generate.sh --pcb   # PCB + schematic, from @@SOURCE_NAME@@'s test points
./generate.sh --3d    # PrintFiles/ (parts + plate.3mf), 3D models, stackup.png
./generate.sh --pcb --full --3d     # everything, without being asked
```

Settings are in `config.yaml`, a venv was created by the installer

## Parts needed

| PrintFiles/ | qty | hardware |
| --- | --- | --- |
| `-holder` | 1 | 4 stack screws and optionally heat-set-inserts |
| `-lid` | 1 | 1 screw in the front face optionally heat-set-insert |
| `-caps` | 1 set of 4  | none |
| `-key` | 1 | 1 screw |
| `-feet` | 1 set of 4 | 4 screws |

## HowTo

- Generate the PCB, route your testing logic
- Order PCB, Print 3d printed parts
- Screw on the PCB and feet from the bottom, use the lid and pressers to ensure the board is pressed into the pogo pins properly
