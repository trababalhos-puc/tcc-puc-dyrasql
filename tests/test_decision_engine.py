"""Testes do DecisionEngine alinhados a monografia."""

from __future__ import annotations

from decision_engine import DecisionEngine


def test_volume_factor_article_example(article_metadata):
    engine = DecisionEngine()
    fv = engine._calculate_volume_factor(article_metadata)
    assert abs(fv - 0.54) < 0.02  # escala em MB (T_max=1000 GB, R_max=1e9)


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
    assert engine._select_cluster(0.59) == "small"
    assert engine._select_cluster(0.6) == "medium"
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

    assert abs(decision["score"] - 0.57) < 0.03
    assert decision["cluster"] == "small"  # S = 0,57 < 0,6 (limiar calibrado)
    assert abs(decision["factors"]["volume"] - 0.54) < 0.02
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


def test_volume_factor_sub_gb_not_negative():
    engine = DecisionEngine()
    metadata = {"t": {"total_size_bytes": 50 * 1024**2, "total_records": 1_000_000}}
    assert engine._calculate_volume_factor(metadata) > 0


def test_complexity_factor_memory_intensive():
    engine = DecisionEngine()
    base = {
        "joins": 0,
        "aggregations": 1,
        "subqueries": 0,
        "partitioned_filters": 0,
        "non_partitioned_filters": 0,
    }
    leve = engine._calculate_complexity_factor(base)
    pesada = engine._calculate_complexity_factor({**base, "memory_intensive": 1})
    assert abs((pesada - leve) - 0.75) < 1e-9


def test_failure_floor_escalates_cluster(mock_history_manager):
    """Apos falha no medium, mesmo com score de small o destino e o large."""
    engine = DecisionEngine()
    mock_history_manager.get_historical_factor.return_value = 1.0
    mock_history_manager.get_minimum_cluster.return_value = "large"
    metadata = {"t": {"total_size_bytes": 1024**2, "total_records": 10}}
    complexity = {
        "joins": 0,
        "aggregations": 1,
        "subqueries": 0,
        "partitioned_filters": 0,
        "non_partitioned_filters": 0,
    }
    decision = engine.decide("q", "fp", metadata, complexity, mock_history_manager)
    assert decision["score"] < 0.6
    assert decision["cluster"] == "large"


def test_failure_floor_never_downsizes(mock_history_manager):
    """O piso so eleva: se o score ja indica large, o piso medium nao reduz."""
    engine = DecisionEngine()
    mock_history_manager.get_historical_factor.return_value = 1.0
    mock_history_manager.get_minimum_cluster.return_value = "medium"
    metadata = {"t": {"total_size_bytes": 3 * 1024**3, "total_records": 10**9}}
    complexity = {
        "joins": 3,
        "aggregations": 3,
        "subqueries": 2,
        "partitioned_filters": 0,
        "non_partitioned_filters": 2,
        "memory_intensive": 1,
    }
    decision = engine.decide("q", "fp", metadata, complexity, mock_history_manager)
    assert decision["cluster"] == "large"
