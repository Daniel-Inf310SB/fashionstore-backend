"""Pruebas de regresión para la selección pública de sucursales."""
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from app.api.routes.store_branches import resolve_storefront_tenant, get_store_branches
from app.models.tenant import Tenant


def test_public_store_branches_restricted_to_configured_tenant(monkeypatch):
    monkeypatch.setenv("PUBLIC_STOREFRONT_TENANT_SLUG", "fashionstore")
    db = MagicMock()
    tenant = Tenant(id=7, name="FashionStore", slug="fashionstore", is_active=True)
    db.query.return_value.filter.return_value.first.return_value = tenant
    with patch("app.api.routes.store_branches.BranchService.get_branches", return_value={"items": [], "page": 1, "page_size": 100, "total": 0, "total_pages": 0}) as service:
        get_store_branches(tenant_slug=None, db=db)
    assert service.call_args.kwargs["tenant_id"] == 7
    assert service.call_args.kwargs["is_active"] is True


def test_public_store_does_not_fall_back_to_other_tenants(monkeypatch):
    monkeypatch.setenv("PUBLIC_STOREFRONT_TENANT_SLUG", "missing-store")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        resolve_storefront_tenant(db)
    assert exc.value.status_code == 503


def test_public_store_rejects_empty_slug(monkeypatch):
    monkeypatch.setenv("PUBLIC_STOREFRONT_TENANT_SLUG", "  ")
    with pytest.raises(HTTPException) as exc:
        resolve_storefront_tenant(MagicMock())
    assert exc.value.status_code == 503
