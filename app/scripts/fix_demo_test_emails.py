"""Migra exclusivamente correos demo conocidos de .test a @example.com.

Vista previa: python -m app.scripts.fix_demo_test_emails
Aplicar:       python -m app.scripts.fix_demo_test_emails --apply

No modifica passwords, roles, tenants, IDs, pedidos ni reservas.
"""
import argparse
import re
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.user import User

CLIENT = re.compile(r"^(fs|us)\.cliente\d{2}@fashionstore\.test$")
STAFF = re.compile(r"^(fs|us)_(?:enc|caj)_\d+_[123]@fashionstore\.test$")


def candidate(user):
    old = user.email.lower()
    if CLIENT.fullmatch(old):
        prefix = old.split('@')[0]
        alias, customer = prefix.split('.', 1)
        expected_username = f'{alias}_cliente_{customer.removeprefix("cliente")}'
        if user.username != expected_username:
            raise ValueError(f"Usuario {user.id}: username no coincide con cuenta demo de cliente")
        return old.split('@')[0] + '@example.com'
    if STAFF.fullmatch(old):
        if user.username != old.split('@')[0]:
            raise ValueError(f"Usuario {user.id}: username no coincide con cuenta demo de personal")
        return old.split('@')[0] + '@example.com'
    if old == 'superadmin@fashionstore.test':
        if user.username != 'fs_superadmin' or user.tenant_id is not None:
            raise ValueError('La cuenta superadmin no coincide con el seed demo previsto')
        return 'superadmin@example.com'
    if old == 'admin@urbanstyle.test':
        if user.username != 'admin_urbanstyle':
            raise ValueError('La cuenta administrativa Urban Style no coincide con el seed demo previsto')
        return 'admin@example.com'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Confirma la actualización atómica')
    args = parser.parse_args()
    with SessionLocal() as db:
        users = db.scalars(select(User).order_by(User.id)).all()
        changes = []
        all_emails = {u.email.lower(): u.id for u in users}
        for user in users:
            new = candidate(user)
            if new is None or new == user.email.lower():
                continue
            if (owner := all_emails.get(new)) is not None and owner != user.id:
                raise RuntimeError(f'Conflicto: {new} ya está ocupado por el usuario {owner}. No se modifica nada.')
            changes.append((user, new))
        if len({new for _, new in changes}) != len(changes):
            raise RuntimeError('Dos cuentas de origen colisionan con el mismo correo destino. No se modifica nada.')
        print(f'Cuentas demo con correo .test por migrar: {len(changes)}')
        for user, new in changes:
            print(f'  ID {user.id} | tenant {user.tenant_id} | {user.email} -> {new}')
        if not args.apply:
            print('VISTA PREVIA: PostgreSQL no se ha modificado. Usa --apply para confirmar.')
            return
        for user, new in changes:
            user.email = new
        db.commit()
        print(f'APLICADO: {len(changes)} correos actualizados; IDs y hashes de contraseñas conservados.')
        print('Los recibos históricos conservan el correo registrado originalmente.')


if __name__ == '__main__':
    main()
