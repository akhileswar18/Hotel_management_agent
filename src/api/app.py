"""
API Layer: FastAPI Application Setup

Main entry point for REST API.
All endpoints routed here, with global error handlers and middleware.
"""

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from src.application import AuthService, SalesService, InventoryService
from src.domain import Money, Order, Item


# ===== Request/Response Models =====

class LoginRequest(BaseModel):
    """Login request body."""
    username: str
    pin: str


class LoginResponse(BaseModel):
    """Login response."""
    user_id: str
    username: str
    role: str
    token: str


class CreateOrderRequest(BaseModel):
    """Create order request."""
    table_id: Optional[str] = None


class OrderItemRequest(BaseModel):
    """Add item to order request."""
    item_id: str
    quantity: int


class FinalizeOrderRequest(BaseModel):
    """Finalize order request."""
    payment_method: str  # CASH, CARD, VOUCHER
    paid_amount: float  # In rupees (will be converted to Money)


class ItemResponse(BaseModel):
    """Item response model."""
    id: str
    name: str
    category: str
    unit_price: float
    reorder_level: int
    stock_on_hand: int

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Order response model."""
    id: str
    table_id: Optional[str]
    status: str
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    receipt_number: Optional[str]
    finalized_at: Optional[str]

    class Config:
        from_attributes = True


# ===== FastAPI App Setup =====

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Hotel Management System - Phase 1",
        description="Offline-first POS and inventory system",
        version="0.1.0",
    )

    # CORS Middleware (allow Flet local connections)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:*", "127.0.0.1"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.1.0",
        }

    # ===== Auth Routes =====
    @app.post("/api/auth/login")
    async def login(request: LoginRequest) -> LoginResponse:
        """Login endpoint."""
        try:
            auth_service = AuthService()
            user, token = auth_service.login(request.username, request.pin)
            return LoginResponse(
                user_id=str(user.id),
                username=user.username,
                role=user.role.value,
                token=token,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
            )

    @app.post("/api/auth/logout")
    async def logout() -> dict:
        """Logout endpoint."""
        # TODO: Implement session invalidation
        return {"status": "logged_out"}

    @app.get("/api/auth/me")
    async def get_current_user() -> dict:
        """Get current user info."""
        # TODO: Extract from session/token
        return {"user_id": "current_user_id"}

    # ===== Sales Routes =====
    @app.post("/api/sales/orders")
    async def create_order(request: CreateOrderRequest) -> OrderResponse:
        """Create new order."""
        # TODO: Extract user from session
        from uuid import uuid4
        user_id = uuid4()

        try:
            sales_service = SalesService()
            order = sales_service.create_order(request.table_id, user_id)
            return OrderResponse(
                id=str(order.id),
                table_id=order.table_id,
                status=order.status.value,
                subtotal=order.subtotal.to_float(),
                discount_amount=order.discount_amount.to_float(),
                tax_amount=order.tax_amount.to_float(),
                total_amount=order.total_amount.to_float(),
                receipt_number=order.receipt_number,
                finalized_at=order.finalized_at.isoformat() if order.finalized_at else None,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @app.post("/api/sales/orders/{order_id}/items")
    async def add_item(order_id: str, request: OrderItemRequest) -> OrderResponse:
        """Add item to order."""
        from uuid import uuid4
        user_id = uuid4()

        try:
            sales_service = SalesService()
            order = sales_service.add_item(
                UUID(order_id),
                UUID(request.item_id),
                request.quantity,
                user_id,
            )
            return OrderResponse(
                id=str(order.id),
                table_id=order.table_id,
                status=order.status.value,
                subtotal=order.subtotal.to_float(),
                discount_amount=order.discount_amount.to_float(),
                tax_amount=order.tax_amount.to_float(),
                total_amount=order.total_amount.to_float(),
                receipt_number=order.receipt_number,
                finalized_at=order.finalized_at.isoformat() if order.finalized_at else None,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @app.post("/api/sales/orders/{order_id}/finalize")
    async def finalize_order(order_id: str, request: FinalizeOrderRequest) -> OrderResponse:
        """Finalize order and process payment."""
        from uuid import uuid4
        user_id = uuid4()

        try:
            sales_service = SalesService()
            from src.domain import PaymentMethod
            order = sales_service.finalize_order(
                UUID(order_id),
                PaymentMethod(request.payment_method),
                Money.from_float(request.paid_amount),
                user_id,
            )
            return OrderResponse(
                id=str(order.id),
                table_id=order.table_id,
                status=order.status.value,
                subtotal=order.subtotal.to_float(),
                discount_amount=order.discount_amount.to_float(),
                tax_amount=order.tax_amount.to_float(),
                total_amount=order.total_amount.to_float(),
                receipt_number=order.receipt_number,
                finalized_at=order.finalized_at.isoformat() if order.finalized_at else None,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @app.get("/api/sales/orders/{order_id}")
    async def get_order(order_id: str) -> OrderResponse:
        """Get order details."""
        try:
            sales_service = SalesService()
            order = sales_service.order_repo.get(order_id)
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            return OrderResponse(
                id=str(order.id),
                table_id=order.table_id,
                status=order.status.value,
                subtotal=order.subtotal.to_float(),
                discount_amount=order.discount_amount.to_float(),
                tax_amount=order.tax_amount.to_float(),
                total_amount=order.total_amount.to_float(),
                receipt_number=order.receipt_number,
                finalized_at=order.finalized_at.isoformat() if order.finalized_at else None,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    # ===== Inventory Routes =====
    @app.get("/api/inventory/items")
    async def list_items() -> List[ItemResponse]:
        """List all items with stock on hand."""
        try:
            inventory_service = InventoryService()
            items = inventory_service.item_repo.list()
            result = []
            for item in items:
                stock = inventory_service.get_stock_on_hand(item.id)
                result.append(ItemResponse(
                    id=str(item.id),
                    name=item.name,
                    category=item.category,
                    unit_price=item.unit_price.to_float(),
                    reorder_level=item.reorder_level,
                    stock_on_hand=stock,
                ))
            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @app.get("/api/inventory/items/{item_id}")
    async def get_item(item_id: str) -> ItemResponse:
        """Get item details with stock."""
        try:
            inventory_service = InventoryService()
            item = inventory_service.item_repo.get(item_id)
            if not item:
                raise HTTPException(status_code=404, detail="Item not found")
            stock = inventory_service.get_stock_on_hand(item.id)
            return ItemResponse(
                id=str(item.id),
                name=item.name,
                category=item.category,
                unit_price=item.unit_price.to_float(),
                reorder_level=item.reorder_level,
                stock_on_hand=stock,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    # ===== Reports Routes =====
    @app.get("/api/reports/daily-sales")
    async def get_daily_sales(date: str = "") -> dict:
        """Get daily sales summary."""
        # TODO: Implement reporting service
        return {
            "date": date or datetime.utcnow().isoformat(),
            "total_revenue": 0.0,
            "transaction_count": 0,
            "payment_methods": {},
            "top_items": [],
        }

    @app.get("/api/reports/inventory-snapshot")
    async def get_inventory_snapshot() -> dict:
        """Get inventory snapshot."""
        try:
            inventory_service = InventoryService()
            items = inventory_service.item_repo.list()
            low_stock = inventory_service.get_low_stock_items()
            return {
                "total_items": len(items),
                "low_stock_count": len(low_stock),
                "low_stock_items": [
                    {
                        "id": str(item.id),
                        "name": item.name,
                        "stock": inventory_service.get_stock_on_hand(item.id),
                        "reorder_level": item.reorder_level,
                    }
                    for item in low_stock
                ],
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    # Global error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler."""
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
