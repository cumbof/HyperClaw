"""Unit tests for skills/anomaly_detector/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("anomaly_detector")
AnomalyDetector = _mod.AnomalyDetector

NORMAL_OBS = [
    ["morning", "office_IP", "email_access"],
    ["afternoon", "office_IP", "file_access"],
    ["morning", "VPN", "email_access"],
    ["afternoon", "office_IP", "email_access"],
    ["morning", "office_IP", "file_access"],
]

NORMAL_SAMPLE = ["morning", "office_IP", "email_access"]
ANOMALY_SAMPLE = ["midnight", "foreign_IP", "tor_browser", "admin_access"]


@pytest.fixture()
def det(tmp_state_dir):
    return AnomalyDetector()


@pytest.fixture()
def trained_det(tmp_state_dir):
    d = AnomalyDetector()
    d.train_normal("login", NORMAL_OBS)
    return d


# ---------------------------------------------------------------------------
# train_normal
# ---------------------------------------------------------------------------

class TestTrainNormal:
    def test_success(self, det):
        result = det.train_normal("login", NORMAL_OBS)
        assert result["status"] == "success"

    def test_sample_count_correct(self, trained_det):
        profiles = trained_det.list_profiles()
        assert profiles["profiles"]["login"]["sample_count"] == len(NORMAL_OBS)

    def test_custom_threshold_stored(self, det):
        det.train_normal("login", NORMAL_OBS, threshold=0.45)
        profiles = det.list_profiles()
        assert profiles["profiles"]["login"]["threshold"] == 0.45

    def test_missing_profile_id(self, det):
        result = det.train_normal("", NORMAL_OBS)
        assert result["status"] == "failed"

    def test_missing_observations(self, det):
        result = det.train_normal("login", [])
        assert result["status"] == "failed"

    def test_additive_on_second_call(self, det):
        det.train_normal("login", NORMAL_OBS[:2])
        det.train_normal("login", NORMAL_OBS[2:])
        profiles = det.list_profiles()
        assert profiles["profiles"]["login"]["sample_count"] == len(NORMAL_OBS)


# ---------------------------------------------------------------------------
# score_observation
# ---------------------------------------------------------------------------

class TestScoreObservation:
    def test_normal_sample_not_anomaly(self, trained_det):
        result = trained_det.score_observation("login", NORMAL_SAMPLE)
        assert result["status"] == "success"
        assert result["is_anomaly"] is False
        assert result["label"] == "NORMAL"

    def test_anomaly_sample_is_anomaly(self, trained_det):
        result = trained_det.score_observation("login", ANOMALY_SAMPLE)
        assert result["status"] == "success"
        assert result["is_anomaly"] is True
        assert result["label"] == "ANOMALY"

    def test_score_range(self, trained_det):
        result = trained_det.score_observation("login", NORMAL_SAMPLE)
        assert 0.0 <= result["anomaly_score"] <= 2.0

    def test_anomaly_score_higher_than_normal(self, trained_det):
        normal = trained_det.score_observation("login", NORMAL_SAMPLE)
        anomalous = trained_det.score_observation("login", ANOMALY_SAMPLE)
        assert anomalous["anomaly_score"] > normal["anomaly_score"]

    def test_unknown_profile(self, det):
        result = det.score_observation("no_profile", NORMAL_SAMPLE)
        assert result["status"] == "failed"

    def test_empty_features(self, trained_det):
        result = trained_det.score_observation("login", [])
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# update_threshold
# ---------------------------------------------------------------------------

class TestUpdateThreshold:
    def test_updates_correctly(self, trained_det):
        trained_det.update_threshold("login", 0.5)
        profiles = trained_det.list_profiles()
        assert profiles["profiles"]["login"]["threshold"] == 0.5

    def test_invalid_threshold_high(self, trained_det):
        result = trained_det.update_threshold("login", 3.0)
        assert result["status"] == "failed"

    def test_invalid_threshold_negative(self, trained_det):
        result = trained_det.update_threshold("login", -0.1)
        assert result["status"] == "failed"

    def test_unknown_profile(self, det):
        result = det.update_threshold("nonexistent", 0.5)
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# list_profiles
# ---------------------------------------------------------------------------

class TestListProfiles:
    def test_empty_initially(self, det):
        result = det.list_profiles()
        assert result["status"] == "success"
        assert result["profiles"] == {}

    def test_multiple_profiles(self, det):
        det.train_normal("a", NORMAL_OBS)
        det.train_normal("b", NORMAL_OBS)
        result = det.list_profiles()
        assert "a" in result["profiles"]
        assert "b" in result["profiles"]


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_profile_survives_reinstantiation(self, tmp_state_dir):
        d1 = AnomalyDetector()
        d1.train_normal("login", NORMAL_OBS)

        d2 = AnomalyDetector()
        result = d2.score_observation("login", NORMAL_SAMPLE)
        assert result["status"] == "success"
