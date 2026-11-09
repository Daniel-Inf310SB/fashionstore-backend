from pathlib import Path


def test_cu52_onboard_route_is_declared():
    from fastapi.routing import APIRoute
    from app.api.routes.platform_tenants import router
    matches = [r for r in router.routes if isinstance(r, APIRoute) and r.path == '/platform/tenants/onboard']
    assert len(matches) == 1
    assert matches[0].methods == {'POST'}


def test_cu52_onboarding_rejects_missing_admin():
    from pydantic import ValidationError
    from app.schemas.platform import TenantOnboardCreate
    try:
        TenantOnboardCreate.model_validate({'tenant': {'name': 'Demo', 'slug': 'demo'}})
    except ValidationError:
        pass
    else:
        raise AssertionError('El administrador inicial debe ser obligatorio')


def test_cu52_onboarding_normalizes_admin_email():
    from app.schemas.platform import TenantOnboardCreate
    item = TenantOnboardCreate.model_validate({
        'tenant': {'name': 'Demo', 'slug': 'demo'},
        'admin': {'first_name': 'Admin', 'email': '  PERSONA@EXAMPLE.COM  ', 'password': 'Secret987!'},
    })
    assert item.admin.email == 'persona@example.com'
