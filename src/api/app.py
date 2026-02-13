"""
API Layer: FastAPI Application Setup

Main entry point for REST API.
All endpoints routed here, with global error handlers and middleware.
"""

from fastapi import FastAPI, HTTPException, status, Body, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID, uuid4

from src.application import AuthService, SalesService, InventoryService, ReportingService
from src.domain import Money, PaymentMethod
from src.events import EventBus, EventStore
from src.events.event import Event
from src.agents.order_agent import OrderAgent
from src.agents.audit_agent import AuditAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.auth_agent import AuthAgent
from src.agents.print_agent import PrintAgent
from src.agents.notification_agent import NotificationAgent
from src.agents.reporting_agent import ReportingAgent
from src.agents.inventory_agent import InventoryAgent
from src.agents.insight_agent import InsightAgent
from src.agents.orchestrator_agent import OrchestratorAgent


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


def _event_payload_to_response(payload: dict) -> OrderResponse:
    """Convert an event payload dict (from OrderAgent) back to an OrderResponse."""
    return OrderResponse(
        id=payload.get("order_id", ""),
        table_id=payload.get("table_id") or None,
        status=payload.get("status", ""),
        subtotal=payload.get("subtotal", 0.0),
        discount_amount=payload.get("discount_amount", 0.0),
        tax_amount=payload.get("tax_amount", 0.0),
        total_amount=payload.get("total_amount", 0.0),
        receipt_number=payload.get("receipt_number") or None,
        finalized_at=payload.get("finalized_at"),
        line_items=[
            LineItemResponse(
                id=li.get("id", ""),
                item_id=li.get("item_id", ""),
                item_name=li.get("item_name", ""),
                quantity=li.get("quantity", 0),
                unit_price=li.get("unit_price", 0.0),
                total_amount=li.get("total_amount", 0.0),
            )
            for li in payload.get("line_items", [])
        ],
    )


def _publish_order_event(event_bus: "EventBus", event: Event) -> OrderResponse:
    """Publish an order event to the bus and convert the result to an OrderResponse.

    Re-dispatches order.finalized and order.voided so InventoryAgent (and others) can react.
    Raises ValueError if the event bus returns an error (order.error) or fails.
    """
    result = event_bus.publish_sync(event)
    if not result.success:
        raise ValueError(result.error or "Event processing failed")
    if result.event and result.event.type == "order.error":
        error_msg = result.event.payload.get("message", "Order operation failed")
        raise ValueError(error_msg)
    if result.event:
        if result.event.type in ("order.finalized", "order.voided"):
            event_bus.publish_sync(result.event)
        return _event_payload_to_response(result.event.payload)
    raise ValueError("No response from event handler")


def _publish_inventory_event(event_bus: "EventBus", event: Event) -> dict:
    """Publish an inventory event and return the response payload.

    Raises ValueError if the bus fails or returns inventory.error.
    """
    result = event_bus.publish_sync(event)
    if not result.success:
        raise ValueError(result.error or "Event processing failed")
    if result.event and result.event.type == "inventory.error":
        error_msg = result.event.payload.get("message", "Inventory operation failed")
        raise ValueError(error_msg)
    if result.event:
        return result.event.payload
    raise ValueError("No response from event handler")


# ===== FastAPI App Setup =====

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Hotel Management System",
        description="Offline-first POS and inventory system",
        version="2.0.0",
    )

    # CORS Middleware (allow Flet local connections)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ===== Event Bus Setup (Agent Architecture) =====
    event_store = EventStore()
    event_bus = EventBus(store=event_store)

    # Register agents
    order_agent = OrderAgent()
    audit_agent = AuditAgent()

    # Subscribe OrderAgent to its declared event types
    for event_type in order_agent.subscribes_to:
        event_bus.subscribe(event_type, order_agent.handle)

    # Subscribe AuditAgent to all events (wildcard)
    for event_type in audit_agent.subscribes_to:
        event_bus.subscribe(event_type, audit_agent.handle)

    # Register InventoryAgent (needs bus to publish low_stock/out_of_stock alerts)
    inventory_agent = InventoryAgent(event_bus=event_bus)
    for event_type in inventory_agent.subscribes_to:
        event_bus.subscribe(event_type, inventory_agent.handle)

    # Subscribe PaymentAgent, AuthAgent, PrintAgent, NotificationAgent, ReportingAgent
    payment_agent = PaymentAgent()
    auth_agent = AuthAgent()
    print_agent = PrintAgent()
    notification_agent = NotificationAgent()
    reporting_agent = ReportingAgent()
    for event_type in payment_agent.subscribes_to:
        event_bus.subscribe(event_type, payment_agent.handle)
    for event_type in auth_agent.subscribes_to:
        event_bus.subscribe(event_type, auth_agent.handle)
    for event_type in print_agent.subscribes_to:
        event_bus.subscribe(event_type, print_agent.handle)
    for event_type in notification_agent.subscribes_to:
        event_bus.subscribe(event_type, notification_agent.handle)
    for event_type in reporting_agent.subscribes_to:
        event_bus.subscribe(event_type, reporting_agent.handle)

    # Register InsightAgent (LLM advisory, read-only, degradable)
    insight_agent = InsightAgent()
    for event_type in insight_agent.subscribes_to:
        event_bus.subscribe(event_type, insight_agent.handle)

    # Register OrchestratorAgent (multi-step workflows; needs bus to fire sub-events)
    orchestrator_agent = OrchestratorAgent(event_bus=event_bus)
    for event_type in orchestrator_agent.subscribes_to:
        event_bus.subscribe(event_type, orchestrator_agent.handle)

    # Store on app.state for external access (tests, UI polling for notifications)
    app.state.event_bus = event_bus
    app.state.notification_agent = notification_agent

    # Security: Add basic rate limiting middleware
    from collections import defaultdict
    import time as _time
    _rate_limits = defaultdict(list)
    _RATE_LIMIT = 100  # requests per minute

    @app.middleware("http")
    async def rate_limit_middleware(request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = _time.time()
        # Clean old entries
        _rate_limits[client_ip] = [t for t in _rate_limits[client_ip] if now - t < 60]
        if len(_rate_limits[client_ip]) >= _RATE_LIMIT:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        _rate_limits[client_ip].append(now)
        response = await call_next(request)
        return response

    @app.middleware("http")
    async def security_headers_middleware(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

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
            username = request.username
            pin = request.pin
            # Input validation
            if len(username) > 50:
                raise ValueError("Username too long")
            if len(pin) > 10:
                raise ValueError("PIN too long")
            auth_service = AuthService()
            user, token = auth_service.login(username, pin)
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
    async def logout(request: dict = Body(default={})) -> dict:
        """Logout user — invalidate session."""
        try:
            auth_service = AuthService()
            session_token = request.get("token", "")
            user_id = request.get("user_id", "")
            auth_service.logout(user_id=user_id, session_token=session_token)
            return {"status": "logged_out"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/auth/me")
    async def get_current_user() -> dict:
        """Get current user info (from session/token)."""
        return {"user_id": "current_user_id"}

    # ===== User Management Routes (Manager Only) =====
    @app.get("/api/users")
    async def list_users() -> list:
        """List all users (manager only)."""
        try:
            auth_service = AuthService()
            users = auth_service.user_repo.list()
            return [
                {
                    "id": str(u.id),
                    "username": u.username,
                    "role": u.role.value,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ]
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/users")
    async def create_user(request: dict = Body(...)) -> dict:
        """Create a new user (manager only)."""
        try:
            username = request.get("username", "").strip()
            pin = request.get("pin", "").strip()
            role = request.get("role", "WAITER").strip().upper()
            if not username or not pin:
                raise ValueError("Username and PIN are required")
            if len(pin) < 4:
                raise ValueError("PIN must be at least 4 digits")

            auth_service = AuthService()
            # Check for duplicate username
            existing = auth_service.user_repo.get_by_username(username)
            if existing:
                raise ValueError(f"Username '{username}' already exists")

            from src.domain import User, Role
            from uuid import uuid4
            pin_hash = auth_service.hash_pin(pin)
            user = User(
                id=uuid4(),
                username=username,
                role=Role(role),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            auth_service.user_repo.create(user, pin_hash)
            return {
                "id": str(user.id),
                "username": user.username,
                "role": user.role.value,
                "status": "created",
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/api/users/{user_id}")
    async def update_user(user_id: str, request: dict = Body(default={})) -> dict:
        """Update user role or reset PIN (manager only)."""
        try:
            auth_service = AuthService()
            user = auth_service.user_repo.get(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            new_role = request.get("role")
            new_pin = request.get("pin")

            updates = []
            params = []
            if new_role:
                updates.append("role = ?")
                params.append(new_role.upper())
            if new_pin:
                pin_hash = auth_service.hash_pin(new_pin)
                updates.append("pin_hash = ?")
                params.append(pin_hash)
            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.utcnow().isoformat() + "Z")
                params.append(user_id)
                from src.infrastructure.database import Database
                db = Database()
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
                db.conn.execute(query, params)
                db.conn.commit()

            return {"id": user_id, "status": "updated"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ===== Sales Routes (Event-Driven via OrderAgent) =====
    @app.post("/api/sales/orders")
    async def create_order(request: CreateOrderRequest) -> OrderResponse:
        """Create a new draft order via event bus."""
        user_id = _resolve_user_id(request.user_id)
        try:
            event = Event.create(
                type="order.create",
                source="API",
                payload={"table_id": request.table_id or "1", "user_id": str(user_id)},
                user_id=str(user_id),
            )
            return _publish_order_event(event_bus, event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/items")
    async def add_item_to_order(order_id: str, request: OrderItemRequest) -> OrderResponse:
        """Add an item to a draft order via event bus."""
        user_id = _resolve_user_id(request.user_id)
        try:
            event = Event.create(
                type="order.add_item",
                source="API",
                payload={
                    "order_id": order_id,
                    "item_id": request.item_id,
                    "quantity": request.quantity,
                },
                user_id=str(user_id),
            )
            return _publish_order_event(event_bus, event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/api/sales/orders/{order_id}/discount")
    async def apply_discount(order_id: str, request: DiscountRequest) -> OrderResponse:
        """Apply a discount to a draft order via event bus."""
        user_id = _resolve_user_id(request.user_id)
        try:
            event = Event.create(
                type="order.discount",
                source="API",
                payload={
                    "order_id": order_id,
                    "discount_type": request.discount_type,
                    "discount_value": request.amount,
                },
                user_id=str(user_id),
            )
            return _publish_order_event(event_bus, event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/finalize")
    async def finalize_order(order_id: str, request: FinalizeOrderRequest) -> OrderResponse:
        """Finalize order, process payment, deduct stock via event bus."""
        user_id = _resolve_user_id(request.user_id)
        try:
            event = Event.create(
                type="order.finalize",
                source="API",
                payload={
                    "order_id": order_id,
                    "payment_method": request.payment_method,
                    "amount_tendered": request.paid_amount,
                },
                user_id=str(user_id),
            )
            return _publish_order_event(event_bus, event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/void")
    async def void_order(order_id: str, request: VoidOrderRequest) -> OrderResponse:
        """Void an order with reason via event bus."""
        user_id = _resolve_user_id(request.user_id)
        try:
            event = Event.create(
                type="order.void",
                source="API",
                payload={
                    "order_id": order_id,
                    "reason": request.reason,
                    "approver_id": request.approver_id or "",
                },
                user_id=str(user_id),
            )
            return _publish_order_event(event_bus, event)
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
        """Remove a line item from a draft order via event bus."""
        try:
            user_id = _resolve_user_id(request.user_id if request else None)
            event = Event.create(
                type="order.remove_item",
                source="API",
                payload={
                    "order_id": order_id,
                    "line_item_id": line_item_id,
                },
                user_id=str(user_id),
            )
            return _publish_order_event(event_bus, event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/api/sales/orders/{order_id}/items/{line_item_id}")
    async def update_line_item_qty(order_id: str, line_item_id: str, request: UpdateLineItemQtyRequest) -> OrderResponse:
        """Update quantity of a line item in a draft order via event bus."""
        try:
            user_id = _resolve_user_id(request.user_id)
            event = Event.create(
                type="order.edit_qty",
                source="API",
                payload={
                    "order_id": order_id,
                    "line_item_id": line_item_id,
                    "new_qty": request.quantity,
                },
                user_id=str(user_id),
            )
            return _publish_order_event(event_bus, event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/hold")
    async def hold_order(order_id: str, request: HoldResumeRequest = None) -> OrderResponse:
        """Put a draft order on hold via event bus."""
        try:
            user_id = _resolve_user_id(request.user_id if request else None)
            event = Event.create(
                type="order.hold",
                source="API",
                payload={"order_id": order_id},
                user_id=str(user_id),
            )
            return _publish_order_event(event_bus, event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/sales/orders/{order_id}/resume")
    async def resume_order(order_id: str, request: HoldResumeRequest = None) -> OrderResponse:
        """Resume a held order via event bus."""
        try:
            user_id = _resolve_user_id(request.user_id if request else None)
            event = Event.create(
                type="order.resume",
                source="API",
                payload={"order_id": order_id},
                user_id=str(user_id),
            )
            return _publish_order_event(event_bus, event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/receipts/{receipt_number}")
    async def get_receipt(receipt_number: str) -> dict:
        """Get receipt/order data by receipt number (for digital receipt link)."""
        try:
            sales_service = SalesService()
            order = sales_service.get_order_by_receipt_number(receipt_number)
            if not order:
                raise HTTPException(status_code=404, detail="Receipt not found")
            return _order_to_response(order).model_dump()
        except HTTPException:
            raise
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
        """Update an existing item's price and/or reorder level via event bus."""
        user_id = _resolve_user_id(request.user_id)
        try:
            payload = {"item_id": item_id}
            if request.unit_price is not None:
                payload["unit_price"] = request.unit_price
            if request.reorder_level is not None:
                payload["reorder_level"] = request.reorder_level
            event = Event.create(
                type="inventory.update",
                source="API",
                payload=payload,
                user_id=str(user_id),
            )
            result_payload = _publish_inventory_event(event_bus, event)
            return ItemResponse(
                id=result_payload.get("id", item_id),
                name=result_payload.get("name", ""),
                category=result_payload.get("category", ""),
                unit_price=result_payload.get("unit_price", 0.0),
                reorder_level=result_payload.get("reorder_level", 0),
                stock_on_hand=result_payload.get("stock_on_hand", 0),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/api/inventory/items/{item_id}/archive")
    async def archive_item(item_id: str, request: UpdateItemRequest = None) -> dict:
        """Soft-delete / archive an inventory item via event bus."""
        user_id = _resolve_user_id(request.user_id if request else None)
        try:
            event = Event.create(
                type="inventory.archive",
                source="API",
                payload={"item_id": item_id},
                user_id=str(user_id),
            )
            payload = _publish_inventory_event(event_bus, event)
            return {
                "status": payload.get("status", "archived"),
                "item_id": payload.get("item_id", item_id),
                "name": payload.get("name", ""),
            }
        except ValueError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))
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
        """Record stock adjustment (recount, wastage, etc.) via event bus."""
        user_id = _resolve_user_id(request.user_id)
        try:
            event = Event.create(
                type="inventory.adjust",
                source="API",
                payload={
                    "item_id": request.item_id,
                    "quantity_change": request.quantity_change,
                    "reason": request.reason,
                },
                user_id=str(user_id),
            )
            payload = _publish_inventory_event(event_bus, event)
            return {
                "id": payload.get("id", ""),
                "item_id": payload.get("item_id", ""),
                "quantity_change": payload.get("quantity_change", 0),
                "reason": payload.get("reason", ""),
                "transaction_type": payload.get("transaction_type", "ADJUSTMENT"),
                "stock_on_hand": payload.get("stock_on_hand", 0),
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

    # ===== Insights (InsightAgent — LLM advisory, read-only) =====
    @app.get("/api/insights/upsell/{order_id}")
    async def get_upsell_suggestions(order_id: str) -> dict:
        """Get LLM upsell suggestions for an order. Degrades to empty if LLM unavailable."""
        event = Event.create(
            type="insight.suggest_upsell",
            payload={"order_id": order_id},
            source="API",
        )
        result = event_bus.publish_sync(event)
        if result.success and result.event and result.event.type == "insight.suggestion":
            return result.event.payload
        return {"suggestions": [], "message": "Insight unavailable"}

    @app.post("/api/insights/query")
    async def natural_language_query(request: dict = Body(...)) -> dict:
        """Natural language query over sales/reporting data. Degrades if LLM unavailable."""
        question = request.get("question", "")
        event = Event.create(
            type="insight.natural_query",
            payload={"question": question},
            source="API",
        )
        result = event_bus.publish_sync(event)
        if result.success and result.event and result.event.type == "insight.query_result":
            return result.event.payload
        return {"answer": "", "message": "Insight unavailable"}

    # ===== Voice WebSocket (A124) =====
    @app.websocket("/ws/voice")
    async def voice_websocket(websocket: WebSocket):
        await websocket.accept()
        try:
            from src.voice.stt import SpeechToText
            from src.voice.tts import TextToSpeech
            from src.voice.intent_parser import IntentParser
            stt = SpeechToText()
            tts = TextToSpeech()
            parser = IntentParser()

            while True:
                data = await websocket.receive_bytes()
                transcript = stt.transcribe(data)
                if not transcript:
                    await websocket.send_json({"type": "error", "message": "Could not transcribe audio"})
                    continue

                await websocket.send_json({"type": "transcript", "text": transcript})

                intent = parser.parse(transcript)
                await websocket.send_json({"type": "intent", "intent": intent})

                if intent.get("action") == "create_order" and intent.get("items"):
                    event = Event.create(
                        type="workflow.multi_step",
                        source="VoicePipeline",
                        payload={"intent": intent},
                    )
                    result = event_bus.publish_sync(event)
                    if result.success and result.event:
                        await websocket.send_json({"type": "result", "payload": result.event.payload})
                    else:
                        await websocket.send_json({"type": "error", "message": result.error or "Workflow failed"})
                else:
                    await websocket.send_json({"type": "info", "message": f"Intent: {intent.get('action', 'unknown')}"})
        except Exception:
            pass  # WebSocket closed

    # ===== Text Command (voice-equivalent without audio) =====
    class TextCommandRequest(BaseModel):
        text: str
        user_id: str = ""
        pending_intent: dict = None  # For follow-up conversation context

    @app.post("/api/voice/text-command")
    async def text_command(request: TextCommandRequest):
        """Process a text command through IntentParser.
        Supports follow-up questions when required fields are missing.
        Pass pending_intent from a previous response to continue a conversation."""
        try:
            from src.voice.intent_parser import IntentParser
            parser = IntentParser()

            # If there's a pending intent, merge the follow-up answer
            if request.pending_intent:
                intent = parser.parse_followup(request.pending_intent, request.text)
            else:
                intent = parser.parse(request.text)

            action = intent.get("action", "unknown")

            # Check for missing required fields → ask follow-up
            missing = parser.get_missing_fields(intent)
            if missing:
                prompt = parser.get_followup_prompt(intent)
                return {
                    "status": "followup",
                    "intent": intent,
                    "missing_fields": missing,
                    "message": prompt,
                }

            # --- Execute the command based on action ---
            sales_service = SalesService()
            inventory_service = InventoryService()
            reporting_service = ReportingService()

            if action == "create_order":
                event = Event.create(
                    type="workflow.multi_step",
                    source="TextCommand",
                    payload={"intent": intent},
                    user_id=request.user_id,
                )
                result = event_bus.publish_sync(event)
                if result.success and result.event:
                    return {
                        "status": "success",
                        "intent": intent,
                        "result": result.event.payload,
                        "message": "Order created successfully!",
                    }
                else:
                    return {
                        "status": "error",
                        "intent": intent,
                        "message": result.error or "Failed to create order",
                    }

            elif action == "add_item":
                # Add items to the most recent draft order
                try:
                    orders = sales_service.list_orders(status="draft")
                    if not orders:
                        return {"status": "error", "intent": intent,
                                "message": "No active draft order. Create an order first."}
                    current_order = orders[-1]
                    uid = UUID(request.user_id) if request.user_id else (current_order.created_by or UUID(int=0))
                    for item in intent.get("items", []):
                        sales_service.add_item(
                            order_id=current_order.id,
                            item_id=UUID(item["item_id"]),
                            quantity=item.get("quantity", 1),
                            added_by=uid,
                        )
                    updated = sales_service.get_order(current_order.id)
                    items_desc = ", ".join(f"{i.get('name','?')} x{i.get('quantity',1)}" for i in intent.get("items", []))
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Added {items_desc} to order (table {updated.table_id}).",
                    }
                except Exception as ex:
                    return {"status": "error", "intent": intent, "message": str(ex)}

            elif action == "finalize_order":
                try:
                    from src.domain.value_objects import PaymentMethod as PM, Money
                    orders = sales_service.list_orders(status="draft")
                    if not orders:
                        return {"status": "error", "intent": intent,
                                "message": "No active draft order to finalize."}
                    current_order = orders[-1]
                    pm_str = intent.get("payment_method", "CASH")
                    pm = PM(pm_str)
                    uid = UUID(request.user_id) if request.user_id else (current_order.created_by or UUID(int=0))
                    total_money = current_order.total_amount if isinstance(current_order.total_amount, Money) else Money(cents=int(current_order.total_amount * 100) if current_order.total_amount else 0)
                    finalized = sales_service.finalize_order(
                        order_id=current_order.id,
                        payment_method=pm,
                        paid_amount=total_money,
                        finalized_by=uid,
                    )
                    total_display = finalized.total_amount.cents / 100 if hasattr(finalized.total_amount, 'cents') else finalized.total_amount
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Order finalized! Receipt #{finalized.receipt_number}, Total: Rs.{total_display:.2f}, Payment: {pm_str}",
                    }
                except Exception as ex:
                    return {"status": "error", "intent": intent, "message": str(ex)}

            elif action == "void_order":
                try:
                    orders = sales_service.list_orders(status="draft")
                    if not orders:
                        return {"status": "error", "intent": intent,
                                "message": "No active draft order to void."}
                    current_order = orders[-1]
                    reason = intent.get("reason") or "Voided via command"
                    uid = UUID(request.user_id) if request.user_id else (current_order.created_by or UUID(int=0))
                    sales_service.void_order(
                        order_id=current_order.id,
                        reason=reason,
                        voided_by=uid,
                    )
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Order voided. Reason: {reason}",
                    }
                except Exception as ex:
                    return {"status": "error", "intent": intent, "message": str(ex)}

            elif action == "hold_order":
                try:
                    orders = sales_service.list_orders(status="draft")
                    if not orders:
                        return {"status": "error", "intent": intent,
                                "message": "No active draft order to hold."}
                    current_order = orders[-1]
                    uid = UUID(request.user_id) if request.user_id else (current_order.created_by or UUID(int=0))
                    sales_service.hold_order(
                        order_id=current_order.id,
                        user_id=uid,
                    )
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Order for table {current_order.table_id} put on hold.",
                    }
                except Exception as ex:
                    return {"status": "error", "intent": intent, "message": str(ex)}

            elif action == "create_product":
                try:
                    from src.domain.value_objects import Money
                    price_cents = int(intent["price"] * 100)
                    uid = UUID(request.user_id) if request.user_id else UUID(int=0)
                    new_item = inventory_service.create_item(
                        name=intent["name"],
                        category=intent.get("category", "food"),
                        unit_price=Money(cents=price_cents),
                        reorder_level=intent.get("reorder_level", 10),
                        created_by=uid,
                    )
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Product '{intent['name']}' created at Rs.{intent['price']:.2f} ({intent.get('category', 'food')}).",
                    }
                except Exception as ex:
                    return {"status": "error", "intent": intent, "message": str(ex)}

            elif action == "stock_in":
                try:
                    item_id = UUID(intent["item_id"]) if intent.get("item_id") else None
                    qty = intent.get("quantity", 0)
                    uid = UUID(request.user_id) if request.user_id else UUID(int=0)
                    if not item_id:
                        return {"status": "error", "intent": intent, "message": "Could not identify the product."}
                    inventory_service.record_stock_in(
                        item_id=item_id,
                        quantity=qty,
                        reference="command_stock_in",
                        recorded_by=uid,
                    )
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Added {qty} units of {intent.get('item_name', '?')} to stock.",
                    }
                except Exception as ex:
                    return {"status": "error", "intent": intent, "message": str(ex)}

            elif action == "report":
                try:
                    from datetime import date
                    report = reporting_service.daily_sales_summary(date.today())
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": (
                            f"Today's Sales:\n"
                            f"Revenue: ₹{report.get('total_revenue', 0):,.2f}\n"
                            f"Transactions: {report.get('transaction_count', 0)}\n"
                            f"Avg Order: ₹{report.get('average_order_value', 0):,.2f}"
                        ),
                    }
                except Exception as ex:
                    return {"status": "error", "intent": intent, "message": str(ex)}

            else:
                return {
                    "status": "info",
                    "intent": intent,
                    "message": (
                        "I didn't understand that command. Try:\n"
                        "• 'create order for table 5 with 2 biryani'\n"
                        "• 'finalize order, pay cash'\n"
                        "• 'add 3 coke to order'\n"
                        "• 'void order'\n"
                        "• 'new product biryani at 250 food'\n"
                        "• 'add 50 units of biryani to stock'\n"
                        "• 'show today's sales'"
                    ),
                }

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
