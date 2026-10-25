# -*- coding: utf-8 -*-
"""Opens the client's own Crucible screen, as the client's Crucible banner does on a click."""
from __future__ import absolute_import, print_function, unicode_literals


def open_crucible(challenge_id, logger):
    """Open the Crucible tab of the missions screen, at this series when one is given."""
    try:
        from gui.server_events.events_dispatcher import showChallenges
        showChallenges(challengeID=challenge_id or None)
    except Exception:
        logger.exception('Failed to open the Crucible screen')
