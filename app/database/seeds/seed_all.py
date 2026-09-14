from app.database.session import SessionLocal

from app.database.seeds.seed_auth import seed_auth
from app.database.seeds.seed_users import seed_users
from app.database.seeds.seed_locations import seed_locations
from app.database.seeds.seed_catalog import seed_catalog
from app.database.seeds.seed_providers import seed_providers
from app.database.seeds.seed_inventory import seed_inventory
from app.database.seeds.seed_commerce import seed_commerce


def run_seed():

    db = SessionLocal()

    try:

        print("")
        print(
            "======================================"
        )
        print(
            "       FASHIONSTORE DATABASE SEED"
        )
        print(
            "======================================"
        )
        print("")

        # =====================================================
        # MÓDULO 1
        # Roles, permisos y administrador
        # =====================================================

        seed_auth(
            db
        )

        # =====================================================
        # MÓDULO 1
        # Empleados
        # =====================================================

        seed_users(
            db
        )

        # =====================================================
        # MÓDULO 2
        # Ciudades, sucursales y asignaciones
        # =====================================================

        seed_locations(
            db
        )

        # =====================================================
        # MÓDULO 3
        # Catálogo completo
        #
        # Incluye:
        # - categorías
        # - audiencias
        # - tallas
        # - colores
        # - temporadas
        # - colecciones
        # - promociones
        # - productos
        # - variantes talla/color
        # - imágenes
        # - relaciones
        # - assets del vestidor virtual
        # =====================================================

        seed_catalog(
            db
        )

        # =====================================================
        # MÓDULO 4
        # Proveedores
        #
        # Incluye:
        # - proveedores
        # - productos por proveedor
        # - precio de compra
        # - pedido mínimo
        # - tiempo estimado de entrega
        # - disponibilidad por variante
        # =====================================================

        seed_providers(
            db
        )

        # =====================================================
        # MÓDULO 5
        # Inventario
        #
        # Incluye:
        # - inventario por sucursal
        # - stock por variante
        # - stock reservado
        # - stock mínimo / máximo
        # - punto de reposición
        # - movimientos de inventario
        # - entradas desde proveedor
        # - ajustes de inventario
        # - trazabilidad por usuario
        # =====================================================

        seed_inventory(
            db
        )

        # =====================================================
        # ITERACIÓN 2
        # MÓDULOS 7 AL 11
        #
        # Incluye:
        # - clientes
        # - reservas
        # - prendas reservadas
        # - carritos
        # - compras digitales
        # - ventas presenciales
        # - pagos electrónicos
        # - pagos en caja
        # - movimientos SALE de inventario
        # - comprobantes
        # - items históricos de comprobante
        # =====================================================

        seed_commerce(
            db
        )

        # =====================================================
        # COMMIT GENERAL
        # =====================================================

        db.commit()

        print("")
        print(
            "======================================"
        )
        print(
            "         SEED COMPLETADO"
        )
        print(
            "======================================"
        )
        print("")

    except Exception as exc:

        db.rollback()

        print("")
        print(
            "======================================"
        )
        print(
            "         ERROR EN EL SEED"
        )
        print(
            "======================================"
        )
        print("")

        print(
            f"Error ejecutando seed: {exc}"
        )

        raise

    finally:

        db.close()


if __name__ == "__main__":

    run_seed()