from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.collection import Collection
from app.models.product import Product
from app.models.product_collection import ProductCollection
from app.models.product_promotion import ProductPromotion
from app.models.product_season import ProductSeason
from app.models.promotion import Promotion
from app.models.season import Season

from app.services.audit_log_service import (
    AuditLogService,
)


class ProductAssociationService:

    # =====================================================
    # VALIDAR PRODUCTO
    # =====================================================

    @staticmethod
    def _get_product(
        db: Session,
        product_id: int,
    ) -> Product:

        product = db.get(
            Product,
            product_id,
        )

        if product is None:
            raise LookupError(
                "Producto no encontrado."
            )

        return product


    # =====================================================
    # VALIDAR TEMPORADA
    # =====================================================

    @staticmethod
    def _get_active_season(
        db: Session,
        season_id: int,
    ) -> Season:

        season = db.get(
            Season,
            season_id,
        )

        if season is None:
            raise LookupError(
                "Temporada no encontrada."
            )

        if not season.is_active:
            raise ValueError(
                "La temporada seleccionada está inactiva."
            )

        return season


    # =====================================================
    # VALIDAR COLECCIÓN
    # =====================================================

    @staticmethod
    def _get_active_collection(
        db: Session,
        collection_id: int,
    ) -> Collection:

        collection = db.get(
            Collection,
            collection_id,
        )

        if collection is None:
            raise LookupError(
                "Colección no encontrada."
            )

        if not collection.is_active:
            raise ValueError(
                "La colección seleccionada está inactiva."
            )

        return collection


    # =====================================================
    # VALIDAR PROMOCIÓN
    # =====================================================

    @staticmethod
    def _get_active_promotion(
        db: Session,
        promotion_id: int,
    ) -> Promotion:

        promotion = db.get(
            Promotion,
            promotion_id,
        )

        if promotion is None:
            raise LookupError(
                "Promoción no encontrada."
            )

        if not promotion.is_active:
            raise ValueError(
                "La promoción seleccionada está inactiva."
            )

        return promotion


    # =====================================================
    # LISTAR TODAS
    # =====================================================

    @staticmethod
    def get_associations(
        db: Session,
        product_id: int,
    ) -> dict:

        ProductAssociationService._get_product(
            db=db,
            product_id=product_id,
        )

        seasons = (
            db.query(ProductSeason)
            .options(
                joinedload(
                    ProductSeason.season
                )
            )
            .filter(
                ProductSeason.product_id
                == product_id
            )
            .order_by(
                ProductSeason.id.asc()
            )
            .all()
        )

        collections = (
            db.query(ProductCollection)
            .options(
                joinedload(
                    ProductCollection.collection
                )
            )
            .filter(
                ProductCollection.product_id
                == product_id
            )
            .order_by(
                ProductCollection.id.asc()
            )
            .all()
        )

        promotions = (
            db.query(ProductPromotion)
            .options(
                joinedload(
                    ProductPromotion.promotion
                )
            )
            .filter(
                ProductPromotion.product_id
                == product_id
            )
            .order_by(
                ProductPromotion.id.asc()
            )
            .all()
        )

        return {
            "seasons": seasons,
            "collections": collections,
            "promotions": promotions,
        }


    # =====================================================
    # ASOCIAR TEMPORADA
    # =====================================================

    @staticmethod
    def add_season(
        db: Session,
        product_id: int,
        season_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProductSeason:

        product = (
            ProductAssociationService
            ._get_product(
                db=db,
                product_id=product_id,
            )
        )

        season = (
            ProductAssociationService
            ._get_active_season(
                db=db,
                season_id=season_id,
            )
        )

        existing = (
            db.query(ProductSeason)
            .filter(
                ProductSeason.product_id
                == product_id,
                ProductSeason.season_id
                == season_id,
            )
            .first()
        )

        if existing is not None:
            raise ValueError(
                "El producto ya está asociado "
                "a esta temporada."
            )

        link = ProductSeason(
            product_id=product_id,
            season_id=season_id,
        )

        db.add(link)

        db.flush()

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="ASSIGN_PRODUCT_SEASON",
            module="CATALOG",
            entity_type="ProductSeason",
            entity_id=link.id,
            description=(
                f"Se asoció el producto "
                f"'{product.name}' con la temporada "
                f"'{season.name}'."
            ),
            old_values=None,
            new_values={
                "product_id":
                    product_id,
                "season_id":
                    season_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        return (
            db.query(ProductSeason)
            .options(
                joinedload(
                    ProductSeason.season
                )
            )
            .filter(
                ProductSeason.id
                == link.id
            )
            .first()
        )


    # =====================================================
    # QUITAR TEMPORADA
    # =====================================================

    @staticmethod
    def remove_season(
        db: Session,
        product_id: int,
        season_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:

        product = (
            ProductAssociationService
            ._get_product(
                db=db,
                product_id=product_id,
            )
        )

        link = (
            db.query(ProductSeason)
            .filter(
                ProductSeason.product_id
                == product_id,
                ProductSeason.season_id
                == season_id,
            )
            .first()
        )

        if link is None:
            raise LookupError(
                "La asociación con la temporada "
                "no existe."
            )

        link_id = link.id

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="REMOVE_PRODUCT_SEASON",
            module="CATALOG",
            entity_type="ProductSeason",
            entity_id=link_id,
            description=(
                f"Se quitó una temporada del "
                f"producto '{product.name}'."
            ),
            old_values={
                "product_id":
                    product_id,
                "season_id":
                    season_id,
            },
            new_values=None,
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.delete(link)

        db.commit()


    # =====================================================
    # ASOCIAR COLECCIÓN
    # =====================================================

    @staticmethod
    def add_collection(
        db: Session,
        product_id: int,
        collection_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProductCollection:

        product = (
            ProductAssociationService
            ._get_product(
                db=db,
                product_id=product_id,
            )
        )

        collection = (
            ProductAssociationService
            ._get_active_collection(
                db=db,
                collection_id=collection_id,
            )
        )

        existing = (
            db.query(ProductCollection)
            .filter(
                ProductCollection.product_id
                == product_id,
                ProductCollection.collection_id
                == collection_id,
            )
            .first()
        )

        if existing is not None:
            raise ValueError(
                "El producto ya está asociado "
                "a esta colección."
            )

        link = ProductCollection(
            product_id=product_id,
            collection_id=collection_id,
        )

        db.add(link)

        db.flush()

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="ASSIGN_PRODUCT_COLLECTION",
            module="CATALOG",
            entity_type="ProductCollection",
            entity_id=link.id,
            description=(
                f"Se asoció el producto "
                f"'{product.name}' con la colección "
                f"'{collection.name}'."
            ),
            old_values=None,
            new_values={
                "product_id":
                    product_id,
                "collection_id":
                    collection_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        return (
            db.query(ProductCollection)
            .options(
                joinedload(
                    ProductCollection.collection
                )
            )
            .filter(
                ProductCollection.id
                == link.id
            )
            .first()
        )


    # =====================================================
    # QUITAR COLECCIÓN
    # =====================================================

    @staticmethod
    def remove_collection(
        db: Session,
        product_id: int,
        collection_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:

        product = (
            ProductAssociationService
            ._get_product(
                db=db,
                product_id=product_id,
            )
        )

        link = (
            db.query(ProductCollection)
            .filter(
                ProductCollection.product_id
                == product_id,
                ProductCollection.collection_id
                == collection_id,
            )
            .first()
        )

        if link is None:
            raise LookupError(
                "La asociación con la colección "
                "no existe."
            )

        link_id = link.id

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="REMOVE_PRODUCT_COLLECTION",
            module="CATALOG",
            entity_type="ProductCollection",
            entity_id=link_id,
            description=(
                f"Se quitó una colección del "
                f"producto '{product.name}'."
            ),
            old_values={
                "product_id":
                    product_id,
                "collection_id":
                    collection_id,
            },
            new_values=None,
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.delete(link)

        db.commit()


    # =====================================================
    # ASOCIAR PROMOCIÓN
    # =====================================================

    @staticmethod
    def add_promotion(
        db: Session,
        product_id: int,
        promotion_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProductPromotion:

        product = (
            ProductAssociationService
            ._get_product(
                db=db,
                product_id=product_id,
            )
        )

        promotion = (
            ProductAssociationService
            ._get_active_promotion(
                db=db,
                promotion_id=promotion_id,
            )
        )

        existing = (
            db.query(ProductPromotion)
            .filter(
                ProductPromotion.product_id
                == product_id,
                ProductPromotion.promotion_id
                == promotion_id,
            )
            .first()
        )

        if existing is not None:
            raise ValueError(
                "El producto ya está asociado "
                "a esta promoción."
            )

        link = ProductPromotion(
            product_id=product_id,
            promotion_id=promotion_id,
        )

        db.add(link)

        db.flush()

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="ASSIGN_PRODUCT_PROMOTION",
            module="CATALOG",
            entity_type="ProductPromotion",
            entity_id=link.id,
            description=(
                f"Se asoció el producto "
                f"'{product.name}' con la promoción "
                f"'{promotion.name}'."
            ),
            old_values=None,
            new_values={
                "product_id":
                    product_id,
                "promotion_id":
                    promotion_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        return (
            db.query(ProductPromotion)
            .options(
                joinedload(
                    ProductPromotion.promotion
                )
            )
            .filter(
                ProductPromotion.id
                == link.id
            )
            .first()
        )


    # =====================================================
    # QUITAR PROMOCIÓN
    # =====================================================

    @staticmethod
    def remove_promotion(
        db: Session,
        product_id: int,
        promotion_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:

        product = (
            ProductAssociationService
            ._get_product(
                db=db,
                product_id=product_id,
            )
        )

        link = (
            db.query(ProductPromotion)
            .filter(
                ProductPromotion.product_id
                == product_id,
                ProductPromotion.promotion_id
                == promotion_id,
            )
            .first()
        )

        if link is None:
            raise LookupError(
                "La asociación con la promoción "
                "no existe."
            )

        link_id = link.id

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="REMOVE_PRODUCT_PROMOTION",
            module="CATALOG",
            entity_type="ProductPromotion",
            entity_id=link_id,
            description=(
                f"Se quitó una promoción del "
                f"producto '{product.name}'."
            ),
            old_values={
                "product_id":
                    product_id,
                "promotion_id":
                    promotion_id,
            },
            new_values=None,
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.delete(link)

        db.commit()