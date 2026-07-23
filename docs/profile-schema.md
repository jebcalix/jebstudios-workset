# Esquema de perfil Workset v1

Archivo: `~/.config/workset/profiles/<id>.yaml`

## Campos raíz

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `id` | string | no | Identificador; por defecto nombre del archivo |
| `name` | string | sí | Nombre visible en el picker |
| `description` | string | no | Descripción corta |
| `version` | int | no | Versión del schema (default: 1) |
| `monitors` | object | no | Layout de monitores (fase 2+) |
| `apps` | list | sí | Aplicaciones a lanzar |

## Objeto `monitors` (fase 2+)

```yaml
monitors:
  primary: DP-1          # o "primary", "left", EDID serial
  arrangement: horizontal
```

## Objeto `apps[]`

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `id` | string | no | ID interno para logs |
| `exec` | list[string] | sí | Comando y argumentos |
| `monitor` | string | no | Monitor destino |
| `workspace` | int/string | no | Workspace destino (backend-specific) |
| `state` | enum | no | `normal`, `maximized`, `fullscreen`, `minimized` |
| `match` | object | no | Criterios para identificar la ventana |
| `delay_ms` | int | no | Espera antes de lanzar (default: 0) |
| `timeout_ms` | int | no | Timeout esperando ventana (default: 15000) |

## Objeto `match`

| Campo | Descripción |
|-------|-------------|
| `app_id` | App ID Wayland |
| `wm_class` | WM_CLASS (X11 / XWayland) |
| `title` | Subcadena en el título |
| `instance` | N-ésima ventana del mismo match (1-based) |

## Estados soportados por backend

| state | Hyprland | i3/Sway | X11 | GNOME | KDE |
|-------|----------|---------|-----|-------|-----|
| normal | ✓ | ✓ | ✓ | ✓ | ✓ |
| maximized | ✓ | ✓ | parcial | parcial | ✓ |
| fullscreen | ✓ | ✓ | ✓ | ✓ | ✓ |
| minimized | ✓ | ✓ | parcial | difícil | ✓ |

## Ejemplo mínimo

```yaml
name: Desarrollo
apps:
  - exec: [cursor]
  - exec: [gnome-terminal]
```
