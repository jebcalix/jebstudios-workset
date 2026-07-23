# Flatpak en perfiles Workset

Las apps Flatpak no comparten el mismo `wm_class` que los binarios nativos.
Usa `flatpak run` en `exec` y define `match.app_id` o `match.wm_class` explícitamente.

## Ejemplo

```yaml
name: Flatpak Dev
apps:
  - id: vscode-flatpak
    exec: [flatpak, run, com.visualstudio.code]
    match:
      app_id: com.visualstudio.code
    workspace: 1

  - id: spotify
    exec: [flatpak, run, com.spotify.Client]
    match:
      wm_class: spotify
    monitor: primary
```

## Notas

- El `app_id` Wayland suele coincidir con el ID Flatpak (`com.example.App`).
- En XWayland, `wm_class` puede diferir; usa `workset capture --name debug` para inspeccionar.
- Sandbox: algunas apps Flatpak tardan más en abrir; aumenta `timeout_ms`.
