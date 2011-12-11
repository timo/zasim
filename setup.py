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
      entry_points="""
          [console_scripts]
          zasim_cli = zasim.cagen.main:main
          zasim_gui = zasim.gui.main:cli_main
          zasim_tutorial = zasim.examples.notebooks.notebook_app
      """
    )
