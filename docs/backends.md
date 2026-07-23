# Backends — matriz de implementación

| Backend | Detección | Placement | Herramientas | Estado |
|---------|-----------|-----------|--------------|--------|
| **generic** | fallback | ❌ | — | ✅ |
| **hyprland** | `HYPRLAND_INSTANCE_SIGNATURE` | ✅ | hyprctl | ✅ |
| **x11** | `XDG_SESSION_TYPE=x11` + wmctrl | ✅ | wmctrl, xrandr | ✅ |
| **sway** | `SWAYSOCK` | ✅ | swaymsg | ✅ |
| **i3** | `I3SOCK` | ✅ | i3-msg | ✅ |
| **kde** | `XDG_CURRENT_DESKTOP=KDE` | parcial | qdbus6, wmctrl | ✅ |
| **gnome** | `XDG_CURRENT_DESKTOP=GNOME` | parcial* | wmctrl, gdbus | ✅ |

\* GNOME Wayland nativo: placement limitado; XWayland funciona con wmctrl.

## Dependencias opcionales (Arch)

```bash
sudo pacman -S wmctrl          # X11 / XWayland / Plasma / XFCE / Cinnamon / MATE
# Hyprland: hyprctl incluido
# Sway/i3: sway / i3-wm
# Picker: python-gobject gtk4 libadwaita
# Tray:   libayatana-appindicator
# GNOME tray: gnome-shell-extension-appindicator
# X11 panel tray bridge: snixembed
```

Bandeja multi-DE: [tray.md](tray.md).

## Omarchy

Ver [omarchy.md](omarchy.md) — backend **hyprland** automático.

## Manjaro GNOME

Backend **gnome** detectado.

- **GNOME X11**: placement con wmctrl.
- **GNOME Wayland**: modo *solo launch* (sin esperas ni placement). `wmctrl` solo lista clientes XWayland; apps nativas (Cursor, gnome-terminal, etc.) no aparecen y antes provocaban timeout. En `workset doctor` se muestra esta limitación.
