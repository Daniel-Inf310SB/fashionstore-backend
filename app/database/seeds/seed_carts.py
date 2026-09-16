from __future__ import annotations

from collections import defaultdict

from sqlalchemy import (
    select,
)
from sqlalchemy.orm import (
    Session,
)

from app.models.cart_item import (
    CartItem,
)
from app.models.inventory import (
    Inventory,
)
from app.models.shopping_cart import (
    ShoppingCart,
)
from app.models.user import (
    User,
)


# =========================================================
# CLIENTES Y ESCENARIOS DEL SEED
# =========================================================
#
# branch_offset permite distribuir los carritos entre
# distintas sucursales disponibles sin depender de IDs fijos.
# =========================================================

CART_SCENARIOS = [
    {
        "email":
            "cliente01@fashionstore.com",

        "status":
            "ACTIVE",

        "quantities":
            [
                1,
                2,
            ],

        "branch_offset":
            0,
    },
    {
        "email":
            "cliente02@fashionstore.com",

        "status":
            "ACTIVE",

        "quantities":
            [
                1,
                1,
                2,
            ],

        "branch_offset":
            1,
    },
    {
        "email":
            "cliente03@fashionstore.com",

        "status":
            "CONVERTED",

        "quantities":
            [
                2,
                1,
            ],

        "branch_offset":
            2,
    },
    {
        "email":
            "cliente04@fashionstore.com",

        "status":
            "ABANDONED",

        "quantities":
            [
                1,
                1,
            ],

        "branch_offset":
            0,
    },
]


# =========================================================
# CLIENTE
# =========================================================

def _get_customer(
    db: Session,

    email: str,
) -> User:

    customer = db.scalar(
        select(
            User
        )
        .where(
            User.email
            ==
            email
        )
    )


    if customer is None:

        raise RuntimeError(
            f"No existe el cliente {email}. "
            "Ejecuta seed_customers primero."
        )


    return customer


# =========================================================
# INVENTARIOS DISPONIBLES AGRUPADOS POR SUCURSAL
# =========================================================

def _get_inventories_by_branch(
    db: Session,

    *,
    minimum_available: int = 5,
) -> dict[
    int,
    list[Inventory],
]:

    inventories = list(
        db.scalars(
            select(
                Inventory
            )
            .where(
                Inventory.is_active.is_(
                    True
                ),
                (
                    Inventory.stock_quantity
                    -
                    Inventory.reserved_quantity
                )
                >=
                minimum_available,
            )
            .order_by(
                Inventory.branch_id,
                Inventory.id,
            )
        ).all()
    )


    if not inventories:

        raise RuntimeError(
            "No existe inventario suficiente "
            "para crear carritos de prueba."
        )


    grouped: dict[
        int,
        list[Inventory],
    ] = defaultdict(
        list
    )


    for inventory in inventories:

        grouped[
            inventory.branch_id
        ].append(
            inventory
        )


    return dict(
        grouped
    )


# =========================================================
# SELECCIONAR SUCURSAL PARA UN ESCENARIO
# =========================================================

def _choose_branch_id(
    inventories_by_branch: dict[
        int,
        list[Inventory],
    ],

    *,
    branch_offset: int,
    required_unique_variants: int,
) -> int:

    eligible_branch_ids = []


    for (
        branch_id,
        inventories,
    ) in inventories_by_branch.items():

        unique_variant_ids = {
            inventory.product_variant_id

            for inventory
            in inventories
        }


        if (
            len(
                unique_variant_ids
            )
            >=
            required_unique_variants
        ):

            eligible_branch_ids.append(
                branch_id
            )


    eligible_branch_ids.sort()


    if not eligible_branch_ids:

        raise RuntimeError(
            "No existe una sucursal con "
            "variantes suficientes para "
            "crear los carritos de prueba."
        )


    return eligible_branch_ids[
        branch_offset
        %
        len(
            eligible_branch_ids
        )
    ]


# =========================================================
# ASIGNAR SUCURSAL A CARRITO EXISTENTE
# =========================================================

def _ensure_existing_cart_branch(
    db: Session,

    *,
    cart: ShoppingCart,
    inventories_by_branch: dict[
        int,
        list[Inventory],
    ],
    branch_offset: int,
) -> bool:

    if (
        cart.branch_id
        is not None
    ):

        return False


    cart_items = list(
        db.scalars(
            select(
                CartItem
            )
            .where(
                CartItem.cart_id
                ==
                cart.id
            )
            .order_by(
                CartItem.id
            )
        ).all()
    )


    # Intentar encontrar una sucursal capaz de surtir
    # todas las variantes ya existentes del carrito.
    candidate_branch_ids = sorted(
        inventories_by_branch.keys()
    )


    for branch_id in candidate_branch_ids:

        inventories = (
            inventories_by_branch[
                branch_id
            ]
        )


        available_by_variant = {
            inventory.product_variant_id:
                (
                    inventory.stock_quantity
                    -
                    inventory.reserved_quantity
                )

            for inventory
            in inventories
        }


        if all(
            available_by_variant.get(
                item.product_variant_id,
                0,
            )
            >=
            item.quantity

            for item
            in cart_items
        ):

            cart.branch_id = (
                branch_id
            )

            return True


    # Si los datos antiguos mezclaban variantes de distintas
    # sucursales, asignamos una sucursal válida del seed para
    # normalizar el registro de prueba.
    selected_branch_id = (
        _choose_branch_id(
            inventories_by_branch,

            branch_offset=
                branch_offset,

            required_unique_variants=
                max(
                    1,
                    len(
                        cart_items
                    ),
                ),
        )
    )


    cart.branch_id = (
        selected_branch_id
    )

    return True


# =========================================================
# SEED
# =========================================================

def seed_carts(
    db: Session,
) -> None:

    print(
        "🌱 Seed carritos..."
    )


    inventories_by_branch = (
        _get_inventories_by_branch(
            db
        )
    )


    created_carts = 0

    existing_carts = 0

    updated_carts = 0

    created_items = 0


    for scenario in CART_SCENARIOS:

        customer = (
            _get_customer(
                db,
                scenario[
                    "email"
                ],
            )
        )


        # =================================================
        # IDEMPOTENCIA
        # =================================================

        cart = db.scalar(
            select(
                ShoppingCart
            )
            .where(
                ShoppingCart.customer_id
                ==
                customer.id,
                ShoppingCart.status
                ==
                scenario[
                    "status"
                ],
            )
            .order_by(
                ShoppingCart.id
            )
        )


        if cart is not None:

            existing_carts += 1


            if (
                _ensure_existing_cart_branch(
                    db,

                    cart=
                        cart,

                    inventories_by_branch=
                        inventories_by_branch,

                    branch_offset=
                        scenario[
                            "branch_offset"
                        ],
                )
            ):

                updated_carts += 1


            continue


        # =================================================
        # SUCURSAL
        # =================================================

        branch_id = (
            _choose_branch_id(
                inventories_by_branch,

                branch_offset=
                    scenario[
                        "branch_offset"
                    ],

                required_unique_variants=
                    len(
                        scenario[
                            "quantities"
                        ]
                    ),
            )
        )


        branch_inventories = (
            inventories_by_branch[
                branch_id
            ]
        )


        # =================================================
        # CREAR CARRITO
        # =================================================

        cart = ShoppingCart(
            customer_id=
                customer.id,

            branch_id=
                branch_id,

            status=
                scenario[
                    "status"
                ],
        )


        db.add(
            cart
        )


        db.flush()


        created_carts += 1


        used_variant_ids: set[
            int
        ] = set()


        inventory_index = 0


        # =================================================
        # CREAR ITEMS
        # =================================================

        for quantity in (
            scenario[
                "quantities"
            ]
        ):

            found_inventory = None

            attempts = 0


            while (
                attempts
                <
                len(
                    branch_inventories
                )
            ):

                inventory = (
                    branch_inventories[
                        inventory_index
                        %
                        len(
                            branch_inventories
                        )
                    ]
                )


                inventory_index += 1

                attempts += 1


                if (
                    inventory.product_variant_id
                    in
                    used_variant_ids
                ):

                    continue


                available = (
                    inventory.stock_quantity
                    -
                    inventory.reserved_quantity
                )


                if (
                    available
                    <
                    quantity
                ):

                    continue


                found_inventory = (
                    inventory
                )

                break


            if (
                found_inventory
                is None
            ):

                raise RuntimeError(
                    "No se encontró una variante "
                    "con stock suficiente en la "
                    f"sucursal {branch_id} para "
                    "el carrito."
                )


            used_variant_ids.add(
                found_inventory
                .product_variant_id
            )


            item = CartItem(
                cart_id=
                    cart.id,

                product_variant_id=
                    found_inventory
                    .product_variant_id,

                quantity=
                    quantity,
            )


            db.add(
                item
            )


            created_items += 1


    db.flush()


    print(
        "✅ Carritos listos: "
        f"{created_carts} creados, "
        f"{existing_carts} ya existentes, "
        f"{updated_carts} actualizados con sucursal, "
        f"{created_items} items creados."
    )


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================

if __name__ == "__main__":

    from app.database.session import (
        SessionLocal,
    )

    from app.database.seeds.seed_customers import (
        seed_customers,
    )


    db = SessionLocal()


    try:

        seed_customers(
            db
        )


        seed_carts(
            db
        )


        db.commit()


    except Exception:

        db.rollback()

        raise


    finally:

        db.close()
