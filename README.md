# KiCad Fakir-Board Generator

Generates a pogo-pin test fixture from a KiCAD project

- Creates a programming board to place your testing logic on
- Generates a 3d Printed Pogo Pin holder
- Desigs a clamp system to hold your target board in place

## Install

```sh
cd ~/boards/MyKicadProject        
curl -fsSL https://raw.githubusercontent.com/Mimoja/kicad-fakir-gen/main/install.sh | bash -s --
```

Installer Options:
| Option | What |
| --- | --- |
| `--name NAME` | folder and fixture name (default `fakir`) |
| `--force` | replace an existing folder |
| `--no-env` | do not create the Python environment |

## Howto

```sh
cd fakir
./generate.sh --pcb   # after changing the board or config.yaml
./generate.sh --3d    # after --pcb; both flags together do both
```

## AI Disclaimer
When contributing please ensure at least 51% of the work was human made. AI did review this entire codebase after writing and did fix some bugs and I absolutely agree that it is a powerfull tool, but at least try to have a human in the loop! thanks