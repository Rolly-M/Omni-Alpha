# OmniAlpha — Risk Controls Reference

> ⚠️ Always read this document before modifying any risk parameters.

## Mandatory Safeguards (Cannot Be Disabled)

| Safeguard | Description |
|---|---|
| **Paper mode default** | `LIVE_TRADING_ENABLED=false` — no real broker connections |
| **Manual approval** | `MANUAL_APPROVAL_REQUIRED=true` — human must confirm before execution |
| **Fat-finger hard cap** | 20% of portfolio per order — hardcoded, not configurable |
| **Duplicate order prevention** | Blocks same-direction orders in the same 60-second window |
| **Audit trail** | All decisions logged immutably, never deleted |

## Configurable Risk Limits (`.env`)

| Variable | Default | Description |
|---|---|---|
| `MAX_POSITION_SIZE_PCT` | 0.05 | 5% max per position |
| `MAX_DAILY_LOSS_PCT` | 0.02 | 2% max daily loss (circuit breaker) |
| `MAX_DRAWDOWN_PCT` | 0.15 | 15% max portfolio drawdown |
| `MAX_LEVERAGE` | 1.0 | No leverage by default |
| `MIN_CASH_PCT` | 0.10 | 10% minimum cash reserve |
| `MAX_SECTOR_EXPOSURE_PCT` | 0.30 | 30% max per sector |

## Kill Switch

Activating the kill switch immediately blocks ALL new orders:

```bash
# Via API
curl -X POST http://localhost:8000/api/control/kill-switch/activate?reason=emergency

# Via dashboard
Risk Monitor page → "ACTIVATE KILL SWITCH" button

# Via config
KILL_SWITCH_ENABLED=true  # in .env
```

## Risk Agent Veto Logic

The `RiskAgent` runs before every order. Evaluation order:

1. Kill switch check (immediate REJECTED if active)
2. Daily loss limit (REJECTED if breached)
3. Drawdown circuit breaker (REJECTED if > MAX_DRAWDOWN_PCT)
4. Cash floor (REJECTED if insufficient, or REDUCE_SIZE)
5. High volatility filter (halve position if ATR > 3%)
6. Aggregate risk score (REJECTED if avg > 75, reduce if > 60)
7. Fat-finger limit (REJECTED if > 20%)

## Risk Scoring

Each agent produces a `risk_score` (0-100). The Portfolio Manager and Risk Agent use this:
- < 30: Low risk — normal sizing
- 30–60: Medium risk — monitor
- 60–75: Elevated risk — reduce size
- > 75: High risk — reject trade

## Audit & Compliance

Every action writes to the `audit_logs` table:
- `AGENT_SIGNAL` — every agent output
- `RISK_APPROVED` / `RISK_REJECTED` — risk decisions
- `ORDER_SUBMITTED` / `ORDER_FILLED` / `ORDER_REJECTED` — order lifecycle
- `KILL_SWITCH_TRIGGERED` — emergency stops
- `CYCLE_STARTED` / `CYCLE_COMPLETE` — pipeline runs

Audit rows are **append-only** — no UPDATE or DELETE operations.
