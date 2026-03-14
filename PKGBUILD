# Maintainer: Kreuder <mk@singular.de>
pkgname=marklite
pkgver=0.3.3
pkgrel=1
pkgdesc='A lightweight GTK4 Markdown reader and editor'
arch=('any')
url='https://github.com/mkay/marklite'
license=('MIT')
depends=(
  'python'
  'python-gobject'
  'python-markdown'
  'python-pygments'
  'gtk4'
  'libadwaita'
  'webkitgtk-6.0'
)
makedepends=(
  'meson'
)
source=("$pkgname-$pkgver.tar.gz::https://github.com/mkay/marklite/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('2c5167d6f961e6aa21c59094bd9c005de567b62e858e6d82622020b462d0b9c6')

build() {
  arch-meson "$pkgname-$pkgver" build
  meson compile -C build
}

package() {
  meson install -C build --destdir "$pkgdir"
  install -Dm644 "$pkgname-$pkgver/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
