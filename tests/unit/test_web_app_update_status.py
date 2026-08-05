import os
import sys


project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'WebGui'))

from web_app import _normalize_update_status


def test_normalize_update_status_clears_stale_applying_when_version_matches():
    update_info = {
        'current_version': '1.3.0',
        'available_version': '1.3.0',
        'last_check': '2026-08-05 10:00:00',
        'update_status': 'applying',
        'has_update': False,
    }

    normalized = _normalize_update_status(update_info)

    assert normalized['update_status'] == 'idle'
    assert normalized['available_version'] == ''
    assert normalized['has_update'] is False