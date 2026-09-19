from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AssistantAction = Literal[
    "NAVIGATE_HOME",
    "NAVIGATE_CATALOG",
    "NAVIGATE_CART",
    "NAVIGATE_ORDERS",
    "NAVIGATE_RESERVATIONS",
    "NAVIGATE_PRODUCT",
    "NAVIGATE_CHECKOUT",
    "SEARCH_CATALOG",
    "VIEW_CART",
    "VIEW_ORDERS",
    "VIEW_RESERVATIONS",
    "CART_ADD",
    "CART_INCREMENT",
    "CART_DECREMENT",
    "CART_SET_QUANTITY",
    "CART_REMOVE",
    "CART_CLEAR",
    "RESERVATION_ADD",
    "RESERVATION_SET_QUANTITY",
    "RESERVATION_REMOVE",
    "RESERVATION_CANCEL",
    "UNKNOWN",
]


class CustomerAssistantContext(BaseModel):
    current_page: str | None = Field(default=None, max_length=80)
    branch_id: int | None = Field(default=None, ge=1)
    product_id: int | None = Field(default=None, ge=1)
    variant_id: int | None = Field(default=None, ge=1)
    cart_item_id: int | None = Field(default=None, ge=1)
    reservation_id: int | None = Field(default=None, ge=1)


class CustomerAssistantInterpretRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=700)
    context: CustomerAssistantContext = Field(default_factory=CustomerAssistantContext)


class CustomerAssistantNavigation(BaseModel):
    target: Literal["HOME", "CATALOG", "CART", "ORDERS", "RESERVATIONS", "PRODUCT", "CHECKOUT"]
    params: dict[str, Any] = Field(default_factory=dict)
    query: dict[str, Any] = Field(default_factory=dict)


class CustomerAssistantResolvedCommand(BaseModel):
    action: AssistantAction
    message: str
    can_execute: bool
    requires_confirmation: bool = False
    confirmation_message: str | None = None
    navigation: CustomerAssistantNavigation | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    unresolved: list[str] = Field(default_factory=list)


class CustomerAssistantInterpretResponse(BaseModel):
    command: str
    result: CustomerAssistantResolvedCommand
    usage: dict[str, int | None] | None = None


class CustomerAssistantExecuteRequest(BaseModel):
    action: AssistantAction
    params: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False


class CustomerAssistantExecuteResponse(BaseModel):
    action: AssistantAction
    message: str
    data: dict[str, Any] | list[Any] | None = None
    navigation: CustomerAssistantNavigation | None = None
