desktop_file = configure_file(
  input: 'de.singular.marklite.desktop.in',
  output: 'de.singular.marklite.desktop',
  configuration: conf,
  install: true,
  install_dir: datadir / 'applications',
)

install_data(
  'de.singular.marklite.svg',
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps',
)

install_data(
  'icons/hicolor/scalable/apps/de.singular.marklite-symbolic.svg',
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps',
)
