# Maintainer: Your Name <your@email.com>
pkgname=marklite
pkgver=0.1.0
pkgrel=1
pkgdesc="A lightweight GTK4 Markdown reader and editor for GNOME"
arch=('any')
license=('GPL-3.0-or-later')
depends=(
  'python'
  'python-gobject'
  'gtk4'
  'libadwaita'
  'webkitgtk-6.0'
  'gtksourceview5'
  'python-markdown'
  'python-pygments'
)
makedepends=('meson' 'ninja')
source=()

build() {
  cd "$startdir"
  meson setup builddir --prefix=/usr --buildtype=plain
  ninja -C builddir
}

package() {
  cd "$startdir"
  DESTDIR="$pkgdir" meson install -C builddir
}
