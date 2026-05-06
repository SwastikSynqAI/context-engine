"""
Demo seed script — populates the Context Engine intelligence layer with realistic
YourCompany data for video demos. Hits the live API at localhost:8000.

Run: python scripts/seed_intelligence.py
"""

import sys
import subprocess
import uuid as _uuid
from datetime import datetime, timedelta, timezone

import requests

BASE = "http://localhost:8000"
IDS = {}  # entity name → entity id


def post(path, payload, label=""):
    r = requests.post(f"{BASE}{path}", json=payload, timeout=15)
    if r.status_code not in (200, 201):
        print(f"  ✗ {label or path}: {r.status_code} {r.text[:200]}")
        return None
    print(f"  ✓ {label}")
    return r.json()


def check_api():
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        print(f"API health: {r.json().get('status', 'unknown')}")
        return True
    except Exception as e:
        print(f"Cannot reach API at {BASE}: {e}")
        return False


# ── 1. Buildings ──────────────────────────────────────────────────────────────

def seed_buildings():
    print("\n── Buildings ──")
    buildings = [
        {
            "type": "building",
            "name": "ContextCo Delhi East",
            "source": "google_sheets",
            "source_id": "bld-noida-s62",
            "confidence": 0.98,
            "attributes": {
                "city": "Noida", "micromarket": "Sector 62",
                "total_sqft": 120000, "total_seats": 800, "available_seats": 120,
                "floors": 6, "grade": "A+",
                "amenities": ["cafeteria", "gym", "lounge", "24x7_access", "power_backup"],
                "base_price_per_seat": 9500,
                "address": "Plot 7A, Sector 62, Noida, UP 201309",
                "metro_distance_mins": 3, "parking_slots": 200,
            },
        },
        {
            "type": "building",
            "name": "ContextCo Delhi North",
            "source": "google_sheets",
            "source_id": "bld-ggn-cc",
            "confidence": 0.97,
            "attributes": {
                "city": "Gurgaon", "micromarket": "Cyber City DLF Phase 2",
                "total_sqft": 85000, "total_seats": 580, "available_seats": 65,
                "floors": 4, "grade": "A+",
                "amenities": ["cafeteria", "rooftop_lounge", "24x7_access", "concierge", "power_backup"],
                "base_price_per_seat": 11500,
                "address": "Building 10B, DLF Cyber City, Gurugram, HR 122002",
                "metro_distance_mins": 5, "parking_slots": 150, "premium_location": True,
            },
        },
        {
            "type": "building",
            "name": "ContextCo Mumbai Hub",
            "source": "google_sheets",
            "source_id": "bld-bkc-mum",
            "confidence": 0.99,
            "attributes": {
                "city": "Mumbai", "micromarket": "Bandra Kurla Complex G Block",
                "total_sqft": 95000, "total_seats": 640, "available_seats": 80,
                "floors": 5, "grade": "A+",
                "amenities": ["cafeteria", "lounge", "podcast_studio", "24x7_access", "power_backup", "EV_charging"],
                "base_price_per_seat": 14000,
                "address": "G-Block, BKC, Bandra East, Mumbai 400051",
                "parking_slots": 120, "sea_view": True,
            },
        },
        {
            "type": "building",
            "name": "ContextCo Mumbai West",
            "source": "google_sheets",
            "source_id": "bld-powai-mum",
            "confidence": 0.96,
            "attributes": {
                "city": "Mumbai", "micromarket": "Hiranandani Business Park",
                "total_sqft": 68000, "total_seats": 460, "available_seats": 95,
                "floors": 4, "grade": "A",
                "amenities": ["cafeteria", "lounge", "24x7_access", "power_backup"],
                "base_price_per_seat": 11000,
                "address": "Lake Boulevard, Hiranandani Business Park, Powai 400076",
                "parking_slots": 100,
            },
        },
        {
            "type": "building",
            "name": "ContextCo Chennai",
            "source": "google_sheets",
            "source_id": "bld-omr-che",
            "confidence": 0.95,
            "attributes": {
                "city": "Chennai", "micromarket": "OMR Sholinganallur",
                "total_sqft": 60000, "total_seats": 420, "available_seats": 140,
                "floors": 3, "grade": "A",
                "amenities": ["cafeteria", "lounge", "24x7_access", "power_backup"],
                "base_price_per_seat": 8200,
                "address": "No 24, OMR Road, Sholinganallur, Chennai 600119",
                "parking_slots": 180,
            },
        },
    ]
    for b in buildings:
        result = post("/entities", b, b["name"])
        if result:
            IDS[b["name"]] = result["id"]


# ── 2. Clients ────────────────────────────────────────────────────────────────

def seed_clients():
    print("\n── Clients ──")
    clients = [
        {
            "type": "client", "name": "Zeta Tech",
            "source": "hubspot", "source_id": "hs-zeta-001", "confidence": 0.97,
            "pii_fields": [],
            "attributes": {
                "industry": "fintech", "sub_industry": "payments_infrastructure",
                "headcount": 420, "seats_required": 180, "location": "Noida",
                "funding_stage": "Series C", "funding_amount_usd": "120M",
                "funded_date": "2024-09", "icp_score": 0.91,
                "contract_value_inr": 20520000, "status": "active_tenant",
                "onboarded_date": "2024-11-01", "account_manager": "admin",
            },
        },
        {
            "type": "client", "name": "Groww",
            "source": "hubspot", "source_id": "hs-groww-002", "confidence": 0.99,
            "pii_fields": [],
            "attributes": {
                "industry": "fintech", "sub_industry": "wealthtech",
                "headcount": 1800, "seats_required": 220, "location": "Gurgaon",
                "funding_stage": "Listed", "icp_score": 0.88,
                "contract_value_inr": 30360000, "status": "active_tenant",
                "onboarded_date": "2024-08-15", "account_manager": "admin",
            },
        },
        {
            "type": "client", "name": "Razorpay",
            "source": "hubspot", "source_id": "hs-rzp-003", "confidence": 0.98,
            "pii_fields": [],
            "attributes": {
                "industry": "fintech", "sub_industry": "payment_gateway",
                "headcount": 3200, "seats_required": 200, "location": "Mumbai",
                "funding_stage": "Series F", "funding_amount_usd": "375M",
                "icp_score": 0.94, "contract_value_inr": 33600000,
                "status": "active_tenant", "onboarded_date": "2024-06-01",
                "account_manager": "admin",
            },
        },
        {
            "type": "client", "name": "Innoviti Technologies",
            "source": "hubspot", "source_id": "hs-innov-004", "confidence": 0.93,
            "pii_fields": [],
            "attributes": {
                "industry": "fintech", "sub_industry": "B2B_payments",
                "headcount": 380, "seats_required": 80, "location": "Noida",
                "funding_stage": "Series B", "funding_amount_usd": "45M",
                "funded_date": "2024-06", "icp_score": 0.82,
                "contract_value_inr": 9120000, "status": "active_tenant",
                "onboarded_date": "2025-01-10", "account_manager": "admin",
            },
        },
        {
            "type": "client", "name": "Pepper Content",
            "source": "hubspot", "source_id": "hs-pepper-005", "confidence": 0.90,
            "pii_fields": [],
            "attributes": {
                "industry": "saas", "sub_industry": "content_marketing",
                "headcount": 280, "seats_required": 65, "location": "Mumbai",
                "funding_stage": "Series B", "funding_amount_usd": "14.3M",
                "icp_score": 0.76, "contract_value_inr": 8580000,
                "status": "active_tenant", "onboarded_date": "2025-02-01",
                "account_manager": "admin",
            },
        },
        {
            "type": "client", "name": "Jar App",
            "source": "hubspot", "source_id": "hs-jar-006", "confidence": 0.94,
            "pii_fields": [],
            "attributes": {
                "industry": "fintech", "sub_industry": "micro_savings",
                "headcount": 350, "seats_required": 90, "location": "Gurgaon",
                "funding_stage": "Series C", "funding_amount_usd": "86M",
                "funded_date": "2024-11", "icp_score": 0.87,
                "contract_value_inr": 12420000, "status": "active_tenant",
                "onboarded_date": "2025-03-01", "account_manager": "admin",
            },
        },
        {
            "type": "client", "name": "Mintifi",
            "source": "hubspot", "source_id": "hs-mintifi-007", "confidence": 0.89,
            "pii_fields": [],
            "attributes": {
                "industry": "bfsi", "sub_industry": "supply_chain_finance",
                "headcount": 220, "seats_required": 75, "location": "Mumbai",
                "funding_stage": "Series C", "funding_amount_usd": "110M",
                "funded_date": "2025-01", "icp_score": 0.85,
                "contract_value_inr": 12600000, "status": "in_negotiation",
                "account_manager": "admin",
            },
        },
        {
            "type": "client", "name": "Plum",
            "source": "hubspot", "source_id": "hs-plum-008", "confidence": 0.91,
            "pii_fields": [],
            "attributes": {
                "industry": "insurtech", "sub_industry": "employee_benefits",
                "headcount": 180, "seats_required": 50, "location": "Gurgaon",
                "funding_stage": "Series B", "funding_amount_usd": "22M",
                "funded_date": "2025-02", "icp_score": 0.79,
                "contract_value_inr": 6900000, "status": "lead",
                "account_manager": "admin",
            },
        },
    ]
    for c in clients:
        result = post("/entities", c, c["name"])
        if result:
            IDS[c["name"]] = result["id"]


# ── 3. Brokers ────────────────────────────────────────────────────────────────

def seed_brokers():
    print("\n── Brokers ──")
    brokers = [
        {
            "type": "broker", "name": "PropConnect Realty",
            "source": "google_sheets", "source_id": "brk-propconnect", "confidence": 0.95,
            "pii_fields": ["phone"],
            "attributes": {
                "contact_person": "Rahul Sharma", "phone": "+91-9810123456",
                "city": "Delhi NCR", "specialisation": "managed_offices",
                "active_mandates": 14, "deals_closed_with_synq": 6,
                "avg_commission_pct": 1.5, "rating": 4.7,
            },
        },
        {
            "type": "broker", "name": "JLL India Corporate",
            "source": "google_sheets", "source_id": "brk-jll", "confidence": 0.98,
            "pii_fields": ["phone"],
            "attributes": {
                "contact_person": "Aman Mehta", "phone": "+91-9910234567",
                "city": "Pan India", "specialisation": "enterprise_office_leasing",
                "active_mandates": 42, "deals_closed_with_synq": 3,
                "avg_commission_pct": 2.0, "rating": 4.5,
            },
        },
        {
            "type": "broker", "name": "Cushman & Wakefield India",
            "source": "google_sheets", "source_id": "brk-cw", "confidence": 0.97,
            "pii_fields": ["phone"],
            "attributes": {
                "contact_person": "Kavita Nair", "phone": "+91-9820345678",
                "city": "Mumbai", "specialisation": "commercial_real_estate",
                "active_mandates": 28, "deals_closed_with_synq": 2,
                "avg_commission_pct": 1.75, "rating": 4.6,
            },
        },
    ]
    for b in brokers:
        result = post("/entities", b, b["name"])
        if result:
            IDS[b["name"]] = result["id"]


# ── 4. Vendors ────────────────────────────────────────────────────────────────

def seed_vendors():
    print("\n── Vendors ──")
    vendors = [
        {
            "type": "vendor", "name": "CleanPro Facility Services",
            "source": "google_sheets", "source_id": "vnd-cleanpro", "confidence": 0.96,
            "attributes": {
                "service_category": "housekeeping",
                "contract_start": "2024-01-01", "contract_value_monthly_inr": 840000,
                "buildings_covered": ["ContextCo Delhi East", "ContextCo Delhi North", "ContextCo Mumbai Hub"],
                "sla_uptime_pct": 98.2, "rating": 4.4,
            },
        },
        {
            "type": "vendor", "name": "SecureFirst India",
            "source": "google_sheets", "source_id": "vnd-securefirst", "confidence": 0.97,
            "attributes": {
                "service_category": "security_access_control",
                "contract_start": "2023-07-01", "contract_value_monthly_inr": 560000,
                "buildings_covered": ["ContextCo Delhi East", "ContextCo Delhi North", "ContextCo Mumbai Hub", "ContextCo Mumbai West"],
                "sla_uptime_pct": 99.5, "rating": 4.7,
            },
        },
        {
            "type": "vendor", "name": "BrewBridge Hospitality",
            "source": "google_sheets", "source_id": "vnd-brewbridge", "confidence": 0.92,
            "attributes": {
                "service_category": "cafeteria_pantry",
                "contract_start": "2024-04-01", "contract_value_monthly_inr": 1200000,
                "buildings_covered": ["ContextCo Delhi East", "ContextCo Delhi North", "ContextCo Mumbai Hub", "ContextCo Mumbai West", "ContextCo Chennai"],
                "avg_daily_covers": 1800, "rating": 4.6, "renewal_due": "2025-03-31",
            },
        },
        {
            "type": "vendor", "name": "TechSetup India",
            "source": "google_sheets", "source_id": "vnd-techsetup", "confidence": 0.94,
            "attributes": {
                "service_category": "IT_infrastructure",
                "contract_start": "2023-09-01", "contract_value_monthly_inr": 380000,
                "buildings_covered": ["ContextCo Mumbai Hub", "ContextCo Mumbai West", "ContextCo Chennai"],
                "sla_response_hours": 2, "rating": 4.3,
            },
        },
    ]
    for v in vendors:
        result = post("/entities", v, v["name"])
        if result:
            IDS[v["name"]] = result["id"]


# ── 5. Contacts ───────────────────────────────────────────────────────────────

def seed_contacts():
    print("\n── Contacts ──")
    contacts = [
        {
            "type": "contact", "name": "Aditi Sharma",
            "source": "hubspot", "source_id": "ct-aditi", "confidence": 0.96,
            "pii_fields": ["email", "phone"],
            "attributes": {
                "email": "aditi.sharma@zetatech.com", "phone": "+91-9871234560",
                "title": "Head of Workplace", "client": "Zeta Tech",
                "decision_maker": True, "preferred_contact": "email",
            },
        },
        {
            "type": "contact", "name": "Karan Gupta",
            "source": "hubspot", "source_id": "ct-karan", "confidence": 0.95,
            "pii_fields": ["email", "phone"],
            "attributes": {
                "email": "karan.gupta@groww.in", "phone": "+91-9872345671",
                "title": "VP Operations", "client": "Groww",
                "decision_maker": True, "preferred_contact": "whatsapp",
            },
        },
        {
            "type": "contact", "name": "Shreya Nair",
            "source": "hubspot", "source_id": "ct-shreya", "confidence": 0.97,
            "pii_fields": ["email", "phone"],
            "attributes": {
                "email": "shreya.nair@razorpay.com", "phone": "+91-9873456782",
                "title": "Director of Real Estate", "client": "Razorpay",
                "decision_maker": True, "preferred_contact": "email",
            },
        },
        {
            "type": "contact", "name": "Vivek Anand",
            "source": "hubspot", "source_id": "ct-vivek", "confidence": 0.91,
            "pii_fields": ["email", "phone"],
            "attributes": {
                "email": "vivek.anand@innoviti.com", "phone": "+91-9874567893",
                "title": "Admin & Facilities Manager", "client": "Innoviti Technologies",
                "decision_maker": False, "preferred_contact": "phone",
            },
        },
        {
            "type": "contact", "name": "Riya Desai",
            "source": "hubspot", "source_id": "ct-riya", "confidence": 0.93,
            "pii_fields": ["email", "phone"],
            "attributes": {
                "email": "riya.desai@mintifi.com", "phone": "+91-9875678904",
                "title": "CFO", "client": "Mintifi",
                "decision_maker": True, "preferred_contact": "email",
                "note": "Key decision maker for ongoing negotiation — very price-sensitive",
            },
        },
        {
            "type": "contact", "name": "Aakash Mehta",
            "source": "hubspot", "source_id": "ct-aakash", "confidence": 0.90,
            "pii_fields": ["email", "phone"],
            "attributes": {
                "email": "aakash.mehta@jarapp.com", "phone": "+91-9876789015",
                "title": "Head of People & Operations", "client": "Jar App",
                "decision_maker": True, "preferred_contact": "whatsapp",
            },
        },
    ]
    for c in contacts:
        result = post("/entities", c, c["name"])
        if result:
            IDS[c["name"]] = result["id"]


# ── 6. Deals ──────────────────────────────────────────────────────────────────

def seed_deals():
    print("\n── Deals ──")
    deals = [
        {
            "type": "deal", "name": "Zeta Tech — Noida S62 180-Seat",
            "source": "hubspot", "source_id": "deal-zeta-001", "confidence": 0.99,
            "attributes": {
                "client": "Zeta Tech", "building": "ContextCo Delhi East",
                "seats": 180, "price_per_seat_inr": 9500, "total_value_inr": 20520000,
                "tenure_months": 24, "status": "closed_won", "closed_date": "2024-10-28",
                "broker": "PropConnect Realty", "broker_commission_pct": 1.5,
                "lock_in_months": 12, "escalation_pct_pa": 5,
            },
        },
        {
            "type": "deal", "name": "Groww — Gurgaon Cyber City 220-Seat",
            "source": "hubspot", "source_id": "deal-groww-002", "confidence": 0.99,
            "attributes": {
                "client": "Groww", "building": "ContextCo Delhi North",
                "seats": 220, "price_per_seat_inr": 11500, "total_value_inr": 30360000,
                "tenure_months": 36, "status": "closed_won", "closed_date": "2024-08-10",
                "broker": "JLL India Corporate", "broker_commission_pct": 2.0,
                "lock_in_months": 18, "escalation_pct_pa": 5,
            },
        },
        {
            "type": "deal", "name": "Razorpay — BKC 200-Seat Premium",
            "source": "hubspot", "source_id": "deal-rzp-003", "confidence": 0.99,
            "attributes": {
                "client": "Razorpay", "building": "ContextCo Mumbai Hub",
                "seats": 200, "price_per_seat_inr": 14000, "total_value_inr": 33600000,
                "tenure_months": 24, "status": "closed_won", "closed_date": "2024-05-22",
                "broker": "Cushman & Wakefield India", "broker_commission_pct": 1.75,
                "lock_in_months": 12, "escalation_pct_pa": 6,
            },
        },
        {
            "type": "deal", "name": "Innoviti — Noida S62 80-Seat",
            "source": "hubspot", "source_id": "deal-innov-004", "confidence": 0.96,
            "attributes": {
                "client": "Innoviti Technologies", "building": "ContextCo Delhi East",
                "seats": 80, "price_per_seat_inr": 9500, "total_value_inr": 9120000,
                "tenure_months": 12, "status": "closed_won", "closed_date": "2025-01-05",
                "broker": "PropConnect Realty", "broker_commission_pct": 1.5,
                "direct_deal": True,
            },
        },
        {
            "type": "deal", "name": "Pepper Content — Powai 65-Seat",
            "source": "hubspot", "source_id": "deal-pepper-005", "confidence": 0.95,
            "attributes": {
                "client": "Pepper Content", "building": "ContextCo Mumbai West",
                "seats": 65, "price_per_seat_inr": 11000, "total_value_inr": 8580000,
                "tenure_months": 12, "status": "closed_won", "closed_date": "2025-01-28",
                "direct_deal": True, "lock_in_months": 6,
            },
        },
        {
            "type": "deal", "name": "Jar App — Gurgaon 90-Seat",
            "source": "hubspot", "source_id": "deal-jar-006", "confidence": 0.97,
            "attributes": {
                "client": "Jar App", "building": "ContextCo Delhi North",
                "seats": 90, "price_per_seat_inr": 11500, "total_value_inr": 12420000,
                "tenure_months": 24, "status": "closed_won", "closed_date": "2025-02-20",
                "broker": "PropConnect Realty", "broker_commission_pct": 1.5,
            },
        },
        {
            "type": "deal", "name": "Mintifi — BKC 75-Seat Negotiation",
            "source": "hubspot", "source_id": "deal-mintifi-007", "confidence": 0.72,
            "attributes": {
                "client": "Mintifi", "building": "ContextCo Mumbai Hub",
                "seats": 75, "asking_price_per_seat_inr": 14000,
                "proposed_price_per_seat_inr": 12880, "tenure_months": 24,
                "status": "in_negotiation", "broker": "Cushman & Wakefield India",
                "note": "Admin approved max 8% discount with CFO sign-off",
                "last_touchpoint": "2026-04-18",
            },
        },
        {
            "type": "deal", "name": "Plum — Gurgaon 50-Seat Prospect",
            "source": "hubspot", "source_id": "deal-plum-008", "confidence": 0.60,
            "attributes": {
                "client": "Plum", "building": "ContextCo Delhi North",
                "seats": 50, "asking_price_per_seat_inr": 11500, "tenure_months": 12,
                "status": "lead",
                "note": "Recently funded Series B — high ICP signal. First walkthrough scheduled.",
                "first_contact_date": "2026-04-10",
            },
        },
    ]
    for d in deals:
        result = post("/entities", d, d["name"])
        if result:
            IDS[d["name"]] = result["id"]


# ── 7. Spaces ─────────────────────────────────────────────────────────────────

def seed_spaces():
    print("\n── Spaces ──")
    spaces = [
        {
            "type": "space", "name": "Noida S62 — Floor 3 East Wing",
            "source": "google_sheets", "source_id": "spc-noida-3e", "confidence": 0.98,
            "attributes": {
                "building": "ContextCo Delhi East", "floor": 3, "wing": "East",
                "capacity_seats": 180, "occupied_by": "Zeta Tech", "sqft": 19800,
                "layout": "open_plan", "has_dedicated_reception": True, "status": "occupied",
            },
        },
        {
            "type": "space", "name": "Noida S62 — Floor 2 West Wing",
            "source": "google_sheets", "source_id": "spc-noida-2w", "confidence": 0.97,
            "attributes": {
                "building": "ContextCo Delhi East", "floor": 2, "wing": "West",
                "capacity_seats": 80, "occupied_by": "Innoviti Technologies", "sqft": 8800,
                "layout": "hybrid", "has_dedicated_reception": False, "status": "occupied",
            },
        },
        {
            "type": "space", "name": "Gurgaon CC — Floor 4 Full",
            "source": "google_sheets", "source_id": "spc-ggn-f4", "confidence": 0.98,
            "attributes": {
                "building": "ContextCo Delhi North", "floor": 4,
                "capacity_seats": 220, "occupied_by": "Groww", "sqft": 24200,
                "layout": "open_plan", "has_dedicated_reception": True,
                "has_board_room": True, "status": "occupied",
            },
        },
        {
            "type": "space", "name": "BKC — Floor 2 North",
            "source": "google_sheets", "source_id": "spc-bkc-f2n", "confidence": 0.99,
            "attributes": {
                "building": "ContextCo Mumbai Hub", "floor": 2, "wing": "North",
                "capacity_seats": 200, "occupied_by": "Razorpay", "sqft": 22000,
                "layout": "activity_based", "has_dedicated_reception": True,
                "has_board_room": True, "sea_facing": True, "status": "occupied",
            },
        },
        {
            "type": "space", "name": "Powai — Floor 1 South",
            "source": "google_sheets", "source_id": "spc-powai-f1s", "confidence": 0.96,
            "attributes": {
                "building": "ContextCo Mumbai West", "floor": 1,
                "capacity_seats": 65, "occupied_by": "Pepper Content",
                "sqft": 7150, "layout": "open_plan", "status": "occupied",
            },
        },
    ]
    for s in spaces:
        result = post("/entities", s, s["name"])
        if result:
            IDS[s["name"]] = result["id"]


# ── 8. Relationships ──────────────────────────────────────────────────────────

def seed_relationships():
    print("\n── Relationships ──")

    def rel(from_name, to_name, rel_type, metadata=None, confidence=0.95):
        from_id = IDS.get(from_name)
        to_id = IDS.get(to_name)
        if not from_id or not to_id:
            print(f"  ✗ Missing ID: {from_name!r} or {to_name!r}")
            return
        post(
            f"/entities/{from_id}/relationships",
            {"from_entity_id": from_id, "to_entity_id": to_id,
             "relationship_type": rel_type, "metadata": metadata or {},
             "confidence": confidence, "source": "google_sheets"},
            f"{from_name} --{rel_type}--> {to_name}",
        )

    # Tenants → Buildings
    rel("Zeta Tech", "ContextCo Delhi East", "tenant_of", {"since": "2024-11-01", "seats": 180})
    rel("Groww", "ContextCo Delhi North", "tenant_of", {"since": "2024-08-15", "seats": 220})
    rel("Razorpay", "ContextCo Mumbai Hub", "tenant_of", {"since": "2024-06-01", "seats": 200})
    rel("Innoviti Technologies", "ContextCo Delhi East", "tenant_of", {"since": "2025-01-10", "seats": 80})
    rel("Pepper Content", "ContextCo Mumbai West", "tenant_of", {"since": "2025-02-01", "seats": 65})
    rel("Jar App", "ContextCo Delhi North", "tenant_of", {"since": "2025-03-01", "seats": 90})

    # Contacts → Clients
    rel("Aditi Sharma", "Zeta Tech", "contact_at", {"role": "Head of Workplace"})
    rel("Karan Gupta", "Groww", "contact_at", {"role": "VP Operations"})
    rel("Shreya Nair", "Razorpay", "contact_at", {"role": "Director of Real Estate"})
    rel("Vivek Anand", "Innoviti Technologies", "contact_at", {"role": "Admin & Facilities"})
    rel("Riya Desai", "Mintifi", "contact_at", {"role": "CFO"})
    rel("Aakash Mehta", "Jar App", "contact_at", {"role": "Head of People & Operations"})

    # Spaces → Buildings
    rel("Noida S62 — Floor 3 East Wing", "ContextCo Delhi East", "located_in", {"floor": 3})
    rel("Noida S62 — Floor 2 West Wing", "ContextCo Delhi East", "located_in", {"floor": 2})
    rel("Gurgaon CC — Floor 4 Full", "ContextCo Delhi North", "located_in", {"floor": 4})
    rel("BKC — Floor 2 North", "ContextCo Mumbai Hub", "located_in", {"floor": 2})
    rel("Powai — Floor 1 South", "ContextCo Mumbai West", "located_in", {"floor": 1})

    # Deals → Clients / Buildings
    rel("Zeta Tech — Noida S62 180-Seat", "Zeta Tech", "part_of_deal", {"role": "client"})
    rel("Zeta Tech — Noida S62 180-Seat", "ContextCo Delhi East", "part_of_deal", {"role": "property"})
    rel("Groww — Gurgaon Cyber City 220-Seat", "Groww", "part_of_deal", {"role": "client"})
    rel("Groww — Gurgaon Cyber City 220-Seat", "ContextCo Delhi North", "part_of_deal", {"role": "property"})
    rel("Razorpay — BKC 200-Seat Premium", "Razorpay", "part_of_deal", {"role": "client"})
    rel("Razorpay — BKC 200-Seat Premium", "ContextCo Mumbai Hub", "part_of_deal", {"role": "property"})
    rel("Mintifi — BKC 75-Seat Negotiation", "Mintifi", "part_of_deal", {"role": "client"})
    rel("Mintifi — BKC 75-Seat Negotiation", "ContextCo Mumbai Hub", "part_of_deal", {"role": "property"})

    # Brokers → Deals
    rel("PropConnect Realty", "Zeta Tech — Noida S62 180-Seat", "broker_for", {"commission_pct": 1.5})
    rel("JLL India Corporate", "Groww — Gurgaon Cyber City 220-Seat", "broker_for", {"commission_pct": 2.0})
    rel("Cushman & Wakefield India", "Razorpay — BKC 200-Seat Premium", "broker_for", {"commission_pct": 1.75})
    rel("PropConnect Realty", "Innoviti — Noida S62 80-Seat", "broker_for", {"commission_pct": 1.5})
    rel("Cushman & Wakefield India", "Mintifi — BKC 75-Seat Negotiation", "broker_for", {"commission_pct": 1.75})

    # Vendors → Buildings
    for bld in ["ContextCo Delhi East", "ContextCo Delhi North", "ContextCo Mumbai Hub"]:
        rel("CleanPro Facility Services", bld, "vendor_for", {"service": "housekeeping"})
    for bld in ["ContextCo Delhi East", "ContextCo Delhi North", "ContextCo Mumbai Hub", "ContextCo Mumbai West"]:
        rel("SecureFirst India", bld, "vendor_for", {"service": "security"})
    for bld in ["ContextCo Delhi East", "ContextCo Delhi North", "ContextCo Mumbai Hub", "ContextCo Mumbai West", "ContextCo Chennai"]:
        rel("BrewBridge Hospitality", bld, "vendor_for", {"service": "cafeteria"})
    for bld in ["ContextCo Mumbai Hub", "ContextCo Mumbai West", "ContextCo Chennai"]:
        rel("TechSetup India", bld, "vendor_for", {"service": "IT_infrastructure"})


# ── 9. Expert Decisions ───────────────────────────────────────────────────────

def seed_decisions():
    print("\n── Expert Decisions ──")
    decisions = [
        {
            "decision_type": "lead_approval", "actor": "admin",
            "human_action": "Approved Razorpay as high-priority lead — fintech Series F, 200 seats, BKC",
            "human_reasoning": "Series F fintech in BKC is exactly our ICP. Brand name win. Push to close within Q2.",
            "primary_entity_id": IDS.get("Razorpay"),
            "context_snapshot": {"lead": {"name": "Razorpay", "industry": "fintech", "seats": 200, "funding_stage": "Series F"}, "icp_match_score": 0.94},
        },
        {
            "decision_type": "deal_closure", "actor": "admin",
            "human_action": "Closed Razorpay at ₹14,000/seat — no discount, 24-month, 6% escalation",
            "human_reasoning": "BKC premium justified. Competitor quoted higher. Strong value signal and brand fit.",
            "primary_entity_id": IDS.get("Razorpay"),
            "context_snapshot": {"deal": {"client": "Razorpay", "seats": 200}, "wework_benchmark": 15500, "approved_rate": 14000},
        },
        {
            "decision_type": "lead_approval", "actor": "admin",
            "human_action": "Approved Zeta Tech — Series C fintech, 180 seats Noida, strong team pedigree",
            "human_reasoning": "Ex-Visa, ex-Razorpay founders. Series C funding last month means headcount growth imminent. Good 2-year lock-in candidate.",
            "primary_entity_id": IDS.get("Zeta Tech"),
            "context_snapshot": {"lead": {"name": "Zeta Tech", "industry": "fintech", "seats": 180, "funded_recently": True}, "icp_match_score": 0.91},
        },
        {
            "decision_type": "pricing_decision", "actor": "admin",
            "human_action": "Approved Zeta Tech at ₹9,500/seat — standard Noida S62 rate, no discount",
            "human_reasoning": "No broker pressure. Only one competing option (Awfis Sector 58 at ₹9,200). Standard rate holds.",
            "primary_entity_id": IDS.get("Zeta Tech"),
            "context_snapshot": {"standard_rate": 9500, "competitor_rate": 9200, "decision": "hold_standard"},
        },
        {
            "decision_type": "deal_closure", "actor": "admin",
            "human_action": "Closed Groww at ₹11,500/seat — 36-month tenure, JLL brokered",
            "human_reasoning": "Listed company, stable ARR. 36-month preferred by them. JLL at 2% fair for deal size.",
            "primary_entity_id": IDS.get("Groww"),
            "context_snapshot": {"deal": {"client": "Groww", "seats": 220, "total_value": 30360000}, "tenure": "36 months"},
        },
        {
            "decision_type": "lead_rejection", "actor": "admin",
            "human_action": "Rejected IndiaMart inquiry — 15 seats, wrong profile, SME",
            "human_reasoning": "15 seats is below our minimum. Redirecting to hot-desk product. Not our ICP.",
            "primary_entity_id": None,
            "context_snapshot": {"lead": {"seats": 15, "industry": "ecommerce"}, "reason": "below_minimum_seat_threshold"},
        },
        {
            "decision_type": "vendor_selection", "actor": "admin",
            "human_action": "Selected BrewBridge Hospitality for all 5 buildings — pan-India cafeteria",
            "human_reasoning": "BrewBridge beat 3 competitors on quality score (4.6 vs avg 3.9) and offered 15% volume discount. 6-month Mumbai pilot had zero complaints.",
            "primary_entity_id": IDS.get("BrewBridge Hospitality"),
            "context_snapshot": {"vendor": "BrewBridge", "monthly_inr": 1200000, "quality_score": 4.6, "discount_pct": 15},
        },
        {
            "decision_type": "pricing_decision", "actor": "admin",
            "human_action": "Approved 8% discount for Mintifi — max allowed, conditional on 24-month lock-in and CFO sign-off",
            "human_reasoning": "NBFC in BKC with 75 seats at ₹12,880 is still above our floor. Lock-in de-risks the discount. Do not go below ₹12,800.",
            "primary_entity_id": IDS.get("Mintifi"),
            "context_snapshot": {"standard_rate": 14000, "approved_discount_pct": 8, "approved_rate": 12880, "floor": 12800},
        },
        {
            "decision_type": "lead_approval", "actor": "admin",
            "human_action": "Approved Jar App — Series C fintech savings, 90 seats Gurgaon",
            "human_reasoning": "Series C in Nov 2024 means scaling fast. 90 seats, perfect mid-size deal. Strong ICP.",
            "primary_entity_id": IDS.get("Jar App"),
            "context_snapshot": {"lead": {"name": "Jar App", "industry": "fintech", "seats": 90, "funded_recently": True}, "icp_match_score": 0.87},
        },
        {
            "decision_type": "broker_commission", "actor": "admin",
            "human_action": "Approved PropConnect commission at 1.5% for Jar App deal — ₹186,300",
            "human_reasoning": "Standard rate for sub-₹2Cr deals. PropConnect brought them inbound so full commission is fair.",
            "primary_entity_id": IDS.get("PropConnect Realty"),
            "context_snapshot": {"broker": "PropConnect Realty", "commission_pct": 1.5, "commission_inr": 186300},
        },
        {
            "decision_type": "deal_closure", "actor": "admin",
            "human_action": "Closed Innoviti at ₹9,500/seat — 12-month, direct (no broker)",
            "human_reasoning": "Inbound via LinkedIn. No broker saves commission. Short term OK — Series B companies usually expand.",
            "primary_entity_id": IDS.get("Innoviti Technologies"),
            "context_snapshot": {"direct_deal": True, "tenure": "12 months", "expansion_probability": "high"},
        },
        {
            "decision_type": "lead_rejection", "actor": "admin",
            "human_action": "Rejected co-working arbitrage inquiry — third-party operator wanting to sub-let",
            "human_reasoning": "Sub-tenants violate our direct tenant model. Rejected and encoding as a standing rule.",
            "primary_entity_id": None,
            "context_snapshot": {"lead_type": "operator_sublease", "seats": 200, "note": "encode as rule"},
        },
    ]

    decision_ids = []
    for d in decisions:
        result = post("/context/decisions", d, d["human_action"][:60])
        if result:
            decision_ids.append(result["id"])

    # Record outcomes
    outcomes = [
        (0, "success", "Razorpay signed within 3 weeks — anchor tenant for BKC", "positive"),
        (1, "success", "Deal closed, tenant moved in on time, zero escalations", "positive"),
        (2, "success", "Zeta Tech onboarded, added 20 extra seats in month 3", "positive"),
        (3, "success", "Standard rate held — no churn in first 12 months", "positive"),
        (4, "success", "Groww signed 36-month — highest tenure deal to date", "positive"),
        (6, "success", "BrewBridge across all 5 buildings — tenant NPS up 12pts", "positive"),
        (8, "success", "Jar App signed, expanding to 120 seats Q3 2026", "positive"),
        (10, "success", "Innoviti moved in, already requesting 20 additional seats", "positive"),
    ]
    for idx, outcome, notes, signal in outcomes:
        if idx < len(decision_ids):
            requests.patch(
                f"{BASE}/context/decisions/{decision_ids[idx]}/outcome",
                json={"outcome": outcome, "outcome_notes": notes, "feedback_signal": signal},
                timeout=10,
            )
    print("  ✓ Outcomes recorded on 8 decisions")


# ── 10. Rules ─────────────────────────────────────────────────────────────────

def seed_rules():
    print("\n── Rules ──")
    rules = [
        {
            "name": "Priority: recently-funded BFSI / fintech companies",
            "reasoning": "Admin approved 4 consecutive fintech leads funded within 6 months. All 4 closed. Fresh funding means headcount growth and office urgency.",
            "condition": {"industry_in": ["bfsi", "fintech", "insurtech"], "funded_within_months": 6},
            "action": {"priority": "high", "icp_signal": "strong", "flag_for": "admin"},
            "created_by": "admin",
        },
        {
            "name": "Enterprise pricing review: deals ≥ 500 seats",
            "reasoning": "Deals above 500 seats affect building utilization materially. Standard rack rate may leave revenue on the table.",
            "condition": {"entity_type": "deal", "deal_seats_gte": 500},
            "action": {"apply_pricing_tier": "enterprise", "flag_for": "admin", "note": "Custom pricing required"},
            "created_by": "admin",
        },
        {
            "name": "Source preference: HubSpot headcount over Google Sheets",
            "reasoning": "When HubSpot and Sheets disagree on headcount, HubSpot is more current — sales team updates it directly from client calls. Sheets lags by 1-2 quarters.",
            "condition": {"entity_type": "client", "field_name": "headcount", "sources_conflict": True},
            "action": {"prefer_source": "hubspot", "over": "google_sheets"},
            "created_by": "admin",
        },
        {
            "name": "Broker commission cap: 2 months rent for deals above ₹1Cr",
            "reasoning": "JLL tried to claim 2.5% on the Groww deal. We capped at 2 months rent. Encoding as a standing cap.",
            "condition": {"entity_type": "deal", "deal_value_inr_gte": 10000000},
            "action": {"max_broker_commission": "2_months_rent"},
            "created_by": "admin",
        },
        {
            "name": "Gurgaon Cyber City: 15% premium over base NCR rate",
            "reasoning": "Cyber City commands a sustained premium — metro connectivity, ITES cluster, brand value. Never price at standard NCR rates.",
            "condition": {"entity_type": "deal", "building": "ContextCo Delhi North"},
            "action": {"apply_location_premium_pct": 15, "note": "Verify with Admin if client pushes back"},
            "created_by": "admin",
        },
        {
            "name": "No sub-leasing: auto-reject operator / arbitrage inquiries",
            "reasoning": "Admin rejected a 200-seat operator inquiry. Sub-tenants create complexity and violate our direct tenant model.",
            "condition": {"lead_type": "operator_sublease"},
            "action": {"auto_reject": True, "rejection_reason": "no_subletting_policy"},
            "created_by": "admin",
        },
    ]
    for r in rules:
        post("/rules", r, r["name"])


# ── 11. Data Conflicts ────────────────────────────────────────────────────────

def seed_conflicts():
    print("\n── Data Conflicts ──")

    if IDS.get("Groww"):
        r = post("/conflicts", {
            "entity_id": IDS["Groww"], "field_name": "headcount",
            "value_a": "1200", "source_a": "google_sheets",
            "value_b": "1800", "source_b": "hubspot",
        }, "Groww headcount conflict")
        if r:
            requests.post(f"{BASE}/conflicts/{r['id']}/resolve", json={
                "resolved_value": "1800", "resolved_by": "admin",
                "resolution_reasoning": "HubSpot reflects the latest BD call with Karan (VP Ops) who confirmed 1,800 headcount post Series E hiring push. Sheets hasn't been updated in 4 months.",
                "create_rule": False,
            }, timeout=10)
            print("  ✓ Groww conflict resolved")

    if IDS.get("Innoviti Technologies"):
        post("/conflicts", {
            "entity_id": IDS["Innoviti Technologies"], "field_name": "seats_required",
            "value_a": "80", "source_a": "hubspot",
            "value_b": "100", "source_b": "google_sheets",
        }, "Innoviti seats conflict (open)")

    if IDS.get("Mintifi"):
        post("/conflicts", {
            "entity_id": IDS["Mintifi"], "field_name": "funding_amount_usd",
            "value_a": "110M", "source_a": "hubspot",
            "value_b": "95M", "source_b": "document",
        }, "Mintifi funding amount conflict (open)")


# ── 12. Eval Cases ────────────────────────────────────────────────────────────

def seed_eval_cases():
    print("\n── Eval Cases ──")
    cases = [
        {
            "question": "What is our standard pricing for 100 seats in Gurgaon Cyber City?",
            "expected_themes": ["base price per seat", "Cyber City 15% premium", "comparable deals", "tenure impact"],
            "intent_type": "pricing_query", "min_expected_score": 0.75,
            "tags": ["pricing", "gurgaon"], "created_by": "admin",
        },
        {
            "question": "Which clients are in negotiation and what is the current status?",
            "expected_themes": ["Mintifi BKC negotiation", "8% discount approved", "CFO sign-off required", "floor rate ₹12,800"],
            "intent_type": "deal_status", "min_expected_score": 0.7,
            "tags": ["deals", "pipeline"], "created_by": "admin",
        },
        {
            "question": "Who are our top 3 clients by contract value and where are they?",
            "expected_themes": ["Razorpay BKC ₹3.36Cr", "Groww Gurgaon ₹3.04Cr", "Zeta Tech Noida ₹2.05Cr"],
            "intent_type": "client_lookup", "min_expected_score": 0.8,
            "tags": ["clients", "revenue"], "created_by": "admin",
        },
        {
            "question": "What vendors are active at BKC Mumbai and what are their SLA commitments?",
            "expected_themes": ["CleanPro housekeeping 98.2% SLA", "SecureFirst security 99.5% SLA", "BrewBridge cafeteria", "TechSetup IT 2hr response"],
            "intent_type": "vendor_lookup", "min_expected_score": 0.7,
            "tags": ["vendors", "operations"], "created_by": "admin",
        },
        {
            "question": "What is our ICP based on deals closed in the last fiscal year?",
            "expected_themes": ["fintech BFSI industry", "Series B to F funding", "50-250 seats", "NCR and Mumbai", "recently funded signal"],
            "intent_type": "icp_query", "min_expected_score": 0.75,
            "tags": ["icp", "strategy"], "created_by": "admin",
        },
        {
            "question": "Which buildings have more than 100 available seats right now?",
            "expected_themes": ["ContextCo Chennai 140 seats", "ContextCo Mumbai West 95 seats", "availability numbers"],
            "intent_type": "availability_query", "min_expected_score": 0.7,
            "tags": ["availability", "operations"], "created_by": "admin",
        },
        {
            "question": "Which broker did we use for Razorpay and what was their commission?",
            "expected_themes": ["Cushman & Wakefield India", "1.75% commission", "deal value ₹3.36Cr"],
            "intent_type": "deal_lookup", "min_expected_score": 0.8,
            "tags": ["deals", "brokers"], "created_by": "admin",
        },
        {
            "question": "Is Jar App likely to expand their current seat count?",
            "expected_themes": ["current 90 seats Gurgaon", "expansion signal 120 seats Q3 2026", "Series C growth trajectory"],
            "intent_type": "client_lookup", "min_expected_score": 0.7,
            "tags": ["clients", "expansion"], "created_by": "admin",
        },
    ]
    for c in cases:
        post("/evals/cases", c, c["question"][:60])


# ── 13. Eval Runs (direct DB insert) ─────────────────────────────────────────

def seed_eval_runs():
    print("\n── Eval Runs ──")
    runs = [
        {
            "id": str(_uuid.uuid4()),
            "triggered_by": "system",
            "run_at": (datetime.now(timezone.utc) - timedelta(days=21)).isoformat(),
            "cases_run": 8, "cases_passed": 5, "avg_score": 0.64,
            "delta_from_last": "NULL",
            "notes": "Baseline — limited entity data, no RLHF decisions yet",
        },
        {
            "id": str(_uuid.uuid4()),
            "triggered_by": "admin",
            "run_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            "cases_run": 8, "cases_passed": 6, "avg_score": 0.74,
            "delta_from_last": 10.0,
            "notes": "Post first batch of expert decisions — pricing and deal queries improved",
        },
        {
            "id": str(_uuid.uuid4()),
            "triggered_by": "admin",
            "run_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "cases_run": 8, "cases_passed": 7, "avg_score": 0.83,
            "delta_from_last": 9.0,
            "notes": "Rules + 12 decisions active — ICP and vendor queries now passing. Strong upward trend.",
        },
    ]
    for run in runs:
        sql = (
            f"INSERT INTO eval_runs (id, triggered_by, run_at, cases_run, cases_passed, avg_score, delta_from_last, notes) "
            f"VALUES ('{run['id']}', '{run['triggered_by']}', '{run['run_at']}', "
            f"{run['cases_run']}, {run['cases_passed']}, {run['avg_score']}, "
            f"{run['delta_from_last']}, $msg${run['notes']}$msg$) ON CONFLICT DO NOTHING;"
        )
        result = subprocess.run(
            ["docker", "exec", "context_engine_db", "psql", "-U", "appuser", "-d", "context_engine", "-c", sql],
            capture_output=True, text=True, timeout=10,
        )
        if "INSERT" in result.stdout:
            print(f"  ✓ Eval run: {run['notes'][:55]}")
        else:
            print(f"  ? {result.stdout.strip()} {result.stderr.strip()[:60]}")


# ── 14. Policy Rules ──────────────────────────────────────────────────────────

def seed_policies():
    print("\n── Policy Rules ──")
    policies = [
        {
            "name": "Pricing floor: ₹8,000/seat minimum",
            "description": "Never output a seat price below ₹8,000 without flagging. This is our floor across all markets including Chennai OMR.",
            "condition": {"answer_number_below": {"threshold": 8000}},
            "severity": "warn",
            "violation_message": "⚠️ Price cited is below the ₹8,000/seat floor. Verify before sharing with client.",
            "remediation": "Check the latest pricing sheet or consult Admin for a below-floor exception.",
            "created_by": "admin",
        },
        {
            "name": "Block PII in responses",
            "description": "Never include email addresses or phone numbers in context responses.",
            "condition": {"answer_contains": "@"},
            "severity": "block",
            "violation_message": "Response blocked: contains email address (PII). Redact before sharing.",
            "remediation": "Use name + title instead of email/phone in responses.",
            "created_by": "system",
        },
        {
            "name": "Flag competitor mentions",
            "description": "Flag any response that mentions WeWork, Awfis, or Indiqube by name.",
            "condition": {"answer_contains": "WeWork"},
            "severity": "flag",
            "violation_message": "Competitor name detected — review before sharing externally.",
            "remediation": "Use 'market comparables' instead of naming competitors in client-facing docs.",
            "created_by": "admin",
        },
        {
            "name": "Discount > 15% requires human approval",
            "description": "Flag any response discussing a discount above 15% for the admin's review.",
            "condition": {"question_contains": "discount"},
            "severity": "warn",
            "violation_message": "⚠️ Discount exceeds 15% — Admin's approval required before quoting.",
            "remediation": "Get explicit sign-off before responding to client.",
            "created_by": "admin",
        },
    ]
    for p in policies:
        post("/oversight/policies", p, p["name"])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Context Engine — Intelligence Layer Demo Seed")
    print("=" * 50)

    if not check_api():
        sys.exit(1)

    seed_buildings()
    seed_clients()
    seed_brokers()
    seed_vendors()
    seed_contacts()
    seed_deals()
    seed_spaces()
    seed_relationships()
    seed_decisions()
    seed_rules()
    seed_conflicts()
    seed_eval_cases()
    seed_eval_runs()
    seed_policies()

    print("\n" + "=" * 50)
    print("Done! Visit http://localhost:3001 to see the live data.")


if __name__ == "__main__":
    main()
