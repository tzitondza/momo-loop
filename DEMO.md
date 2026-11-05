# MoMo Loop — Demo scripts

Use these with the live app. Default judge account: **`lead@mtn.demo` / `lead123`**.

Caveats to say once early: cash-out after inflow is a **signal**, not proof; recoverable value is **modelled**; data is **synthetic** with planted gaps for ranking checks.

---

## 90-second pitch (no click-through)

1. **Problem** — MoMo value leaks to cash when the next merchant cannot accept it.  
2. **Insight** — Inflow → cash-out within 30 minutes flags probable cash-out boundaries.  
3. **Product** — MoMo Loop ranks where expanding acceptance keeps the most value digital.  
4. **Proof** — Live dashboard: leak KPIs → boundary map → scored opportunities → pipeline → impact simulator.  
5. **Ask** — Pilot on anonymised OpCo data; measure merchant-payment lift in one corridor.

---

## 3-minute live demo (recommended)

**Login:** `lead@mtn.demo` / `lead123` (national scope).

| Time | Where | Say / do |
| --- | --- | --- |
| 0:00 | Login | “Internal tool for acquisition — roles and territory scoping.” |
| 0:20 | **Overview** | Point to leakage / recoverable value / opportunity count. “Value enters the wallet, then exits as cash.” |
| 0:50 | **Boundaries** | Open a hotspot. “Inflow then cash-out in 30 minutes — probable boundary, not a failed payment claim.” |
| 1:20 | **Opportunities** | Top row score + reasons. Optional: Export CSV/PDF. “Transparent scoring, not a black-box model.” |
| 1:50 | **Pipeline** | **Add to pipeline** → move to *reviewing* / *assigned*. “Turns insight into merchant-team workflow.” |
| 2:20 | **Simulate** | Raise merchants / recovery → save scenario. “What if we onboard here?” |
| 2:45 | Close | “Next: validate on anonymised MoMo data, pilot one area, measure digital payment lift.” |

**Optional 20s contrast:** log out → `viewer@mtn.demo` / `viewer123` → Overview only shows **Gauteng**. “Same product, OpCo-scoped.”

---

## 5-minute judge deep-dive

Follow the 3-minute path, then add:

1. **Admin** (`admin@mtn.demo` / `admin123`) — Refresh analytics + CSV upload story (“batch anonymised feeds”).  
2. **Ranking quality** — Call out planted gaps / hit-rate if shown on Opportunities.  
3. **Path to production** — Postgres store, nightly rematerialise, JWT roles, audit on exports/pipeline — “built like an internal platform, not a slide deck.”

---

## One-line answers (if asked)

| Question | Answer |
| --- | --- |
| Is every cash-out a rejected merchant? | No — we score **probable** boundaries from timing patterns. |
| Is recoverable value real revenue? | No — modelled under stated recovery / feasibility assumptions. |
| Why not ML? | Transparent rules first; ML when we have labelled OpCo outcomes. |
| Why South Africa? | Representative multi-region OpCo story; method ports across markets. |
| Who uses it? | Analysts rank; acquisition leads run pipeline; admins refresh/import data. |

---

## Accounts (local / demo)

| Email | Password | Show |
| --- | --- | --- |
| `lead@mtn.demo` | `lead123` | Main demo (national) |
| `viewer@mtn.demo` | `viewer123` | Region scope (Gauteng) |
| `analyst@mtn.demo` | `analyst123` | WC ranking / simulator |
| `admin@mtn.demo` | `admin123` | Refresh + CSV import |
