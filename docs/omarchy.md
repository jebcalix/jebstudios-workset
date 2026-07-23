# Omarchy / Hyprland

Omarchy usa Hyprland como compositor. Workset detecta automáticamente el backend **hyprland**.

## Rutas sugeridas

```bash
mkdir -p ~/.config/workset/profiles
# Opcional: symlink desde presets Omarchy
ln -sf ~/.config/omarchy/worksets/*.yaml ~/.config/workset/profiles/ 2>/dev/null || true
```

## Autostart post-login

```bash
# Picker al iniciar sesión
cp /usr/share/applications/jebstudios-workset-picker-autostart.desktop ~/.config/autostart/

# O aplicar perfil por defecto directamente
workset apply dev
```

## Ejemplo Hyprland

```yaml
name: Omarchy Dev
conditions:
  desktop: hyprland
apps:
  - id: terminal
    exec: [kitty]
    workspace: 1
    match:
      app_id: kitty
  - id: editor
    exec: [cursor, ~/proyectos]
    workspace: 2
    state: maximized
    match:
      wm_class: Cursor
```

## Comandos útiles

```bash
workset doctor          # debe mostrar backend: hyprland
workset capture --name omarchy-actual
hyprctl clients -j      # debug manual de ventanas
```
