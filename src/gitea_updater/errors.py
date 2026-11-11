"""Error type for expected update failures (reported without a stack trace)."""


class UpdateError(Exception):
    """An update step failed in a way the user can act on."""
