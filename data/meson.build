desktop_file = configure_file(
  input: 'de.singular.stenmark.desktop.in',
  output: 'de.singular.stenmark.desktop',
  configuration: conf,
  install: true,
  install_dir: datadir / 'applications',
)

install_data(
  'de.singular.stenmark.svg',
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps',
)

install_data(
  'de.singular.stenmark-symbolic.svg',
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps',
)

install_data(
  'de.singular.stenmark.metainfo.xml',
  install_dir: datadir / 'metainfo',
)
