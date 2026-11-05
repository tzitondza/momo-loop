"""Generate synthetic MoMo transaction data for MoMo Loop PoC (South Africa context)."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
N_CUSTOMERS = 800
N_TRANSACTIONS = 6000
START = datetime(2026, 9, 1, 6, 0, 0)

# Deliberately planted acceptance gaps (ground truth for ranking evaluation)
GAP_LOCATIONS = {"LOC03", "LOC07", "LOC11"}  # Alexandra, Diepsloot, Khayelitsha Site C
GAP_CATEGORIES = {"Grocery", "Transport", "Pharmacy", "Hardware"}

LOCATIONS = [
    {"location_id": "LOC01", "name": "Johannesburg CBD", "region": "Gauteng", "lat": -26.2041, "lng": 28.0473, "urban": True},
    {"location_id": "LOC02", "name": "Sandton", "region": "Gauteng", "lat": -26.1076, "lng": 28.0567, "urban": True},
    {"location_id": "LOC03", "name": "Alexandra", "region": "Gauteng", "lat": -26.1033, "lng": 28.0975, "urban": True},
    {"location_id": "LOC04", "name": "Soweto (Orlando)", "region": "Gauteng", "lat": -26.2485, "lng": 27.8540, "urban": True},
    {"location_id": "LOC05", "name": "Tembisa", "region": "Gauteng", "lat": -25.9964, "lng": 28.2268, "urban": False},
    {"location_id": "LOC06", "name": "Pretoria CBD", "region": "Gauteng", "lat": -25.7479, "lng": 28.2293, "urban": True},
    {"location_id": "LOC07", "name": "Diepsloot", "region": "Gauteng", "lat": -25.9333, "lng": 28.0167, "urban": False},
    {"location_id": "LOC08", "name": "Durban CBD", "region": "KwaZulu-Natal", "lat": -29.8587, "lng": 31.0218, "urban": True},
    {"location_id": "LOC09", "name": "Umlazi", "region": "KwaZulu-Natal", "lat": -29.9667, "lng": 30.8833, "urban": False},
    {"location_id": "LOC10", "name": "Cape Town CBD", "region": "Western Cape", "lat": -33.9249, "lng": 18.4241, "urban": True},
    {"location_id": "LOC11", "name": "Khayelitsha Site C", "region": "Western Cape", "lat": -34.0400, "lng": 18.6800, "urban": False},
    {"location_id": "LOC12", "name": "Mitchells Plain", "region": "Western Cape", "lat": -34.0500, "lng": 18.6167, "urban": False},
]

CATEGORIES = [
    "Grocery",
    "Transport",
    "Pharmacy",
    "Hardware",
    "Fuel",
    "Restaurant",
    "Airtime Agent",
    "Wholesale Supplier",
]


def merchant_accepts(location_id: str, category: str, merchant_idx: int) -> bool:
    """Ground-truth acceptance: plant gaps in selected location×category combos."""
    if location_id in GAP_LOCATIONS and category in GAP_CATEGORIES:
        # Mostly non-accepting in planted gaps
        return merchant_idx % 5 == 0
    if category == "Airtime Agent":
        return True
    if location_id in {"LOC01", "LOC02", "LOC04"}:
        return merchant_idx % 4 != 0  # better coverage in urban hubs
    return merchant_idx % 3 != 0


def main() -> None:
    rng = random.Random(SEED)
    out = Path(__file__).parent

    # Merchants
    merchants = []
    mid = 1
    for loc in LOCATIONS:
        for cat in CATEGORIES:
            count = 3 if loc["urban"] else 2
            for i in range(count):
                accepts = merchant_accepts(loc["location_id"], cat, mid)
                merchants.append(
                    {
                        "merchant_id": f"M{mid:04d}",
                        "name": f"{cat} #{i + 1} — {loc['name']}",
                        "location_id": loc["location_id"],
                        "merchant_category": cat,
                        "accepts_momo": "Yes" if accepts else "No",
                        "is_planted_gap": str(
                            loc["location_id"] in GAP_LOCATIONS
                            and cat in GAP_CATEGORIES
                            and not accepts
                        ),
                    }
                )
                mid += 1

    with (out / "locations.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["location_id", "name", "region", "lat", "lng", "urban"])
        w.writeheader()
        for loc in LOCATIONS:
            w.writerow({**loc, "urban": str(loc["urban"])})

    with (out / "merchants.csv").open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "merchant_id",
                "name",
                "location_id",
                "merchant_category",
                "accepts_momo",
                "is_planted_gap",
            ],
        )
        w.writeheader()
        w.writerows(merchants)

    customers = [f"C{i:04d}" for i in range(1, N_CUSTOMERS + 1)]
    # Prefer certain locations for cash-out journeys (signal strength)
    loc_weights = []
    for loc in LOCATIONS:
        w = 3.0 if loc["location_id"] in GAP_LOCATIONS else (2.0 if loc["urban"] else 1.0)
        loc_weights.append(w)

    accepting = [m for m in merchants if m["accepts_momo"] == "Yes"]
    non_accepting = [m for m in merchants if m["accepts_momo"] == "No"]

    transactions = []
    tx_id = 1
    t = START

    def add_tx(
        customer_id: str,
        tx_type: str,
        amount: float,
        ts: datetime,
        location_id: str,
        merchant_category: str = "",
        merchant_id: str = "",
        merchant_accepts_momo: str = "",
        related_inflow_id: str = "",
        minutes_after_inflow: str = "",
    ) -> str:
        nonlocal tx_id
        tid = f"TX{tx_id:06d}"
        transactions.append(
            {
                "transaction_id": tid,
                "customer_id": customer_id,
                "transaction_type": tx_type,
                "amount": round(amount, 2),
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "location_id": location_id,
                "merchant_category": merchant_category,
                "merchant_id": merchant_id,
                "merchant_accepts_momo": merchant_accepts_momo,
                "related_inflow_id": related_inflow_id,
                "minutes_after_inflow": minutes_after_inflow,
            }
        )
        tx_id += 1
        return tid

    while len(transactions) < N_TRANSACTIONS:
        customer = rng.choice(customers)
        loc = rng.choices(LOCATIONS, weights=loc_weights, k=1)[0]
        location_id = loc["location_id"]
        t += timedelta(minutes=rng.randint(1, 25))

        # Inflow (P2P receive or cash-in)
        inflow_type = rng.choice(["P2P", "P2P", "P2P", "cash-in"])
        amount = round(rng.uniform(50, 2500) if inflow_type == "P2P" else rng.uniform(100, 1500), 2)
        inflow_id = add_tx(customer, inflow_type, amount, t, location_id)

        # Outcome shortly after inflow
        roll = rng.random()
        # Higher cash-out probability in planted gap locations
        cashout_p = 0.55 if location_id in GAP_LOCATIONS else (0.28 if not loc["urban"] else 0.18)
        merchant_p = 0.22 if location_id in GAP_LOCATIONS else 0.42

        if roll < cashout_p:
            delay = rng.randint(2, 45)
            cash_amount = round(amount * rng.uniform(0.6, 1.0), 2)
            # Attach a "desired" category the customer likely needed (for gap analysis)
            desired_cat = rng.choice(list(GAP_CATEGORIES) if location_id in GAP_LOCATIONS else CATEGORIES[:5])
            add_tx(
                customer,
                "cash-out",
                cash_amount,
                t + timedelta(minutes=delay),
                location_id,
                merchant_category=desired_cat,
                merchant_accepts_momo="Unknown",
                related_inflow_id=inflow_id,
                minutes_after_inflow=str(delay),
            )
        elif roll < cashout_p + merchant_p:
            delay = rng.randint(5, 120)
            m = rng.choice(accepting if accepting else merchants)
            # Bias merchant to same location when possible
            same_loc = [x for x in accepting if x["location_id"] == location_id]
            if same_loc and rng.random() < 0.7:
                m = rng.choice(same_loc)
            pay_amount = round(min(amount, rng.uniform(20, amount)), 2)
            add_tx(
                customer,
                "merchant payment",
                pay_amount,
                t + timedelta(minutes=delay),
                m["location_id"],
                merchant_category=m["merchant_category"],
                merchant_id=m["merchant_id"],
                merchant_accepts_momo="Yes",
                related_inflow_id=inflow_id,
                minutes_after_inflow=str(delay),
            )
        else:
            # Transfer out / hold — sometimes a later cash-out elsewhere
            if rng.random() < 0.25:
                delay = rng.randint(60, 400)
                other = rng.choice(LOCATIONS)
                add_tx(
                    customer,
                    "cash-out",
                    round(amount * rng.uniform(0.3, 0.8), 2),
                    t + timedelta(minutes=delay),
                    other["location_id"],
                    merchant_category=rng.choice(CATEGORIES),
                    merchant_accepts_momo="Unknown",
                    related_inflow_id=inflow_id,
                    minutes_after_inflow=str(delay),
                )

        # Occasional standalone merchant payment (no linked inflow in window)
        if rng.random() < 0.15 and accepting:
            m = rng.choice(accepting)
            add_tx(
                customer,
                "merchant payment",
                round(rng.uniform(15, 400), 2),
                t + timedelta(minutes=rng.randint(1, 10)),
                m["location_id"],
                merchant_category=m["merchant_category"],
                merchant_id=m["merchant_id"],
                merchant_accepts_momo="Yes",
            )

    # Trim to target
    transactions = transactions[:N_TRANSACTIONS]

    with (out / "transactions.csv").open("w", newline="") as f:
        fields = [
            "transaction_id",
            "customer_id",
            "transaction_type",
            "amount",
            "timestamp",
            "location_id",
            "merchant_category",
            "merchant_id",
            "merchant_accepts_momo",
            "related_inflow_id",
            "minutes_after_inflow",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(transactions)

    print(f"Wrote {len(LOCATIONS)} locations, {len(merchants)} merchants, {len(transactions)} transactions")
    print(f"Planted gap locations: {sorted(GAP_LOCATIONS)}")
    print(f"Non-accepting merchants: {len(non_accepting)}")


if __name__ == "__main__":
    main()
