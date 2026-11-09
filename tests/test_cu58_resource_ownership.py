"""CU58: control de propiedad multitenant sin conexiones a la BD real."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.dependencies.resource_tenant import require_owned_record
from app.models.product import Product
from app.models.branch import Branch
from app.models.sale import Sale
from app.models.reservation import Reservation


def _check(model, actor_tenant, row_exists):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = ((1,) if row_exists else None)
    actor = SimpleNamespace(tenant_id=actor_tenant)
    return db, actor


@pytest.mark.parametrize("model", [Product, Branch, Sale, Reservation], ids=["producto", "sucursal", "venta", "reserva"])
def test_recurso_de_otro_tenant_no_se_expone(model):
    db, actor = _check(model, 4, False)
    with pytest.raises(HTTPException) as error:
        require_owned_record(db, actor, model, 123)
    assert error.value.status_code == 404
    expression = db.query.return_value.filter.call_args.args
    sql = " AND ".join(str(e.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})) for e in expression)
    assert f"{model.__tablename__}.tenant_id = 4" in sql
    assert f"{model.__tablename__}.id = 123" in sql
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("model", [Product, Branch, Sale, Reservation], ids=["producto", "sucursal", "venta", "reserva"])
def test_recurso_propio_es_admitido(model):
    db, actor = _check(model, 4, True)
    assert require_owned_record(db, actor, model, 123) is None
    db.query.return_value.filter.return_value.first.assert_called_once()
    db.commit.assert_not_called()


@pytest.mark.parametrize("model", [Product, Branch, Sale, Reservation], ids=["producto", "sucursal", "venta", "reserva"])
def test_usuario_sin_empresa_se_rechaza_antes_de_consultar(model):
    db, actor = _check(model, None, True)
    with pytest.raises(HTTPException) as error:
        require_owned_record(db, actor, model, 123)
    assert error.value.status_code == 403
    db.query.assert_not_called()
    db.commit.assert_not_called()
