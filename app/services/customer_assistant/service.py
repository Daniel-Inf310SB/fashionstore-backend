from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.audience import Audience
from app.models.branch import Branch
from app.models.category import Category
from app.models.color import Color
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.reservation import Reservation
from app.models.reservation_item import ReservationItem
from app.models.size import Size
from app.models.user import User
from app.schemas.cart import CartResponse
from app.schemas.reservation import ReservationResponse

from app.schemas.customer_assistant import (
    CustomerAssistantContext,
    CustomerAssistantExecuteRequest,
    CustomerAssistantNavigation,
    CustomerAssistantResolvedCommand,
)
from app.schemas.reservation import ReservationAddItems, ReservationItemCreate
from app.services.ai.openai_service import OpenAIService
from app.services.cart_service import CartService
from app.services.customer_assistant.prompt import CustomerAssistantPrompt
from app.services.order_service import OrderService
from app.services.reservation_service import ReservationService


class CustomerAssistantService:
    DESTRUCTIVE = {"CART_REMOVE", "CART_CLEAR", "RESERVATION_REMOVE", "RESERVATION_CANCEL"}

    @staticmethod
    def _first_by_name(db: Session, model, value: str | None):
        if not value:
            return None
        clean = value.strip()
        exact = db.query(model).filter(func.lower(model.name) == clean.lower()).first()
        if exact is not None:
            return exact
        matches = db.query(model).filter(model.name.ilike(f"%{clean}%")).limit(3).all()
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _find_product(db: Session, name: str | None, code: str | None):
        if code:
            product = db.query(Product).filter(func.lower(Product.code) == code.strip().lower(), Product.is_active.is_(True)).first()
            if product:
                return product
        if not name:
            return None
        clean = name.strip()
        exact = db.query(Product).filter(func.lower(Product.name) == clean.lower(), Product.is_active.is_(True)).first()
        if exact:
            return exact
        matches = db.query(Product).filter(Product.name.ilike(f"%{clean}%"), Product.is_active.is_(True)).limit(3).all()
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _resolve_variant(db: Session, entities: dict[str, Any], context: CustomerAssistantContext):
        if context.variant_id:
            variant = db.query(ProductVariant).filter(ProductVariant.id == context.variant_id, ProductVariant.is_active.is_(True)).first()
            if variant:
                return variant

        product = CustomerAssistantService._find_product(db, entities.get("product_name"), entities.get("product_code"))
        if not product:
            return None

        q = db.query(ProductVariant).filter(ProductVariant.product_id == product.id, ProductVariant.is_active.is_(True))
        size = CustomerAssistantService._first_by_name(db, Size, entities.get("size_name"))
        color = CustomerAssistantService._first_by_name(db, Color, entities.get("color_name"))
        if size:
            q = q.filter(ProductVariant.size_id == size.id)
        if color:
            q = q.filter(ProductVariant.color_id == color.id)
        variants = q.limit(3).all()
        return variants[0] if len(variants) == 1 else None

    @staticmethod
    def _active_cart_item(db: Session, user: User, branch_id: int, context: CustomerAssistantContext, entities: dict[str, Any]):
        cart_data = CartService.get_my_cart(db, customer_id=user.id, branch_id=branch_id)
        cart = cart_data.get("cart")
        if not cart:
            return None
        if context.cart_item_id:
            return next((i for i in cart["items"] if i["id"] == context.cart_item_id), None)
        variant = CustomerAssistantService._resolve_variant(db, entities, context)
        if variant:
            return next((i for i in cart["items"] if i["product_variant_id"] == variant.id), None)
        pname = (entities.get("product_name") or "").strip().lower()
        if pname:
            matches = [i for i in cart["items"] if pname in i["product_variant"].product.name.lower()]
            return matches[0] if len(matches) == 1 else None
        return None

    @staticmethod
    def _reservation_for_user(db: Session, user: User, context: CustomerAssistantContext, code: str | None, pending_only: bool = False):
        q = db.query(Reservation).filter(Reservation.customer_id == user.id)
        if context.reservation_id:
            q = q.filter(Reservation.id == context.reservation_id)
        elif code:
            q = q.filter(func.lower(Reservation.reservation_code) == code.strip().lower())
        elif context.branch_id and pending_only:
            q = q.filter(Reservation.branch_id == context.branch_id)
        if pending_only:
            q = q.filter(Reservation.status == "PENDING")
        else:
            q = q.filter(Reservation.status.in_(["PENDING", "CONFIRMED"]))
        rows = q.order_by(Reservation.id.desc()).limit(3).all()
        return rows[0] if len(rows) == 1 else None

    @staticmethod
    def interpret(db: Session, user: User, command: str, context: CustomerAssistantContext):
        parsed, usage = OpenAIService.generate_json(
            instructions=CustomerAssistantPrompt.instructions(),
            input_data={
                "command": command,
                "context": context.model_dump(),
            },
        )
        allowed_actions = {
            "NAVIGATE_HOME", "NAVIGATE_CATALOG", "NAVIGATE_CART", "NAVIGATE_ORDERS",
            "NAVIGATE_RESERVATIONS", "NAVIGATE_PRODUCT", "NAVIGATE_CHECKOUT", "SEARCH_CATALOG", "VIEW_CART",
            "VIEW_ORDERS", "VIEW_RESERVATIONS", "CART_ADD", "CART_INCREMENT",
            "CART_DECREMENT", "CART_SET_QUANTITY", "CART_REMOVE", "CART_CLEAR",
            "RESERVATION_ADD", "RESERVATION_SET_QUANTITY", "RESERVATION_REMOVE",
            "RESERVATION_CANCEL", "UNKNOWN",
        }
        action = str(parsed.get("action") or "UNKNOWN").upper()
        if action not in allowed_actions:
            action = "UNKNOWN"
        entities = parsed.get("entities") if isinstance(parsed.get("entities"), dict) else {}
        params: dict[str, Any] = {}
        unresolved: list[str] = []
        nav = None

        navigation_map = {
            "NAVIGATE_HOME": "HOME",
            "NAVIGATE_CATALOG": "CATALOG",
            "NAVIGATE_CART": "CART",
            "NAVIGATE_ORDERS": "ORDERS",
            "NAVIGATE_RESERVATIONS": "RESERVATIONS",
            "NAVIGATE_CHECKOUT": "CHECKOUT",
            "VIEW_CART": "CART",
            "VIEW_ORDERS": "ORDERS",
            "VIEW_RESERVATIONS": "RESERVATIONS",
        }
        if action in navigation_map:
            nav = CustomerAssistantNavigation(target=navigation_map[action])

        # "Ir a pagar" solamente prepara la navegación al checkout.
        # No crea, confirma ni ejecuta ningún pago.
        if action == "NAVIGATE_CHECKOUT":
            branch_id = context.branch_id

            if not branch_id:
                unresolved.append("sucursal")
                nav = None
            else:
                cart_data = CartService.get_my_cart(
                    db,
                    customer_id=user.id,
                    branch_id=branch_id,
                )
                cart = cart_data.get("cart")

                if isinstance(cart, dict):
                    cart_items = cart.get("items") or []
                else:
                    cart_items = getattr(cart, "items", None) or [] if cart else []

                if not cart or not cart_items:
                    unresolved.append("carrito con productos")
                    nav = None
                else:
                    params["branch_id"] = branch_id
                    nav = CustomerAssistantNavigation(
                        target="CHECKOUT",
                        query={"branch_id": branch_id},
                    )

        if action in {"SEARCH_CATALOG", "NAVIGATE_CATALOG"}:
            query: dict[str, Any] = {}
            if entities.get("search") or entities.get("product_name"):
                query["search"] = entities.get("search") or entities.get("product_name")
            if entities.get("category_name"):
                category = CustomerAssistantService._first_by_name(db, Category, entities.get("category_name"))
                if category:
                    query["category"] = category.name
                else:
                    unresolved.append("categoría")
            if entities.get("audience_name"):
                audience = CustomerAssistantService._first_by_name(db, Audience, entities.get("audience_name"))
                if audience:
                    query["audience"] = audience.name
                else:
                    unresolved.append("audiencia")
            if context.branch_id:
                query["branch_id"] = context.branch_id
            nav = CustomerAssistantNavigation(target="CATALOG", query=query)
            params["catalog_query"] = query

        if action == "NAVIGATE_PRODUCT":
            product = CustomerAssistantService._find_product(db, entities.get("product_name"), entities.get("product_code"))
            if not product:
                unresolved.append("producto")
            else:
                params["product_id"] = product.id
                nav = CustomerAssistantNavigation(target="PRODUCT", params={"product_id": product.id})

        if action.startswith("CART_"):
            branch_id = context.branch_id
            if not branch_id:
                unresolved.append("sucursal")
            else:
                params["branch_id"] = branch_id

            if action == "CART_ADD":
                variant = CustomerAssistantService._resolve_variant(db, entities, context)
                if not variant:
                    unresolved.append("variante del producto")
                else:
                    params["product_variant_id"] = variant.id
                    params["quantity"] = max(1, int(entities.get("quantity") or 1))

            if action in {"CART_INCREMENT", "CART_DECREMENT", "CART_SET_QUANTITY", "CART_REMOVE"} and branch_id:
                item = CustomerAssistantService._active_cart_item(db, user, branch_id, context, entities)
                if not item:
                    unresolved.append("producto del carrito")
                else:
                    params["item_id"] = item["id"]
                    params["current_quantity"] = item["quantity"]
                    qty = max(1, int(entities.get("quantity") or 1))
                    if action == "CART_INCREMENT":
                        params["quantity"] = item["quantity"] + qty
                    elif action == "CART_DECREMENT":
                        params["quantity"] = max(1, item["quantity"] - qty)
                    elif action == "CART_SET_QUANTITY":
                        params["quantity"] = qty

        if action.startswith("RESERVATION_"):
            pending_only = action in {"RESERVATION_ADD", "RESERVATION_SET_QUANTITY", "RESERVATION_REMOVE"}
            reservation = CustomerAssistantService._reservation_for_user(
                db, user, context, entities.get("reservation_code"), pending_only=pending_only
            )
            if not reservation:
                unresolved.append("reserva")
            else:
                params["reservation_id"] = reservation.id
                if action == "RESERVATION_ADD":
                    variant = CustomerAssistantService._resolve_variant(db, entities, context)
                    if not variant:
                        unresolved.append("variante del producto")
                    else:
                        params["product_variant_id"] = variant.id
                        params["quantity"] = max(1, int(entities.get("quantity") or 1))
                elif action in {"RESERVATION_SET_QUANTITY", "RESERVATION_REMOVE"}:
                    item = None
                    if context.variant_id:
                        item = db.query(ReservationItem).filter(
                            ReservationItem.reservation_id == reservation.id,
                            ReservationItem.product_variant_id == context.variant_id,
                        ).first()
                    if item is None:
                        variant = CustomerAssistantService._resolve_variant(db, entities, context)
                        if variant:
                            item = db.query(ReservationItem).filter(
                                ReservationItem.reservation_id == reservation.id,
                                ReservationItem.product_variant_id == variant.id,
                            ).first()
                    if not item:
                        unresolved.append("producto de la reserva")
                    else:
                        params["reservation_item_id"] = item.id
                        if action == "RESERVATION_SET_QUANTITY":
                            params["quantity"] = max(1, int(entities.get("quantity") or 1))

        can_execute = action != "UNKNOWN" and not unresolved
        requires_confirmation = action in CustomerAssistantService.DESTRUCTIVE
        confirmation_message = None
        if requires_confirmation and can_execute:
            confirmation_message = {
                "CART_REMOVE": "¿Confirmas que deseas quitar este producto del carrito?",
                "CART_CLEAR": "¿Confirmas que deseas vaciar todo tu carrito?",
                "RESERVATION_REMOVE": "¿Confirmas que deseas quitar este producto de la reserva pendiente?",
                "RESERVATION_CANCEL": "¿Confirmas que deseas cancelar esta reserva?",
            }[action]

        if action == "UNKNOWN":
            message = "No pude interpretar ese comando con suficiente seguridad."
        elif action == "NAVIGATE_CHECKOUT" and "sucursal" in unresolved:
            message = "Selecciona una sucursal antes de continuar al pago."
        elif action == "NAVIGATE_CHECKOUT" and "carrito con productos" in unresolved:
            message = "Tu carrito está vacío. Agrega productos antes de continuar al pago."
        elif action == "NAVIGATE_CHECKOUT" and not unresolved:
            message = "Tu carrito está listo. Te llevaré al proceso de pago."
        elif unresolved:
            message = "Necesito precisar: " + ", ".join(unresolved) + "."
        else:
            message = str(parsed.get("message") or "Comando interpretado correctamente.")

        result = CustomerAssistantResolvedCommand(
            action=action,
            message=message,
            can_execute=can_execute,
            requires_confirmation=requires_confirmation,
            confirmation_message=confirmation_message,
            navigation=nav,
            params=params,
            unresolved=unresolved,
        )
        return result, usage

    @staticmethod
    def execute(db: Session, user: User, data: CustomerAssistantExecuteRequest):
        action = data.action
        p = data.params
        if action in CustomerAssistantService.DESTRUCTIVE and not data.confirmed:
            raise PermissionError("Esta acción requiere confirmación explícita del cliente.")

        if action in {"NAVIGATE_HOME", "NAVIGATE_CATALOG", "NAVIGATE_CART", "NAVIGATE_ORDERS", "NAVIGATE_RESERVATIONS", "NAVIGATE_PRODUCT", "NAVIGATE_CHECKOUT", "SEARCH_CATALOG", "VIEW_CART", "VIEW_ORDERS", "VIEW_RESERVATIONS"}:
            return {"message": "Acción de navegación lista para el frontend.", "data": None}

        if action == "CART_ADD":
            cart = CartService.add_item(db, customer_id=user.id, branch_id=int(p["branch_id"]), product_variant_id=int(p["product_variant_id"]), quantity=int(p.get("quantity", 1)))
            return {"message": "Producto agregado al carrito.", "data": CartResponse.model_validate(cart).model_dump(mode="json")}
        if action in {"CART_INCREMENT", "CART_DECREMENT", "CART_SET_QUANTITY"}:
            cart = CartService.update_item_quantity(db, customer_id=user.id, item_id=int(p["item_id"]), quantity=int(p["quantity"]))
            return {"message": "Cantidad del carrito actualizada.", "data": CartResponse.model_validate(cart).model_dump(mode="json")}
        if action == "CART_REMOVE":
            cart = CartService.remove_item(db, customer_id=user.id, item_id=int(p["item_id"]))
            return {"message": "Producto eliminado del carrito.", "data": CartResponse.model_validate(cart).model_dump(mode="json")}
        if action == "CART_CLEAR":
            result = CartService.clear_my_cart(db, customer_id=user.id, branch_id=int(p["branch_id"]))
            return {"message": result["message"], "data": result}

        if action == "RESERVATION_ADD":
            payload = ReservationAddItems(items=[ReservationItemCreate(product_variant_id=int(p["product_variant_id"]), quantity=int(p.get("quantity", 1)))])
            result = ReservationService.add_items_to_pending_reservation(db, reservation_id=int(p["reservation_id"]), data=payload, current_user=user)
            return {"message": "Producto agregado a la reserva pendiente.", "data": ReservationResponse.model_validate(result).model_dump(mode="json")}
        if action == "RESERVATION_SET_QUANTITY":
            result = ReservationService.update_pending_item_quantity(db, reservation_id=int(p["reservation_id"]), reservation_item_id=int(p["reservation_item_id"]), quantity=int(p["quantity"]), current_user=user)
            return {"message": "Cantidad de la reserva actualizada.", "data": ReservationResponse.model_validate(result).model_dump(mode="json")}
        if action == "RESERVATION_REMOVE":
            result = ReservationService.remove_pending_item(db, reservation_id=int(p["reservation_id"]), reservation_item_id=int(p["reservation_item_id"]), current_user=user)
            return {"message": "Producto eliminado de la reserva pendiente.", "data": ReservationResponse.model_validate(result).model_dump(mode="json")}
        if action == "RESERVATION_CANCEL":
            result = ReservationService.cancel_reservation(db, reservation_id=int(p["reservation_id"]), current_user=user, reason="Cancelada mediante asistente de FashionStore.")
            return {"message": "Reserva cancelada correctamente.", "data": ReservationResponse.model_validate(result).model_dump(mode="json")}

        raise ValueError("Acción no soportada por el asistente.")
