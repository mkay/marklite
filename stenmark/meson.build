configure_file(
  input: '__init__.py.in',
  output: '__init__.py',
  configuration: conf,
  install: true,
  install_dir: moduledir,
)

stenmark_sources = [
  '__main__.py',
  'app.py',
  'document_panel.py',
  'editor.py',
  'file_watcher.py',
  'html_template.py',
  'markdown_renderer.py',
  'settings_dialog.py',
  'settings_manager.py',
  'sidebar.py',
  'viewer.py',
  'welcome.py',
  'window.py',
]

install_data(stenmark_sources, install_dir: moduledir)

# App-specific icons — kept inside the package data dir
install_subdir(
  'data' / 'icons',
  install_dir: moduledir / 'data',
)

install_subdir(
  'data' / 'editor',
  install_dir: moduledir / 'data',
  exclude_directories: ['node_modules', 'src'],
  exclude_files: ['package.json', 'package-lock.json'],
)

gnome.compile_resources(
  'de.singular.stenmark',
  'data/de.singular.stenmark.gresource.xml',
  source_dir: 'data',
  gresource_bundle: true,
  install: true,
  install_dir: moduledir / 'data',
)
