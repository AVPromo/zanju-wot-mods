from __future__ import print_function, unicode_literals

from .. import config as _config_api
from .modes import build_scaleform_view_payload

_build_mode_preferences = _config_api._build_mode_preferences


def _build_scaleform_payload(vehicle, data, preferred_mode_id=None):
    return build_scaleform_view_payload(
        vehicle,
        data,
        _build_mode_preferences(),
        preferred_mode_id,
    )


def _log_scaleform_payload_summary(scaleform_payload, vehicle, last_log_key, logger):
    payload = scaleform_payload or {}
    modes = payload.get('modes') or []

    vehicle_name = (
        getattr(vehicle, 'userName', None)
        or getattr(vehicle, 'shortUserName', None)
        or getattr(vehicle, 'name', None)
        or '?'
    )
    vehicle_ref = '{0}:{1}'.format(getattr(vehicle, 'intCD', None), vehicle_name)
    mode_ids = []
    marker_counts = []
    for mode in modes:
        mode_id = str(mode.get('id') or '')
        mode_ids.append(mode_id)
        marker_counts.append('{0}:{1}'.format(mode_id, len(mode.get('markers') or [])))

    log_key = (
        vehicle_ref,
        payload.get('selectedModeId'),
        tuple(mode_ids),
        tuple(marker_counts),
    )
    if log_key == last_log_key:
        return last_log_key

    logger.info(
        'Scaleform payload: vehicle=%s selected=%s modes=%s markers=%s',
        vehicle_ref,
        payload.get('selectedModeId'),
        ','.join(mode_ids),
        ', '.join(marker_counts) or 'none',
    )
    return log_key
