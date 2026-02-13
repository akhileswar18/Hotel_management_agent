# Research: Agent-Based Architecture for HMS

**Date**: 2026-02-13 | **Status**: Complete

---

## R1: Event Bus Implementation — In-Process vs External Broker

**Decision**: In-process async event bus using Python `asyncio`

**Rationale**:
- Constitution mandates offline-first — external brokers (Redis, RabbitMQ, Kafka) require network
- Single-device deployment means no need for distributed messaging
- In-process dispatch achieves <1ms latency (vs 5-50ms for external brokers)
- Python `asyncio.Queue` + subscriber registry is <200 lines of code
- No new dependency; asyncio is stdlib

**Alternatives Considered**:
| Option | Latency | Offline? | Complexity | Rejected Because |
|--------|---------|----------|-----------|-----------------|
| Redis Pub/Sub | 5-10ms | NO | Medium | Requires Redis server; network dependency |
| RabbitMQ | 10-50ms | NO | High | Heavy infrastructure; overkill for single device |
| Kafka | 20-100ms | NO | Very High | Enterprise-scale; absurd for desktop app |
| Python `asyncio` | <1ms | YES | Low | **SELECTED** |
| Synchronous dispatch | <0.1ms | YES | Lowest | Blocks caller; no async agent execution |

**Implementation Notes**:
- Use `asyncio.Queue` per subscriber for backpressure
- Wildcard matching via prefix (e.g., `order.*` matches `order.create`)
- `publish_and_wait()` for request-reply pattern (API routes need response)
- Fire-and-forget `publish()` for cascading events (audit, notification)

---

## R2: Agent Framework — Custom vs LangChain vs CrewAI

**Decision**: Custom lightweight agent base class

**Rationale**:
- LangChain/CrewAI are designed for LLM orchestration; our agents are mostly rule-based
- Only 1 of 10 agents (InsightAgent) uses LLM
- Custom base class is ~50 lines; full framework adds 500MB+ of dependencies
- Constitution requires determinism — LLM frameworks add non-deterministic behavior

**Alternatives Considered**:
| Option | LLM Support | Rule Support | Size | Rejected Because |
|--------|------------|-------------|------|-----------------|
| LangChain | Excellent | Awkward | ~500MB | Overkill; 90% of agents are rule-based |
| CrewAI | Good | Limited | ~300MB | Focused on multi-LLM; wrong paradigm |
| Custom BaseAgent | Manual | Natural | ~50 lines | **SELECTED** |
| No framework | N/A | N/A | 0 | Agents need consistent interface |

**BaseAgent Interface**:
```python
class BaseAgent(ABC):
    name: str
    subscribes_to: List[str]
    
    @abstractmethod
    async def handle(self, event: Event) -> Optional[Event]:
        """Process event. Return response event or None."""
    
    async def publish(self, event: Event) -> None:
        """Publish event to bus."""
```

---

## R3: LLM Integration — Local vs Cloud

**Decision**: Configurable — local Ollama (default, offline) with optional OpenAI fallback

**Rationale**:
- Offline-first mandates local LLM as primary
- Ollama runs llama3/mistral locally on modest hardware
- Cloud API (OpenAI) can be used when available for better quality
- InsightAgent is advisory-only — degradable if LLM unavailable

**Configuration**:
```python
# .env
LLM_PROVIDER=ollama        # or "openai"
LLM_MODEL=llama3:8b        # or "gpt-4o-mini"
LLM_TIMEOUT=5              # seconds; skip if exceeded
OLLAMA_URL=http://localhost:11434
OPENAI_API_KEY=sk-...      # only if provider=openai
```

---

## R4: Event Persistence — Where to Store Events

**Decision**: SQLite `event_log` table (same database)

**Rationale**:
- Single source of truth (constitution)
- No additional infrastructure
- Events are append-only (matches audit log pattern)
- SQLite WAL mode handles concurrent writes well
- Queryable for debugging and replay

**Schema**:
```sql
CREATE TABLE event_log (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    source TEXT NOT NULL,
    correlation_id TEXT,
    user_id TEXT,
    payload TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
);
```

---

## R5: Migration Strategy — Strangler Fig

**Decision**: Incremental wrap-and-replace over 5 phases

**Rationale**:
- 70 tasks already complete and working; risk of breaking existing functionality is unacceptable
- Each phase is independently testable and deployable
- Rollback is trivial — remove event bus, agents still delegate to services

**Phases**:
1. **Infrastructure**: EventBus + EventStore + BaseAgent (no behavior change)
2. **Wrap services**: Create agents that delegate to existing services (identical behavior)
3. **Wire API**: Routes publish events instead of calling services (same HTTP interface)
4. **LLM agent**: Add InsightAgent with read-only access
5. **Orchestrator**: Add multi-step workflow support

---

## R6: Performance Impact Analysis

**Decision**: No measurable degradation expected

**Analysis**:
| Operation | Current | With Event Bus | Overhead |
|-----------|---------|---------------|----------|
| Order creation | ~50ms | ~51ms (+1ms dispatch) | +2% |
| Add item | ~30ms | ~31ms | +3% |
| Finalization | ~200ms | ~205ms (3 agents cascade) | +2.5% |
| Stock query | ~5ms | ~5ms (direct, no event) | 0% |
| Report gen | ~500ms | ~500ms (direct, no event) | 0% |

Key insight: The event dispatch overhead (<1ms) is negligible compared to DB I/O (5-200ms). The event bus adds indirection, not latency.

---

## R7: Error Handling in Event-Driven System

**Decision**: Dead letter queue + retry with exponential backoff

**Strategy**:
- Failed event handlers return `Event(type="*.error", ...)`
- Error events route to NotificationAgent → user sees error toast
- Critical failures (DB write fail) trigger synchronous fallback to direct service call
- Dead letter queue stores failed events for manual inspection
- Max 3 retries with 100ms, 500ms, 2s backoff
