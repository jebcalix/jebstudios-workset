# Maintainer: JebStudios
pkgname=jebstudios-workset
pkgver=1.1.0
pkgrel=1
pkgdesc="Multi-DE desktop workset profiles for Arch Linux"
arch=('any')
url="https://github.com/jebcalix/jebstudios-workset"
license=('MIT')
depends=(
  'python'
  'python-pydantic'
  'python-yaml'
)
makedepends=(
  'python-build'
  'python-installer'
  'python-setuptools'
  'python-wheel'
)
optdepends=(
  'python-gobject: GUI GTK (workset-picker)'
  'gtk4: GUI GTK'
  'libadwaita: GUI GTK'
  'libayatana-appindicator: icono de bandeja (workset-tray, preferido)'
  'libappindicator: icono de bandeja (fallback legacy)'
  'gnome-shell-extension-appindicator: bandeja en GNOME Shell'
  'snixembed: proxy SNI→XEmbed (XFCE/MATE/Cinnamon/i3 X11)'
  'waybar: bandeja en Hyprland/Sway/Omarchy'
  'wmctrl: X11 / XWayland / Plasma / XFCE / Cinnamon / MATE'
  'hyprland: Hyprland backend'
  'sway: Sway backend'
  'i3-wm: i3 backend'
  'plasma-workspace: Plasma (KDE) System Tray SNI'
  'qt6-tools: KDE qdbus6 backend'
  'xfce4-panel: bandeja XFCE'
  'cinnamon: Cinnamon (backend x11 vía wmctrl)'
  'mate-panel: bandeja MATE'
  'budgie-desktop: Budgie (backend x11 vía wmctrl)'
)
source=("$pkgname-$pkgver.tar.gz::file://$startdir")
sha256sums=('SKIP')

build() {
  cd "$srcdir"
  python -m build --wheel --no-isolation
}

package() {
  cd "$srcdir"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
  install -Dm644 PLAN.md "$pkgdir/usr/share/doc/$pkgname/PLAN.md"
  install -Dm644 docs/backends.md "$pkgdir/usr/share/doc/$pkgname/backends.md"
  install -Dm644 docs/flatpak.md "$pkgdir/usr/share/doc/$pkgname/flatpak.md"
  install -Dm644 docs/omarchy.md "$pkgdir/usr/share/doc/$pkgname/omarchy.md"
  install -Dm644 docs/tray.md "$pkgdir/usr/share/doc/$pkgname/tray.md"
  install -Dm644 examples/dev.yaml "$pkgdir/usr/share/doc/$pkgname/examples/dev.yaml"
  install -Dm644 examples/dual-monitor.yaml "$pkgdir/usr/share/doc/$pkgname/examples/dual-monitor.yaml"
  install -Dm644 packaging/jebstudios-workset-picker.desktop \
    "$pkgdir/usr/share/applications/jebstudios-workset-picker.desktop"
  install -Dm644 packaging/jebstudios-workset-picker-autostart.desktop \
    "$pkgdir/usr/share/applications/jebstudios-workset-picker-autostart.desktop"
  install -Dm644 packaging/jebstudios-workset-tray.desktop \
    "$pkgdir/usr/share/applications/jebstudios-workset-tray.desktop"
  install -Dm644 packaging/workset-picker.service \
    "$pkgdir/usr/lib/systemd/user/workset-picker.service"
  install -Dm644 packaging/workset.1 "$pkgdir/usr/share/man/man1/workset.1"
  install -Dm644 packaging/workset.bash \
    "$pkgdir/usr/share/bash-completion/completions/workset"

  # Iconos hicolor
  while IFS= read -r -d '' icon; do
    rel="${icon#packaging/icons/}"
    install -Dm644 "$icon" "$pkgdir/usr/share/icons/$rel"
  done < <(find packaging/icons/hicolor -type f \( -name '*.png' -o -name '*.svg' \) -print0)
}
