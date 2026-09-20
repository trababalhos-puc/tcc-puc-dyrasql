"""Testes do DecisionEngine alinhados a monografia."""

from __future__ import annotations

from decision_engine import DecisionEngine


def test_volume_factor_article_example(article_metadata):
    engine = DecisionEngine()
    fv = engine._calculate_volume_factor(article_metadata)
    assert abs(fv - 0.27) < 0.02


def test_volume_factor_empty_metadata():
    engine = DecisionEngine()
    assert engine._calculate_volume_factor({}) == 0.5
    assert engine._calculate_volume_factor(None) == 0.5


def test_complexity_factor_article_example(article_complexity):
    engine = DecisionEngine()
    fc = engine._calculate_complexity_factor(article_complexity)
    assert abs(fc - 0.69) < 0.01


def test_select_cluster_thresholds():
    engine = DecisionEngine()
    assert engine._select_cluster(0.29) == "small"
    assert engine._select_cluster(0.3) == "medium"
    assert engine._select_cluster(0.7) == "medium"
    assert engine._select_cluster(0.71) == "large"


def test_decide_article_example(article_metadata, article_complexity, mock_history_manager):
    engine = DecisionEngine()
    mock_history_manager.get_historical_factor.return_value = 0.5

    decision = engine.decide(
        query="SELECT 1",
        fingerprint="abc",
        metadata=article_metadata,
        complexity=article_complexity,
        history_manager=mock_history_manager,
    )

    assert abs(decision["score"] - 0.44) < 0.03
    assert decision["cluster"] == "medium"
    assert abs(decision["factors"]["volume"] - 0.27) < 0.02
    assert abs(decision["factors"]["complexity"] - 0.69) < 0.01
    assert decision["factors"]["historical"] == 0.5


def test_decide_high_score_routes_to_large(mock_history_manager):
    engine = DecisionEngine()
    mock_history_manager.get_historical_factor.return_value = 1.0
    metadata = {
        "t": {
            "total_size_bytes": int(900 * (1024**3)),
            "total_records": int(5e8),
        }
    }
    complexity = {
        "joins": 5,
        "aggregations": 5,
        "subqueries": 5,
        "partitioned_filters": 0,
        "non_partitioned_filters": 5,
    }
    decision = engine.decide("q", "fp", metadata, complexity, mock_history_manager)
    assert decision["cluster"] == "large"
    assert decision["score"] > 0.7


def test_decide_low_score_routes_to_small(mock_history_manager):
    engine = DecisionEngine()
    mock_history_manager.get_historical_factor.return_value = 0.0
    metadata = {
        "t": {
            "total_size_bytes": int(0.01 * (1024**3)),
            "total_records": 10,
        }
    }
    complexity = {
        "joins": 0,
        "aggregations": 0,
        "subqueries": 0,
        "partitioned_filters": 0,
        "non_partitioned_filters": 0,
    }
    decision = engine.decide("q", "fp", metadata, complexity, mock_history_manager)
    assert decision["cluster"] == "small"
    assert decision["score"] < 0.3
