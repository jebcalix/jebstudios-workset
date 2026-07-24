# jebstudios-workset

**Workset** — perfiles de escritorio multi-DE para Arch Linux.

Elige o aplica un workset al iniciar sesión: aplicaciones, monitores, workspaces y estado de ventanas, sin atarte a GNOME, KDE ni Hyprland.

## Estado

**v1.1.0** — CLI, backends, capture y GUI GTK4 (perfiles, editor, doctor, ajustes). Ver [PLAN.md](PLAN.md).

## Matriz de compatibilidad

| Backend | Detección | Launch | Placement | Capture |
|---------|-----------|--------|-----------|---------|
| **hyprland** | `HYPRLAND_INSTANCE_SIGNATURE` | ✓ | ✓ | ✓ |
| **sway** | `SWAYSOCK` | ✓ | ✓ | ✓ |
| **i3** | `I3SOCK` | ✓ | ✓ | ✓ |
| **kde** | `XDG_CURRENT_DESKTOP=KDE` | ✓ | parcial (wmctrl) | ✓ |
| **gnome** | `XDG_CURRENT_DESKTOP=GNOME` | ✓ | parcial (XWayland) | parcial |
| **x11** | sesión X11 + wmctrl | ✓ | ✓ | ✓ |
| **generic** | fallback | ✓ | — | — |

Ver [docs/backends.md](docs/backends.md), [docs/flatpak.md](docs/flatpak.md), [docs/omarchy.md](docs/omarchy.md), [docs/tray.md](docs/tray.md).

## Instalación (desarrollo)

```bash
git clone https://github.com/jebcalix/jebstudios-workset.git
cd jebstudios-workset
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,gui]"
workset --help
pytest
```

Dependencias de sistema para la GUI: `python-gobject`, `gtk4`, `libadwaita`.

## Instalación (AUR)

```bash
yay -S jebstudios-workset
# o paru -S jebstudios-workset
```

Desde el repositorio (desarrollo local):

```bash
makepkg -si
```

## Uso

```bash
workset list
workset doctor
workset apply dev
workset apply dev --dry-run
workset capture --name "Mi setup"
workset duplicate dev dev-backup
workset default dev
workset-picker          # GUI GTK4 (o menú terminal)
```

### GUI (`workset-picker`)

- **Perfiles** — aplicar, dry-run, editar, duplicar, eliminar, capturar, nuevo
- **Editor** — nombre, condiciones, monitores y apps (exec, match, delays…)
- **Estado** — doctor del entorno y última ejecución
- **Ajustes** — picker al login, perfil por defecto e icono de bandeja

### Tray (`workset-tray`)

Icono multi-DE (StatusNotifier/AppIndicator). Actívalo en **Ajustes**, o:

```bash
sudo pacman -S libayatana-appindicator
# GNOME: + gnome-shell-extension-appindicator (activar extensión)
# Hyprland/Sway: Waybar con módulo tray
# XFCE/MATE/Cinnamon X11: panel + opcional snixembed
workset-tray
```

Detalle por escritorio: [docs/tray.md](docs/tray.md).

## Autostart (picker post-login)

```bash
cp /usr/share/applications/jebstudios-workset-picker-autostart.desktop ~/.config/autostart/
# o systemd user:
systemctl --user enable --now workset-picker.service
```

El autostart usa `workset-picker --login`, que respeta `show_picker_on_login` en `~/.config/workset/config.yaml`.

## Configuración

Perfiles en `~/.config/workset/profiles/*.yaml`.

```bash
mkdir -p ~/.config/workset/profiles
cp examples/dev.yaml ~/.config/workset/profiles/dev.yaml
```

## Licencia

MIT — JebStudios
