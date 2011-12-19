VERSION = '0.0.2'

from setuptools import setup, find_packages

setup(
      name = 'zasim',
      version = VERSION,
      author = 'zasim team',
      description = 'A cellular automaton simulation environment.',
      keywords = '',
      url = '',
      packages = find_packages(),
      package_data = {
          'zasim.examples.notebooks':
              ['notebooks/*', 'static/**/*', 'templates/*'],
          },
      entry_points="""
          [console_scripts]
          zasim_cli = zasim.cagen.main:main
          zasim_gui = zasim.gui.main:cli_main
          zasim_tutorial = zasim.examples.notebooks.notebook_app:launch_notebook_server [notebook]
      """,
      extras_require = dict(notebook = ["tornado>=2.1.0", "zmq"]),
    )
