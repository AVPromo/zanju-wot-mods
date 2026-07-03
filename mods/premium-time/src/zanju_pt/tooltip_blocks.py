"""Exact end time in the Premium Account header-button tooltip.

Hovering the Premium Account header button opens a classic blocks tooltip: the header UI
requests the `ammunitionEmptySlot` tooltip type with the `#tooltips:header/premium_buy`
alias, which `AmmunitionEmptyBlockTooltipData._packBlocks` turns into title/body text
blocks. That type is a generic alias-driven carrier used by other UI too, so the hook
appends the "Ends on" block only for the premium-buy alias, and only while Premium
Account time is actually running.
"""
from __future__ import print_function, unicode_literals

from .formatting import end_datetime_text, ends_on_label, server_now

_PREMIUM_BUY_ALIAS = '#tooltips:header/premium_buy'

_original_pack_blocks = None


def _premium_ends_on(logger):
    """'<date> <time> UTC+X' end-time value for the current Premium Account, or ''."""
    try:
        from helpers import dependency
        from skeletons.gui.shared import IItemsCache
        stats = dependency.instance(IItemsCache).items.stats
        if not stats.isPremium:
            return ''
        expiry = int(stats.activePremiumExpiryTime or 0)
    except Exception:
        logger.exception('Failed to read premium account expiry time')
        return ''
    if expiry <= server_now():
        return ''
    return end_datetime_text(expiry)


def install(logger):
    """Patch the premium-buy blocks tooltip to append the end time. Returns True when active."""
    global _original_pack_blocks

    if _original_pack_blocks is not None:
        return True

    try:
        from gui.shared.tooltips.module import AmmunitionEmptyBlockTooltipData
    except ImportError:
        logger.exception('Blocks tooltip data class not found; premium tooltip integration disabled')
        return False

    original = AmmunitionEmptyBlockTooltipData._packBlocks

    def _pack_blocks_with_end_time(self, *args, **kwargs):
        items = original(self, *args, **kwargs)
        if not args or args[0] != _PREMIUM_BUY_ALIAS:
            return items
        try:
            value = _premium_ends_on(logger)
            if value:
                from gui.Scaleform.genConsts.BLOCKS_TOOLTIP_TYPES import BLOCKS_TOOLTIP_TYPES
                from gui.shared.formatters import text_styles
                from gui.shared.tooltips import formatters
                line = '{0} {1}'.format(text_styles.main(ends_on_label()), text_styles.neutral(value))
                items.append(formatters.packAlignedTextBlockData(
                    text=line,
                    align=BLOCKS_TOOLTIP_TYPES.ALIGN_CENTER,
                    padding=formatters.packPadding(top=8),
                ))
        except Exception:
            logger.exception('Failed to append premium end time to tooltip')
        return items

    AmmunitionEmptyBlockTooltipData._packBlocks = _pack_blocks_with_end_time
    _original_pack_blocks = original
    logger.info('Premium tooltip integration installed')
    return True


def uninstall(logger):
    global _original_pack_blocks

    if _original_pack_blocks is None:
        return
    try:
        from gui.shared.tooltips.module import AmmunitionEmptyBlockTooltipData
        AmmunitionEmptyBlockTooltipData._packBlocks = _original_pack_blocks
    except Exception:
        logger.exception('Failed to restore AmmunitionEmptyBlockTooltipData._packBlocks')
    _original_pack_blocks = None
