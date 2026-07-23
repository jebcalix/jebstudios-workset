# Plan de desarrollo — jebstudios-workset

Aplicación multi-DE para Arch Linux que permite elegir un **workset** (perfil de escritorio) al iniciar sesión o bajo demanda.

**Repositorio:** https://github.com/jebstudios/jebstudios-workset  
**Versión:** 1.1.0

---

## Roadmap — estado

### Fase 0 — Fundación ✅
- Estructura repo, pyproject, CLI, schema YAML, GenericBackend, tests, PKGBUILD

### Fase 1 — MVP multi-DE ✅
- HyprlandBackend, X11Backend, SwayBackend, I3Backend
- WindowWaiter compartido
- Picker GTK4 + fallback terminal
- Autostart `.desktop` + systemd user service

### Fase 2 — KDE + GNOME ✅
- KdeBackend, GnomeBackend
- Resolución de monitores (`primary`, `left`, EDID)
- `list`, `validate`, `doctor`

### Fase 3 — Captura y editor ✅
- `workset capture`, `workset duplicate`, `workset edit`
- `--dry-run`, logging estructurado
- Picker: capturar y duplicar perfiles

### Fase 4 — Pulido AUR ✅
- PKGBUILD, man page, bash completions
- CI GitHub Actions (pytest + ruff)
- README con matriz de compatibilidad

### Fase 5 — Condiciones y docs ✅
- Reglas condicionales (`conditions.min_monitors`, `conditions.desktop`)
- Guía Flatpak (`docs/flatpak.md`)
- Presets Omarchy (`docs/omarchy.md`)

### Fase 6 — GUI ampliada ✅ (v1.1)
- App GTK4 + Libadwaita: perfiles, editor visual, doctor, ajustes
- `delete_profile`, registro de última ejecución
- `workset-picker --login` respeta `show_picker_on_login`
- Desktop de aplicación + autostart separados

---

## Próximos pasos opcionales

1. Publicar en AUR (`makepkg` + subir a aur.archlinux.org)
2. Probar en Hyprland/Omarchy con placement real
3. Extensión GNOME auxiliar para placement Wayland nativo
4. Reordenación drag-and-drop de apps en el editor

---

*JebStudios — workset v1.1.0*
