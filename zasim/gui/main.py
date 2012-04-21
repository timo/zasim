from .mainwin import main
from .argp_qt import make_argument_parser

from ..external.qt import app

import sys

def cli_main():
    argp = make_argument_parser()

    args = argp.parse_args()

    main(**vars(args))

    sys.exit(app.exec_())

if __name__ == "__main__":
    cli_main()
