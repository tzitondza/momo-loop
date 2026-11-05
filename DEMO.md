# MoMo Loop — Presenter walkthrough

Follow this **top to bottom**. Do not skip ahead.  
**Account:** `lead@mtn.demo` / `lead123`  
**Before you start:** open the Render URL, wait until login loads (wake cold start with `/api/health` if needed).

Legend: **SAY** = speak · **CLICK** = do on screen · **POINT** = gesture only

---

## 0. Pre-flight (30 seconds, before judges look)

1. Open your deployed URL.  
2. Confirm login screen is visible.  
3. Keep this page on a second screen / phone as your script.  
4. Have `viewer@mtn.demo` / `viewer123` ready only if you have extra time.

---

## 1. Open — problem (≈20s)

**SAY:**  
“MoMo value often leaves the digital ecosystem. A customer receives money in their wallet, but the next merchant they need cannot accept MoMo — so they cash out, and the digital chain breaks.”

**SAY:**  
“MoMo Loop finds those probable cash-out boundaries and ranks where expanding merchant acceptance would keep the most value digital.”

---

## 2. Login (≈15s)

**CLICK:** Email → `lead@mtn.demo`  
**CLICK:** Password → `lead123`  
**CLICK:** Sign in  

**SAY:**  
“This is an internal acquisition tool — role-based access and territory scoping. I’m signed in as an acquisition lead with national view.”

Wait until **Overview** loads.

---

## 3. Overview — show the leak (≈40s)

You should be on **Overview**.

**POINT** at the main KPI cards (leakage / cash-out / recoverable / opportunities).

**SAY:**  
“Here’s the ecosystem view. We measure how much value sits behind probable cash-out boundaries — money that entered the wallet and exited as cash soon after — and how much we estimate could stay digital if acceptance expands.”

**POINT** at “last refreshed” / scope if visible.

**SAY:**  
“Data is synthetic for the PoC, refreshed from Postgres — same shape we’d use with anonymised OpCo feeds.”

---

## 4. Boundaries — show the signal (≈45s)

**CLICK:** nav → **Cash-out boundaries**

Wait for map / list to render.

**SAY:**  
“We detect a probable boundary when a wallet inflow is followed by a cash-out within thirty minutes. That is a signal — not proof that a merchant rejected MoMo.”

**CLICK:** select / open one hotspot or journey (first strong location on the list or map).

**SAY:**  
“These journeys highlight where digital spending likely stops. That’s where acceptance gaps matter most.”

---

## 5. Opportunities — show the ranking (≈45s)

**CLICK:** nav → **Opportunities**

Wait for the ranked table.

**POINT** at the **top row** — score and reason text.

**SAY:**  
“Opportunities are scored transparently — boundary value, affected customers, frequency, acceptance gap, and feasibility. Not a black box.”

**POINT** at estimated recoverable value on the top row.

**SAY:**  
“This is modelled recoverable value under stated assumptions — not claimed MTN revenue.”

**Optional if smooth:**  
**CLICK:** Export CSV or PDF  
**SAY:** “Acquisition teams can take this list into the field.”

**CLICK:** **Add to pipeline** on the top opportunity (or first available button).

---

## 6. Pipeline — show the workflow (≈40s)

**CLICK:** nav → **Acquisition pipeline**

**SAY:**  
“Insight becomes work. Identified opportunities move through reviewing, assigned, onboarded, and measured.”

**CLICK:** change status of the item you added → **reviewing** (or **assigned**).  
If there’s an assignee dropdown, pick a name.

**SAY:**  
“So merchant teams aren’t staring at a chart — they’re running a pipeline.”

---

## 7. Simulator — show the “what if” (≈40s)

**CLICK:** nav → **Impact simulator**

**CLICK:** pick the same location / category if prompted.  
**CLICK:** increase merchants to onboard and/or recovery slightly.  
Watch the projected numbers update.

**SAY:**  
“Before we commit field effort, we model retention lift under different onboarding assumptions.”

**CLICK:** save scenario (if the save form is visible).  
Name it something short like `Demo corridor`.

**SAY:**  
“Leads can save scenarios and come back to them.”

---

## 8. Close — ask (≈20s)

**SAY:**  
“Path forward: validate on anonymised MoMo data, pilot one corridor, and measure actual merchant-payment lift. MoMo Loop is how we choose where to act first.”

**STOP.** Smile. Hands off the mouse. Take questions.

---

## Extra time only (≈30s) — region scope

Only if judges still want more.

**CLICK:** Sign out  
**CLICK:** login `viewer@mtn.demo` / `viewer123`  
**SAY:** “Same product, Gauteng-only scope — how an OpCo viewer would see it.”  
**CLICK:** Sign out → back to `lead@mtn.demo` if needed for Q&A.

---

## If something breaks mid-demo

| Problem | Do this |
| --- | --- |
| Page spinning | Refresh once; say “waking the free-tier instance.” |
| Login fails | Re-type password carefully; try `admin@mtn.demo` / `admin123` as backup. |
| Wrong tab | Use the top nav labels exactly as written above. |
| Lost your place | Jump to the section heading you’re on — each section stands alone. |
| Blank map/table | Refresh that page; keep talking the SAY line while it loads. |

---

## Q&A cheat sheet (one line each)

- **Is every cash-out a failed merchant payment?** → No — probable boundary from timing, not proof.  
- **Is recoverable value real revenue?** → No — modelled under stated assumptions.  
- **Why not ML yet?** → Transparent rules first; ML when we have labelled OpCo outcomes.  
- **Who uses this?** → Analysts rank, leads run pipeline, admins refresh and import data.
