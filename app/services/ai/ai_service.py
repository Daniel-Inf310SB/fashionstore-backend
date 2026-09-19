from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.schemas.ai import AIAssistantRequest, AIRecommendationRequest, AIReportRequest
from app.services.ai.context_service import AIContextService
from app.services.ai.openai_service import OpenAIService


class AIService:
    @staticmethod
    def recommendations(db: Session, data: AIRecommendationRequest) -> dict:
        products = AIContextService.catalog_context(
            db,
            branch_id=data.branch_id,
            query_text=data.prompt,
            size=data.size,
            category=data.category,
            max_budget=data.max_budget,
            limit=settings.ai_recommendation_context_limit,
            candidate_pool=settings.ai_catalog_candidate_pool,
        )

        if not products:
            return {
                "message": "No encontré prendas disponibles que cumplan esos filtros.",
                "recommendations": [],
                "usage": None,
            }

        result, usage = OpenAIService.generate_json(
            instructions=(
                "Eres el recomendador de FashionStore. Responde SOLO JSON válido. "
                "La lista ya fue preseleccionada por disponibilidad y relevancia. "
                "Usa exclusivamente productos del catálogo recibido; no inventes IDs, precios, stock, tallas ni prendas. "
                "Prioriza la intención del cliente, ocasión, estilo, presupuesto y coincidencias explícitas. "
                "Devuelve {message:string,recommendations:[{product_id:int,variant_id:int,name:string,reason:string}]}. "
                "No repitas la misma variante. Máximo el número solicitado. Sé breve y útil."
            ),
            input_data={
                "request": {
                    "prompt": data.prompt,
                    "size": data.size,
                    "category": data.category,
                    "max_budget": str(data.max_budget) if data.max_budget is not None else None,
                    "limit": data.limit,
                },
                "candidate_products": products,
            },
        )

        valid_ids = {(p["product_id"], p["variant_id"]): p for p in products}
        recommendations = []
        seen: set[tuple[int, int]] = set()
        for item in result.get("recommendations", []):
            key = (item.get("product_id"), item.get("variant_id"))
            product = valid_ids.get(key)
            if product is None or key in seen:
                continue
            seen.add(key)
            recommendations.append({
                "product_id": product["product_id"],
                "variant_id": product["variant_id"],
                "name": product["name"],
                "reason": str(item.get("reason") or "Recomendación basada en tus preferencias.")[:300],
            })
            if len(recommendations) >= data.limit:
                break

        return {
            "message": str(result.get("message") or "Estas son mis recomendaciones.")[:800],
            "recommendations": recommendations,
            "usage": usage,
        }

    @staticmethod
    def assistant(db: Session, data: AIAssistantRequest) -> dict:
        products = AIContextService.assistant_catalog_context(
            db,
            branch_id=data.branch_id,
            message=data.message,
            limit=settings.ai_assistant_context_limit,
        )

        result, usage = OpenAIService.generate_json(
            instructions=(
                "Eres el asistente de moda de FashionStore. Responde SOLO JSON válido. "
                "Puedes orientar sobre combinaciones, ocasiones, estilo, tallas y presupuesto. "
                "Cuando afirmes disponibilidad, precio, talla, color o existencia de un producto de FashionStore, "
                "usa únicamente candidate_products. Si no hay coincidencia suficiente, dilo y ofrece alternativas generales "
                "sin inventar catálogo. Devuelve {message:string,products:[{product_id:int,variant_id:int,name:string}]}. "
                "No repitas variantes y no devuelvas más productos que max_products_to_return."
            ),
            input_data={
                "message": data.message,
                "candidate_products": products,
                "max_products_to_return": data.max_products,
            },
        )

        valid_ids = {(p["product_id"], p["variant_id"]): p for p in products}
        selected = []
        seen: set[tuple[int, int]] = set()
        for item in result.get("products", []):
            key = (item.get("product_id"), item.get("variant_id"))
            product = valid_ids.get(key)
            if product is None or key in seen:
                continue
            seen.add(key)
            selected.append({
                "product_id": product["product_id"],
                "variant_id": product["variant_id"],
                "name": product["name"],
            })
            if len(selected) >= data.max_products:
                break

        return {
            "message": str(result.get("message") or "No pude generar una respuesta.")[:1200],
            "products": selected,
            "usage": usage,
        }

    @staticmethod
    def intelligent_report(db: Session, current_user: User, data: AIReportRequest) -> dict:
        branch_id = AIContextService.resolve_report_branch(
            db,
            current_user=current_user,
            requested_branch_id=data.branch_id,
        )

        metrics, start_date, end_date = AIContextService.report_context(
            db,
            branch_id=branch_id,
            start_date=data.start_date,
            end_date=data.end_date,
            detail_limit=settings.ai_report_detail_limit,
        )

        result, usage = OpenAIService.generate_json(
            instructions=(
                "Eres analista de negocio de FashionStore. Responde SOLO JSON válido. "
                "Analiza exclusivamente las métricas recibidas: nunca inventes cifras, productos, tendencias ni causas. "
                "Puedes describir comparaciones solo cuando existan datos comparables. Si revenue_change_pct es null, "
                "explica que no existe una base anterior distinta de cero en vez de afirmar un porcentaje. "
                "zero_rotation_products significa stock disponible sin ventas efectivas en el periodo, no un diagnóstico histórico absoluto. "
                "Distingue hechos observados de recomendaciones operativas. "
                "Devuelve {title:string,summary:string,findings:[string],recommendations:[string]}. "
                "Máximo 8 hallazgos y 8 recomendaciones, concisos y accionables."
            ),
            input_data={
                "question": data.prompt,
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "metrics": metrics,
            },
        )

        return {
            "title": str(result.get("title") or "Reporte inteligente")[:160],
            "summary": str(result.get("summary") or "")[:2000],
            "findings": [str(x)[:500] for x in result.get("findings", [])][:8],
            "recommendations": [str(x)[:500] for x in result.get("recommendations", [])][:8],
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "branch_id": branch_id,
            "data": metrics,
            "usage": usage,
        }
