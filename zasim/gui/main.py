from .mainwin import main
from .argp_qt import make_argument_parser

from ..external.qt import app

import sys

def cli_main():
    argp = make_argument_parser()

    args = argp.parse_args()

    if args.rule:
        if args.rule.startswith("0x"):
            args.rule = int(args.rule, 16)
        else:
            args.rule = int(args.rule)
    if args.alt_rule:
        if args.alt_rule.startswith("0x"):
            args.alt_rule = int(args.alt_rule, 16)
        else:
            args.alt_rule = int(args.alt_rule)

    main(**vars(args))

    sys.exit(app.exec_())

if __name__ == "__main__":
    cli_main()
