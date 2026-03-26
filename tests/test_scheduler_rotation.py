"""
Tests for autonomous configuration rotation.
"""
from types import SimpleNamespace

from app.services.scheduler_service import SchedulerService


def test_scheduler_rotation_selects_next_config_in_sequence():
    service = SchedulerService()
    schedule = SimpleNamespace(
        configs_json='['
        '{"name":"France | marketing","locations":["Paris"],"categories":["marketing"],"language":"fr","limit":10},'
        '{"name":"Switzerland | consultant","locations":["Geneva"],"categories":["consultant"],"language":"fr","limit":8},'
        '{"name":"Australia | coach","locations":["Sydney"],"categories":["coach"],"language":"en","limit":6}'
        ']',
        last_used_config_index=0,
        locations="Paris",
        categories="marketing",
        language="fr",
        limit_per_location=10,
    )

    config, index, total = service._select_next_rotation_config(schedule)

    assert index == 1
    assert total == 3
    assert config["name"] == "Switzerland | consultant"
    assert config["locations"] == ["Geneva"]
    assert config["categories"] == ["consultant"]


def test_scheduler_rotation_wraps_back_to_first_config():
    service = SchedulerService()
    schedule = SimpleNamespace(
        configs_json='['
        '{"name":"France | marketing","locations":["Paris"],"categories":["marketing"],"language":"fr","limit":10},'
        '{"name":"Switzerland | consultant","locations":["Geneva"],"categories":["consultant"],"language":"fr","limit":8}'
        ']',
        last_used_config_index=1,
        locations="Paris",
        categories="marketing",
        language="fr",
        limit_per_location=10,
    )

    config, index, total = service._select_next_rotation_config(schedule)

    assert index == 0
    assert total == 2
    assert config["name"] == "France | marketing"


def test_scheduler_rotation_falls_back_to_single_schedule_config():
    service = SchedulerService()
    schedule = SimpleNamespace(
        configs_json="",
        last_used_config_index=None,
        locations="Paris,Geneva",
        categories="marketing,consultant",
        language="fr",
        limit_per_location=12,
    )

    config, index, total = service._select_next_rotation_config(schedule)

    assert index == 0
    assert total == 1
    assert config["locations"] == ["Paris", "Geneva"]
    assert config["categories"] == ["marketing", "consultant"]
    assert config["limit"] == 12
