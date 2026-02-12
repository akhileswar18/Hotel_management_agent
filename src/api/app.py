"""
API Layer: FastAPI Application Setup

Main entry point for REST API.
All endpoints routed here, with global error handlers and middleware.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID, uuid4

from src.application import AuthService, SalesService, InventoryService, ReportingService
from src.domain import Money, PaymentMethod


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
    user_id: Optional[str] = None  # Logged-in user ID


class OrderItemRequest(BaseModel):
    """Add item to order request."""
    item_id: str
    quantity: int
    user_id: Optional[str] = None


class FinalizeOrderRequest(BaseModel):
    """Finalize order request."""
    payment_method: str  # CASH, CARD, VOUCHER
    paid_amount: float  # In rupees (will be converted to Money)
    user_id: Optional[str] = None


class DiscountRequest(BaseModel):
    """Apply discount request."""
    discount_type: str  # "percentage" or "absolute"
    amount: float  # % value or absolute amount in paisa
    user_id: Optional[str] = None


class VoidOrderRequest(BaseModel):
    """Void order request."""
    reason: str
    approver_id: Optional[str] = None
    user_id: Optional[str] = None


class StockInRequest(BaseModel):
    """Record stock-in request."""
    item_id: str
    quantity: int
    reference: str
    user_id: Optional[str] = None


class StockAdjustmentRequest(BaseModel):
    """Record stock adjustment request."""
    item_id: str
    quantity_change: int
    reason: str
    user_id: Optional[str] = None


class CreateItemRequest(BaseModel):
    """Create new inventory item."""
    name: str
    category: str
    unit_price: float  # In rupees
    reorder_level: int = 10
    user_id: Optional[str] = None


class UpdateItemRequest(BaseModel):
    """Update inventory item (price and/or reorder level)."""
    unit_price: Optional[float] = None  # In rupees
    reorder_level: Optional[int] = None
    user_id: Optional[str] = None


class RemoveLineItemRequest(BaseModel):
    """Remove line item from order."""
    user_id: Optional[str] = None


class UpdateLineItemQtyRequest(BaseModel):
    """Update line item quantity."""
    quantity: int
    user_id: Optional[str] = None


class HoldResumeRequest(BaseModel):
    """Hold or resume an order."""
    user_id: Optional[str] = None


class LineItemResponse(BaseModel):
    """Line item response model."""
    id: str
    item_id: str
    item_name: str
    quantity: int
    unit_price: float
    total_amount: float


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
    line_items: List[LineItemResponse] = []

    class Config:
        from_attributes = True


def _resolve_user_id(request_user_id: Optional[str]) -> UUID:
    """
    Resolve user ID from request. Uses the provided ID if valid,
    otherwise falls back to the first user in the DB (for dev convenience).
    """
    if request_user_id:
        return UUID(request_user_id)
    # Fallback: grab the first user from DB so FK constraints are satisfied
    from src.infrastructure import UserRepository
    users = UserRepository().list()
    if users:
        return users[0].id
    return uuid4()


def _order_to_response(order) -> OrderResponse:
    """Convert Order domain entity to API response."""
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
        line_items=[
            LineItemResponse(
                id=str(li.id),
                item_id=str(li.item_id),
                item_name=li.item_name,
                quantity=li.quantity,
                unit_price=li.unit_price.to_float(),
                total_amount=li.total_amount.to_float(),
            )
            for li in order.line_items
        ],
    )


# ===== FastAPI App Setup =====

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Hotel Management System - Phase 1",
        description="Offline-first POS and inventory system",
        version="1.0.0",
    )

    # CORS Middleware (allow Flet local connections)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
            "version": "1.0.0",
        }

    # ===== Auth Routes =====
    @app.post("/api/auth/login")
    async def login(request: LoginRequest) -> LoginResponse:
        """Authenticate user with username and PIN."""
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
        """Logout endpoint (session invalidation)."""
        return {"status": "logged_out"}

    @app.get("/api/auth/me")
    async def get_current_user() -> dict:
        """Get current user info (from session/token)."""
        return {"user_id": "current_user_id"}

    # ===== Sales Routes =====
    @app.post("/api/sales/orders")
    async def create_order(request: CreateOrderRequest) -> OrderResponse:
        """Create a new draft order."""
        user_id = _resolve_user_id(request.user_id)
        try:
            sales_service = SalesService()
            order = sales_service.create_order(request.table_id, user_id)
            return _order_to_response(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/items")
    async def add_item_to_order(order_id: str, request: OrderItemRequest) -> OrderResponse:
        """Add an item to a draft order. Line item persisted to DB."""
        user_id = _resolve_user_id(request.user_id)
        try:
            sales_service = SalesService()
            order = sales_service.add_item(
                UUID(order_id),
                UUID(request.item_id),
                request.quantity,
                user_id,
            )
            return _order_to_response(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/api/sales/orders/{order_id}/discount")
    async def apply_discount(order_id: str, request: DiscountRequest) -> OrderResponse:
        """Apply a discount to a draft order."""
        user_id = _resolve_user_id(request.user_id)
        try:
            sales_service = SalesService()
            order = sales_service.apply_order_discount(
                UUID(order_id),
                request.discount_type,
                request.amount,
                user_id,
            )
            return _order_to_response(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/finalize")
    async def finalize_order(order_id: str, request: FinalizeOrderRequest) -> OrderResponse:
        """Finalize order, process payment, deduct stock, assign receipt number."""
        user_id = _resolve_user_id(request.user_id)
        try:
            sales_service = SalesService()
            order = sales_service.finalize_order(
                UUID(order_id),
                PaymentMethod(request.payment_method),
                Money.from_float(request.paid_amount),
                user_id,
            )
            return _order_to_response(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/void")
    async def void_order(order_id: str, request: VoidOrderRequest) -> OrderResponse:
        """Void an order with reason. Reverses stock if finalized."""
        user_id = _resolve_user_id(request.user_id)
        try:
            sales_service = SalesService()
            order = sales_service.void_order(
                UUID(order_id),
                request.reason,
                user_id,
                UUID(request.approver_id) if request.approver_id else None,
            )
            return _order_to_response(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/sales/orders/{order_id}")
    async def get_order(order_id: str) -> OrderResponse:
        """Get order details with line items."""
        try:
            sales_service = SalesService()
            order = sales_service.get_order(UUID(order_id))
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            return _order_to_response(order)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.delete("/api/sales/orders/{order_id}/items/{line_item_id}")
    async def remove_line_item(order_id: str, line_item_id: str, request: RemoveLineItemRequest = None) -> OrderResponse:
        """Remove a line item from a draft order."""
        try:
            sales_service = SalesService()
            user_id = _resolve_user_id(request.user_id if request else None)
            order = sales_service.remove_item(UUID(order_id), UUID(line_item_id), user_id)
            return _order_to_response(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/api/sales/orders/{order_id}/items/{line_item_id}")
    async def update_line_item_qty(order_id: str, line_item_id: str, request: UpdateLineItemQtyRequest) -> OrderResponse:
        """Update quantity of a line item in a draft order."""
        try:
            sales_service = SalesService()
            user_id = _resolve_user_id(request.user_id)
            order = sales_service.update_item_quantity(UUID(order_id), UUID(line_item_id), request.quantity, user_id)
            return _order_to_response(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/hold")
    async def hold_order(order_id: str, request: HoldResumeRequest = None) -> OrderResponse:
        """Put a draft order on hold."""
        try:
            sales_service = SalesService()
            user_id = _resolve_user_id(request.user_id if request else None)
            order = sales_service.hold_order(UUID(order_id), user_id)
            return _order_to_response(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/resume")
    async def resume_order(order_id: str, request: HoldResumeRequest = None) -> OrderResponse:
        """Resume a held order."""
        try:
            sales_service = SalesService()
            user_id = _resolve_user_id(request.user_id if request else None)
            order = sales_service.resume_order(UUID(order_id), user_id)
            return _order_to_response(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/sales/orders")
    async def list_orders(status: str = "", date: str = "") -> List[OrderResponse]:
        """List orders with optional filters."""
        try:
            sales_service = SalesService()
            orders = sales_service.list_orders(
                status=status if status else None,
                date_str=date if date else None,
            )
            return [_order_to_response(o) for o in orders]
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ===== Inventory Routes =====
    @app.get("/api/inventory/items")
    async def list_items(category: str = "") -> List[ItemResponse]:
        """List all items with current stock on hand. Optionally filter by category."""
        try:
            inventory_service = InventoryService()
            if category:
                items = inventory_service.item_repo.list_by_category(category)
            else:
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
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/inventory/items/{item_id}")
    async def get_item(item_id: str) -> ItemResponse:
        """Get item details with current stock."""
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
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/inventory/items")
    async def create_item(request: CreateItemRequest) -> ItemResponse:
        """Create a new inventory item / product."""
        user_id = _resolve_user_id(request.user_id)
        try:
            inventory_service = InventoryService()
            item = inventory_service.create_item(
                name=request.name,
                category=request.category,
                unit_price=Money.from_float(request.unit_price),
                reorder_level=request.reorder_level,
                created_by=user_id,
            )
            return ItemResponse(
                id=str(item.id),
                name=item.name,
                category=item.category,
                unit_price=item.unit_price.to_float(),
                reorder_level=item.reorder_level,
                stock_on_hand=0,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/api/inventory/items/{item_id}")
    async def update_item(item_id: str, request: UpdateItemRequest) -> ItemResponse:
        """Update an existing item's price and/or reorder level."""
        user_id = _resolve_user_id(request.user_id)
        try:
            inventory_service = InventoryService()
            price = Money.from_float(request.unit_price) if request.unit_price is not None else None
            item = inventory_service.update_item(
                item_id=UUID(item_id),
                updated_by=user_id,
                unit_price=price,
                reorder_level=request.reorder_level,
            )
            stock = inventory_service.get_stock_on_hand(UUID(item_id))
            return ItemResponse(
                id=str(item.id),
                name=item.name,
                category=item.category,
                unit_price=item.unit_price.to_float(),
                reorder_level=item.reorder_level,
                stock_on_hand=stock,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/api/inventory/items/{item_id}/archive")
    async def archive_item(item_id: str, request: UpdateItemRequest = None) -> dict:
        """Soft-delete / archive an inventory item."""
        user_id = _resolve_user_id(request.user_id if request else None)
        try:
            inventory_service = InventoryService()
            item = inventory_service.item_repo.get(item_id)
            if not item:
                raise HTTPException(status_code=404, detail="Item not found")
            inventory_service.item_repo.archive_item(item_id, str(user_id))
            return {"status": "archived", "item_id": item_id, "name": item.name}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/inventory/stock-in")
    async def record_stock_in(request: StockInRequest) -> dict:
        """Record stock-in (purchase delivery)."""
        user_id = _resolve_user_id(request.user_id)
        try:
            inventory_service = InventoryService()
            entry = inventory_service.record_stock_in(
                item_id=UUID(request.item_id),
                quantity=request.quantity,
                reference=request.reference,
                recorded_by=user_id,
            )
            return {
                "id": str(entry.id),
                "item_id": str(entry.item_id),
                "quantity_change": entry.quantity_change,
                "reason": entry.reason,
                "transaction_type": entry.transaction_type.value,
                "stock_on_hand": inventory_service.get_stock_on_hand(UUID(request.item_id)),
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/inventory/adjustments")
    async def record_adjustment(request: StockAdjustmentRequest) -> dict:
        """Record stock adjustment (recount, wastage, etc.)."""
        user_id = _resolve_user_id(request.user_id)
        try:
            inventory_service = InventoryService()
            entry = inventory_service.record_adjustment(
                item_id=UUID(request.item_id),
                quantity_change=request.quantity_change,
                reason=request.reason,
                adjusted_by=user_id,
            )
            return {
                "id": str(entry.id),
                "item_id": str(entry.item_id),
                "quantity_change": entry.quantity_change,
                "reason": entry.reason,
                "transaction_type": entry.transaction_type.value,
                "stock_on_hand": inventory_service.get_stock_on_hand(UUID(request.item_id)),
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ===== Reports Routes =====
    @app.get("/api/reports/transactions")
    async def search_transactions(start_date: str = "", end_date: str = "", payment_method: str = "") -> list:
        """Search finalized orders/transactions with filters."""
        try:
            reporting_service = ReportingService()
            results = reporting_service.search_transactions(
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else None,
                payment_method=payment_method if payment_method else None,
            )
            return results
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/reports/daily-sales")
    async def get_daily_sales(report_date: str = "") -> dict:
        """Get daily sales summary with real data from DB."""
        try:
            reporting_service = ReportingService()
            target_date = None
            if report_date:
                target_date = date.fromisoformat(report_date)
            return reporting_service.daily_sales_summary(target_date)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/reports/inventory-snapshot")
    async def get_inventory_snapshot() -> dict:
        """Get inventory snapshot with stock levels and low-stock alerts."""
        try:
            reporting_service = ReportingService()
            return reporting_service.inventory_snapshot()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Global error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler for unhandled errors."""
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
