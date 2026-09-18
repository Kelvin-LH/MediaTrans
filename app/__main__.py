"""Allow `python -m app` as an alias of the `mediatrans` command."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
