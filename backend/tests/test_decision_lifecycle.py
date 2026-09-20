"""Decision OS lifecycle regression tests."""

def test_prediction_outcome_reflection_tables_exist(db_session):
    from app.models.decision_prediction import DecisionPrediction
    from app.models.decision_outcome import DecisionOutcome, DecisionReflection

    assert DecisionPrediction.__tablename__ == "decision_predictions"
    assert DecisionOutcome.__tablename__ == "decision_outcomes"
    assert DecisionReflection.__tablename__ == "decision_reflections"


def test_matrix_is_non_prescriptive():
    from app.services.decision_analysis_service import compute_matrix

    result = compute_matrix(
        [{"criterion": "时间成本", "weight": 50}, {"criterion": "收益", "weight": 50}],
        [
            {"name": "A", "scores": {"时间成本": 8, "收益": 6}},
            {"name": "B", "scores": {"时间成本": 6, "收益": 8}},
        ],
    )
    assert result["winner"] is None
    assert "不代表系统推荐" in result["interpretation"]
