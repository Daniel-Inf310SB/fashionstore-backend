"""Pruebas ligeras de contrato sin requerir PostgreSQL."""
import pytest
from pydantic import ValidationError
from app.schemas.home import HomeBannerInput, HomeBannerPatch
from app.models.home_banner import HomeBanner
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql


def _valid(**overrides):
    data = {"title": "Nueva colección", "image_url": "https://example.com/banner.jpg"}
    data.update(overrides)
    return HomeBannerInput(**data)


def test_banner_catalog_without_target():
    assert _valid().target_id is None


def test_banner_product_requires_target():
    with pytest.raises(ValidationError):
        _valid(target_type="product")
    assert _valid(target_type="product", target_id=2).target_id == 2


def test_banner_catalog_rejects_target():
    with pytest.raises(ValidationError):
        _valid(target_type="catalog", target_id=1)


def test_banner_requires_http_image():
    with pytest.raises(ValidationError):
        _valid(image_url="javascript:alert(1)")


def test_banner_rejects_invalid_dates():
    with pytest.raises(ValidationError):
        _valid(starts_at="2026-11-06T12:00:00Z", ends_at="2026-11-05T12:00:00Z")


def test_banner_table_has_tenant_constraint():
    sql = str(CreateTable(HomeBanner.__table__).compile(dialect=postgresql.dialect()))
    assert "tenant_id" in sql and "FOREIGN KEY" in sql


def test_patch_allows_null_to_clear_optional_field():
    assert HomeBannerPatch(subtitle=None).model_dump(exclude_unset=True) == {"subtitle": None}
