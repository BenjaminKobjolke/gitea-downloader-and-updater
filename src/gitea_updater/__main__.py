"""Allow `python -m gitea_updater`."""

import sys

from gitea_updater.cli import main

sys.exit(main())
