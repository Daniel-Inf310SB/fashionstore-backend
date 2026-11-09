from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.branch import Branch
from app.services.reports.report_assistant_service import ReportAssistantService


def _db(branches):
    db = MagicMock()
    db.scalars.return_value.all.return_value = branches
    return db


def test_speech_spacing_resolves_exact_branch():
    branches = [SimpleNamespace(id=36, name="FashionStore Cala Cala"),
                SimpleNamespace(id=40, name="FashionStore Calacoto")]
    db = _db(branches)
    result = ReportAssistantService._resolve_entity(
        db, Branch, lambda row: row.name, "fashion Store cala cala", tenant_id=1
    )
    assert result == (36, "FashionStore Cala Cala")
    # The SQL query itself remains tenant-scoped.
    assert "tenant_id" in str(db.scalars.call_args.args[0]).lower()


def test_compact_ambiguous_branch_does_not_guess():
    branches = [SimpleNamespace(id=36, name="FashionStore Cala Cala"),
                SimpleNamespace(id=99, name="Fashion Store Cala Cala")]
    result = ReportAssistantService._resolve_entity(
        _db(branches), Branch, lambda row: row.name,
        "fashionstorecalacala", tenant_id=1
    )
    assert result == (None, None)


def test_voice_variant_end_to_end_interpretation():
    db = _db([SimpleNamespace(id=36, name="FashionStore Cala Cala")])
    parsed = {"report_key": "sales", "action": "APPLY_FILTERS", "mode": "replace",
              "filters": {"branch_name": "fashion Store cala cala",
                          "date_from": "2026-10-01", "date_to": "2026-10-31"}}
    from app.schemas.report_assistant import ReportAssistantRequest
    with patch("app.services.reports.report_assistant_service.OpenAIService.generate_json", return_value=(parsed, {})):        response = ReportAssistantService.interpret(
            db, ReportAssistantRequest(command="Muéstrame las ventas de fashion Store cala cala durante octubre de 2026.", current_report="sales"),
            tenant_id=1,
        )
    assert response.can_execute is True
    assert response.filters["branch_id"] == 36
    assert response.filters["date_from"] == "2026-10-01"
