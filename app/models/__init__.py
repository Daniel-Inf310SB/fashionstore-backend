# =========================================================
# MÓDULO 1 - USUARIOS, ROLES Y PERMISOS
# =========================================================

from app.models.role_permission import role_permissions
from app.models.role import Role
from app.models.permission import Permission
from app.models.user import User
from app.models.email_verification_code import EmailVerificationCode
from app.models.user_device import UserDevice
from app.models.user_session import UserSession
from app.models.password_reset_code import PasswordResetCode
from app.models.audit_log import AuditLog


# =========================================================
# MÓDULO 2 - CIUDADES, SUCURSALES Y PERSONAL
# =========================================================

from app.models.city import City
from app.models.branch import Branch
from app.models.employee_branch import EmployeeBranch


# =========================================================
# MÓDULO 3 - CATÁLOGO
# =========================================================

from app.models.category import Category
from app.models.audience import Audience
from app.models.size import Size
from app.models.color import Color
from app.models.season import Season
from app.models.collection import Collection
from app.models.promotion import Promotion

from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.models.virtual_fitting_asset import VirtualFittingAsset

from app.models.product_season import ProductSeason
from app.models.product_collection import ProductCollection
from app.models.product_promotion import ProductPromotion


# =========================================================
# MÓDULO 4 - PROVEEDORES
# =========================================================

from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.supplier_availability import SupplierAvailability


# =========================================================
# MÓDULO 5 - INVENTARIO
# =========================================================

from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement

# =========================================================
# MÓDULO 7 - RESERVAS
# =========================================================

from app.models.reservation import Reservation
from app.models.reservation_item import ReservationItem


# =========================================================
# MÓDULO 8 - CARRITO
# =========================================================

from app.models.shopping_cart import ShoppingCart
from app.models.cart_item import CartItem


# =========================================================
# MÓDULO 9 - COMPRAS DIGITALES
# =========================================================

from app.models.order import Order
from app.models.order_item import OrderItem


# =========================================================
# MÓDULO 10 - VENTAS PRESENCIALES
# =========================================================

from app.models.sale import Sale
from app.models.sale_item import SaleItem


# =========================================================
# MÓDULO 11 - PAGOS
# =========================================================

from app.models.payment import Payment


# =========================================================
# COMPROBANTES DE COMPRA
# =========================================================

from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem