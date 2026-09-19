from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AIUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class AIRecommendationRequest(BaseModel):
    branch_id: int
    prompt: str = Field(min_length=3, max_length=600)
    size: str | None = Field(default=None, max_length=30)
    category: str | None = Field(default=None, max_length=100)
    max_budget: Decimal | None = Field(default=None, ge=0)
    limit: int = Field(default=5, ge=1, le=8)


class AIProductRecommendation(BaseModel):
    product_id: int
    variant_id: int | None = None
    name: str
    reason: str


class AIRecommendationResponse(BaseModel):
    message: str
    recommendations: list[AIProductRecommendation]
    usage: AIUsage | None = None


class AIAssistantRequest(BaseModel):
    branch_id: int
    message: str = Field(min_length=2, max_length=800)
    max_products: int = Field(default=8, ge=1, le=12)


class AIAssistantProduct(BaseModel):
    product_id: int
    variant_id: int | None = None
    name: str


class AIAssistantResponse(BaseModel):
    message: str
    products: list[AIAssistantProduct] = []
    usage: AIUsage | None = None


class AIReportRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)
    branch_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date no puede ser mayor que end_date.")
        return self


class AIReportResponse(BaseModel):
    title: str
    summary: str
    findings: list[str]
    recommendations: list[str]
    period: dict[str, str]
    branch_id: int | None
    data: dict[str, Any]
    usage: AIUsage | None = None


class AIVirtualTryOnResponse(BaseModel):
    message: str
    product_id: int
    variant_id: int
    sku: str
    product_name: str
    color: str
    size: str
    garment_image_url: str
    generated_image_url: str
    generated_image_public_id: str
    generated_image_width: int | None = None
    generated_image_height: int | None = None
    output_format: str
    output_content_type: str
    usage: AIUsage | None = None
