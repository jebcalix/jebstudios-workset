# Bandeja (tray) multi-DE — Arch / AUR

`workset-tray` usa **StatusNotifier / AppIndicator** (Ayatana o `libappindicator`).
Cada escritorio necesita un *host* de bandeja distinto.

## Paquete común

```bash
sudo pacman -S libayatana-appindicator
# alternativa legacy:
# sudo pacman -S libappindicator
```

## Por escritorio

| DE | Host de bandeja | Paquetes útiles |
|----|-----------------|-----------------|
| **Plasma (KDE)** | System Tray nativo (SNI) | `plasma-workspace` |
| **GNOME** | Extensión AppIndicator | `gnome-shell-extension-appindicator` + activarla |
| **Hyprland / Sway / Omarchy** | Waybar `tray` (u otro SNI) | `waybar` |
| **XFCE** | Panel → Status Notifier Plugin | `xfce4-panel`, opcional `snixembed` |
| **MATE** | Panel notification area / SNI | `mate-panel`, opcional `snixembed` |
| **Cinnamon** | Panel systray | `cinnamon`, opcional `snixembed` |
| **Budgie** | Raven / system tray | `budgie-desktop` |
| **LXQt** | Status Notifier | `lxqt-panel` |
| **i3** | polybar / tray XEmbed | `polybar`, `snixembed` |
| **COSMIC** | soporte variable | — |

### snixembed

En paneles X11 que solo entienden la bandeja clásica (XEmbed), proxifica SNI:

```bash
sudo pacman -S snixembed
# autostart snixembed junto con el panel
```

## Autostart

Al activar el tray desde **Ajustes**, Workset escribe
`~/.config/autostart/jebstudios-workset-tray.desktop` (XDG), válido en
GNOME, Plasma, XFCE, Cinnamon, MATE, Budgie, etc.

## Diagnóstico

```bash
workset doctor
# o GUI → Estado → sección Bandeja
```

Muestra familia DE, API (`ayatana` / `appindicator3`) y si hay `StatusNotifierWatcher`.
