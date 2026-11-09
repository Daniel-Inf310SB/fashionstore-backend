"""CU58: protección multitenant de rutas hijas.

Pruebas sin BD ni Cloudinary reales. Presuponen instalado el parche
FashionStore_CU58_Proteccion_Rutas_Hijas.zip.
"""
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.dialects.postgresql import dialect

from app.api.routes import product_images as images
from app.api.routes import product_variants as variants


@pytest.fixture
def db():
    return MagicMock()


def actor(tenant_id):
    return SimpleNamespace(id=18, tenant_id=tenant_id)


def mock_lookup(db, found):
    value = (17,) if found else None
    db.query.return_value.filter.return_value.first.return_value = value
    db.query.return_value.join.return_value.filter.return_value.first.return_value = value


def sql_filter(db):
    direct = db.query.return_value.filter.call_args
    joined = db.query.return_value.join.return_value.filter.call_args
    call = joined if joined is not None else direct
    assert call is not None, "La consulta no aplicó un filtro de propiedad"
    expressions = call.args
    return ' AND '.join(str(e.compile(dialect=dialect(), compile_kwargs={'literal_binds': True})) for e in expressions)


@pytest.mark.parametrize('route,pk,method', [
    ('images', 'product', 'list'),
    ('images', 'product', 'upload'),
    ('images', 'image', 'update'),
    ('images', 'image', 'delete'),
    ('variants', 'product', 'list'),
    ('variants', 'product', 'create'),
    ('variants', 'variant', 'update'),
    ('variants', 'variant', 'upload'),
])
def test_autorizacion_se_aplica_antes_del_servicio(db, route, pk, method):
    module = images if route == 'images' else variants
    helper = getattr(module, f'_require_cu58_{pk}_owner')
    mock_lookup(db, False)
    with pytest.raises(HTTPException) as err:
        helper(db, actor(4), 999)
    assert err.value.status_code == 404
    assert 'products.tenant_id = 4' in sql_filter(db)
    assert ' = 999' in sql_filter(db)
    db.commit.assert_not_called()


@pytest.mark.parametrize('module,pk', [(images, 'product'), (images, 'image'),
                                       (variants, 'product'), (variants, 'variant')])
def test_sin_tenant_se_rechaza_antes_de_la_consulta(db, module, pk):
    with pytest.raises(HTTPException) as err:
        getattr(module, f'_require_cu58_{pk}_owner')(db, actor(None), 45)
    assert err.value.status_code == 403
    db.query.assert_not_called()


@pytest.mark.parametrize('module,pk', [(images, 'product'), (images, 'image'),
                                       (variants, 'product'), (variants, 'variant')])
def test_tenant_propietario_se_admite(db, module, pk):
    mock_lookup(db, True)
    assert getattr(module, f'_require_cu58_{pk}_owner')(db, actor(3), 17) is None
    assert 'products.tenant_id = 3' in sql_filter(db)
    db.commit.assert_not_called()


def request():
    return SimpleNamespace(client=SimpleNamespace(host='127.0.0.1'), headers={})


@pytest.mark.parametrize('target,service,kwargs', [
    (images.get_product_images, images.ProductImageService.get_images,
     {'product_id': 90, 'include_inactive': False}),
    (images.update_product_image, images.ProductImageService.update_image,
     {'image_id': 90, 'payload': SimpleNamespace(), 'request': request()}),
    (images.delete_product_image, images.ProductImageService.delete_image,
     {'image_id': 90, 'request': request()}),
    (variants.get_product_variants, variants.ProductVariantService.get_variants,
     {'product_id': 90, 'include_inactive': False}),
    (variants.create_product_variant, variants.ProductVariantService.create_variant,
     {'product_id': 90, 'payload': SimpleNamespace(), 'request': request()}),
    (variants.update_product_variant, variants.ProductVariantService.update_variant,
     {'variant_id': 90, 'payload': SimpleNamespace(), 'request': request()}),
])
def test_rutas_no_llaman_servicios_ante_ids_ajenos(db, target, service, kwargs):
    mock_lookup(db, False)
    # Patch de la función de servicio sobre su clase, no sobre el objeto ya ligado.
    from unittest.mock import patch as p
    owner_cls = images.ProductImageService if target.__module__.endswith('product_images') else variants.ProductVariantService
    func_name = service.__name__
    with p.object(owner_cls, func_name) as business:
        with pytest.raises(HTTPException) as err:
            target(db=db, current_user=actor(4), **kwargs)
        assert err.value.status_code == 404
        business.assert_not_called()


@pytest.mark.parametrize('target', [images.upload_product_image, variants.upload_variant_image])
def test_upload_ajeno_no_llama_cloudinary(db, target):
    import asyncio
    mock_lookup(db, False)
    upload = UploadFile(filename='test.jpg', file=BytesIO(b'not-an-image'))
    with patch.object(images.CloudinaryService, 'upload_image') as cloud:
        with pytest.raises(HTTPException) as err:
            kwargs = ({'product_id': 90, 'alt_text': None, 'sort_order': 0, 'is_primary': False}
                      if target is images.upload_product_image else {'variant_id': 90})
            asyncio.run(target(db=db, current_user=actor(4), request=request(), file=upload, **kwargs))
        assert err.value.status_code == 404
        cloud.assert_not_called()
