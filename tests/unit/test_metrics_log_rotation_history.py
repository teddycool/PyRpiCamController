import json
import os
import sys


project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'WebGui'))
sys.path.insert(0, os.path.join(project_root, 'CamController'))

import web_app
import MetricsLogger


class TestMetricsHistoryRotation:
    def test_dashboard_history_reads_rotated_metrics_logs(self, tmp_path, monkeypatch):
        base_log = tmp_path / 'cam-metrics.log'
        rotated_log = tmp_path / 'cam-metrics.log.1'

        now_ts = 2_000_000.0
        old_sample_ts = now_ts - (23 * 60 * 60)
        new_sample_ts = now_ts - (60 * 60)

        rotated_log.write_text(
            json.dumps({'data': {'sample_timestamp': old_sample_ts, 'cpu_temperature': 47.2}}) + '\n',
            encoding='utf-8',
        )
        base_log.write_text(
            json.dumps({'data': {'sample_timestamp': new_sample_ts, 'cpu_temperature': 49.9}}) + '\n',
            encoding='utf-8',
        )

        def fake_get(setting_key, default=None):
            if setting_key == 'MetricsLogFilePath':
                return str(base_log)
            return default

        monkeypatch.setattr(web_app.settings_manager, 'get', fake_get)
        monkeypatch.setattr(web_app.time, 'time', lambda: now_ts)

        payload = web_app._load_metrics_dashboard_history(window_minutes=24 * 60, max_lines=200)

        assert payload['sample_count'] == 2
        assert payload['oldest_sample_timestamp'] == round(old_sample_ts, 3)
        assert payload['newest_sample_timestamp'] == round(new_sample_ts, 3)

        temperature_series = payload['widgets']['temperature']['series']
        assert len(temperature_series) == 1
        points = temperature_series[0]['points']
        assert len(points) == 2
        assert points[0]['timestamp'] == round(old_sample_ts, 3)
        assert points[1]['timestamp'] == round(new_sample_ts, 3)
        assert str(rotated_log) in payload['source_files']

    def test_dashboard_history_excludes_samples_older_than_24h(self, tmp_path, monkeypatch):
        base_log = tmp_path / 'cam-metrics.log'
        rotated_log = tmp_path / 'cam-metrics.log.1'

        now_ts = 3_000_000.0
        stale_sample_ts = now_ts - (26 * 60 * 60)
        valid_sample_ts = now_ts - (2 * 60 * 60)

        rotated_log.write_text(
            json.dumps({'data': {'sample_timestamp': stale_sample_ts, 'cpu_temperature': 45.0}}) + '\n',
            encoding='utf-8',
        )
        base_log.write_text(
            json.dumps({'data': {'sample_timestamp': valid_sample_ts, 'cpu_temperature': 50.0}}) + '\n',
            encoding='utf-8',
        )

        def fake_get(setting_key, default=None):
            if setting_key == 'MetricsLogFilePath':
                return str(base_log)
            return default

        monkeypatch.setattr(web_app.settings_manager, 'get', fake_get)
        monkeypatch.setattr(web_app.time, 'time', lambda: now_ts)

        payload = web_app._load_metrics_dashboard_history(window_minutes=24 * 60, max_lines=200)

        assert payload['sample_count'] == 1
        temperature_series = payload['widgets']['temperature']['series']
        assert len(temperature_series) == 1
        points = temperature_series[0]['points']
        assert len(points) == 1
        assert points[0]['timestamp'] == round(valid_sample_ts, 3)


class TestMetricsRetentionCapacity:
    def test_min_backup_count_scales_with_metrics_interval(self):
        fast_interval_backup_count = MetricsLogger.calculate_min_backup_count_for_24h(
            max_bytes=1_000_000,
            interval_seconds=5,
            estimated_event_bytes=900,
        )
        slow_interval_backup_count = MetricsLogger.calculate_min_backup_count_for_24h(
            max_bytes=1_000_000,
            interval_seconds=60,
            estimated_event_bytes=900,
        )

        assert fast_interval_backup_count > slow_interval_backup_count
        assert fast_interval_backup_count >= 18

    def test_min_backup_count_has_sane_floor(self):
        backup_count = MetricsLogger.calculate_min_backup_count_for_24h(
            max_bytes=10_000_000,
            interval_seconds=300,
            estimated_event_bytes=400,
        )

        assert backup_count >= 1
