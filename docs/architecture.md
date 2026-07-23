# Arquitectura — workset

## Capas

1. **CLI / UI** — entrada del usuario (`workset` CLI y GUI GTK4 `workset-picker`)
2. **Engine** — orquestación apply/capture
3. **Backends** — adaptadores por compositor/DE
4. **Config** — carga y validación de perfiles

La GUI (`workset.ui`) solo llama a loader/engine/doctor; no conoce backends concretos.

## Flujo `apply`

```
load profile → detect backend → for each app (ordered):
  sleep(delay_ms)
  subprocess exec (detached)
  backend.wait_for_window(match, timeout)
  backend.move_to_monitor(monitor)
  backend.move_to_workspace(workspace)
  backend.set_state(state)
```

## Backend interface

Cada backend implementa `workset.backends.base.Backend`:

- `name: str`
- `is_available() -> bool`
- `launch_only() -> bool` — si True, no soporta placement
- `wait_for_window(match, timeout_ms) -> WindowHandle | None`
- `move_to_monitor(handle, monitor_ref)`
- `move_to_workspace(handle, workspace)`
- `set_state(handle, state)`
- `list_monitors() -> list[MonitorInfo]`

## Registro

`workset.backends.registry.detect_backend()` prueba en orden:

1. Hyprland
2. Sway
3. i3
4. KDE
5. GNOME
6. X11 generic
7. Generic (launch only)

## Config paths

| Path | Uso |
|------|-----|
| `~/.config/workset/profiles/` | Perfiles YAML |
| `~/.config/workset/config.yaml` | Global: default_profile, show_picker_on_login, last_profile |
| `~/.local/state/workset/last-run.log` | Resultado de la última apply/captura (GUI) |
