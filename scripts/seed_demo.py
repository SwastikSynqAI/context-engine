"""
Demo seed script — populates AI Hire with realistic dummy candidates for video demo.
Run: docker exec synq_api python /app/scripts/seed_demo.py
"""
import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
import random

STAGES = [
    "applied", "pre_screening", "pre_screened", "test_invited",
    "screened", "hr_approved", "shortlisted", "offer_sent", "hired", "rejected"
]

CANDIDATES = [
    # BD Managers
    {"name": "Arjun Mehta", "email": "arjun.mehta@gmail.com", "role": "bd_manager", "stage": "applied", "resume_score": None, "screen_score": None, "years_exp": 5, "current_ctc": 1200000, "expected_ctc": 1600000, "location": "Mumbai"},
    {"name": "Priya Sharma", "email": "priya.sharma@outlook.com", "role": "bd_manager", "stage": "applied", "resume_score": None, "screen_score": None, "years_exp": 4, "current_ctc": 900000, "expected_ctc": 1300000, "location": "Delhi NCR"},
    {"name": "Rohit Verma", "email": "rohit.verma@yahoo.com", "role": "bd_manager", "stage": "pre_screening", "resume_score": 72.5, "screen_score": None, "years_exp": 6, "current_ctc": 1500000, "expected_ctc": 2000000, "location": "Bangalore"},
    {"name": "Sneha Kapoor", "email": "sneha.kapoor@gmail.com", "role": "bd_manager", "stage": "pre_screening", "resume_score": 68.0, "screen_score": None, "years_exp": 3, "current_ctc": 800000, "expected_ctc": 1100000, "location": "Mumbai"},
    {"name": "Vikram Singh", "email": "vikram.singh@gmail.com", "role": "bd_manager", "stage": "pre_screened", "resume_score": 81.0, "screen_score": None, "years_exp": 7, "current_ctc": 1800000, "expected_ctc": 2400000, "location": "Delhi NCR"},
    {"name": "Ananya Iyer", "email": "ananya.iyer@gmail.com", "role": "bd_manager", "stage": "pre_screened", "resume_score": 76.5, "screen_score": None, "years_exp": 5, "current_ctc": 1200000, "expected_ctc": 1700000, "location": "Bangalore"},
    {"name": "Karan Malhotra", "email": "karan.malhotra@gmail.com", "role": "bd_manager", "stage": "test_invited", "resume_score": 84.0, "screen_score": None, "years_exp": 8, "current_ctc": 2000000, "expected_ctc": 2800000, "location": "Mumbai"},
    {"name": "Divya Nair", "email": "divya.nair@gmail.com", "role": "bd_manager", "stage": "test_invited", "resume_score": 79.0, "screen_score": None, "years_exp": 6, "current_ctc": 1400000, "expected_ctc": 1900000, "location": "Bangalore"},
    {"name": "Rahul Gupta", "email": "rahul.gupta@gmail.com", "role": "bd_manager", "stage": "screened", "resume_score": 88.5, "screen_score": 82.0, "years_exp": 9, "current_ctc": 2200000, "expected_ctc": 3000000, "location": "Delhi NCR"},
    {"name": "Pooja Bhatia", "email": "pooja.bhatia@gmail.com", "role": "bd_manager", "stage": "screened", "resume_score": 83.0, "screen_score": 77.5, "years_exp": 7, "current_ctc": 1700000, "expected_ctc": 2300000, "location": "Mumbai"},
    {"name": "Aditya Khanna", "email": "aditya.khanna@gmail.com", "role": "bd_manager", "stage": "hr_approved", "resume_score": 91.0, "screen_score": 86.0, "years_exp": 10, "current_ctc": 2500000, "expected_ctc": 3400000, "location": "Delhi NCR"},
    {"name": "Meera Pillai", "email": "meera.pillai@gmail.com", "role": "bd_manager", "stage": "shortlisted", "resume_score": 93.5, "screen_score": 89.0, "years_exp": 11, "current_ctc": 2800000, "expected_ctc": 3600000, "location": "Bangalore"},
    {"name": "Suresh Rao", "email": "suresh.rao@gmail.com", "role": "bd_manager", "stage": "offer_sent", "resume_score": 95.0, "screen_score": 91.5, "years_exp": 12, "current_ctc": 3000000, "expected_ctc": 4000000, "location": "Mumbai"},
    {"name": "Kavya Reddy", "email": "kavya.reddy@gmail.com", "role": "bd_manager", "stage": "hired", "resume_score": 96.0, "screen_score": 93.0, "years_exp": 8, "current_ctc": 2200000, "expected_ctc": 3000000, "location": "Bangalore"},
    {"name": "Nikhil Joshi", "email": "nikhil.joshi@gmail.com", "role": "bd_manager", "stage": "rejected", "resume_score": 42.0, "screen_score": None, "years_exp": 1, "current_ctc": 400000, "expected_ctc": 900000, "location": "Pune"},
    {"name": "Ritu Saxena", "email": "ritu.saxena@gmail.com", "role": "bd_manager", "stage": "rejected", "resume_score": 55.0, "screen_score": None, "years_exp": 2, "current_ctc": 600000, "expected_ctc": 1200000, "location": "Hyderabad"},

    # Operations Managers
    {"name": "Amit Patel", "email": "amit.patel@gmail.com", "role": "operations_manager", "stage": "applied", "resume_score": None, "screen_score": None, "years_exp": 6, "current_ctc": 1100000, "expected_ctc": 1500000, "location": "Bangalore"},
    {"name": "Sunita Yadav", "email": "sunita.yadav@gmail.com", "role": "operations_manager", "stage": "applied", "resume_score": None, "screen_score": None, "years_exp": 4, "current_ctc": 850000, "expected_ctc": 1200000, "location": "Mumbai"},
    {"name": "Manoj Kumar", "email": "manoj.kumar@gmail.com", "role": "operations_manager", "stage": "pre_screening", "resume_score": 70.0, "screen_score": None, "years_exp": 7, "current_ctc": 1400000, "expected_ctc": 1900000, "location": "Delhi NCR"},
    {"name": "Lakshmi Venkat", "email": "lakshmi.venkat@gmail.com", "role": "operations_manager", "stage": "pre_screened", "resume_score": 78.5, "screen_score": None, "years_exp": 8, "current_ctc": 1600000, "expected_ctc": 2100000, "location": "Chennai"},
    {"name": "Deepak Mishra", "email": "deepak.mishra@gmail.com", "role": "operations_manager", "stage": "test_invited", "resume_score": 82.0, "screen_score": None, "years_exp": 9, "current_ctc": 1900000, "expected_ctc": 2500000, "location": "Bangalore"},
    {"name": "Geeta Sharma", "email": "geeta.sharma@gmail.com", "role": "operations_manager", "stage": "screened", "resume_score": 86.5, "screen_score": 80.0, "years_exp": 10, "current_ctc": 2100000, "expected_ctc": 2800000, "location": "Mumbai"},
    {"name": "Sanjay Tiwari", "email": "sanjay.tiwari@gmail.com", "role": "operations_manager", "stage": "hr_approved", "resume_score": 89.0, "screen_score": 84.5, "years_exp": 11, "current_ctc": 2300000, "expected_ctc": 3100000, "location": "Delhi NCR"},
    {"name": "Rekha Nambiar", "email": "rekha.nambiar@gmail.com", "role": "operations_manager", "stage": "hired", "resume_score": 94.0, "screen_score": 90.0, "years_exp": 13, "current_ctc": 2800000, "expected_ctc": 3500000, "location": "Bangalore"},
    {"name": "Prasad Kulkarni", "email": "prasad.kulkarni@gmail.com", "role": "operations_manager", "stage": "rejected", "resume_score": 48.0, "screen_score": None, "years_exp": 2, "current_ctc": 500000, "expected_ctc": 1000000, "location": "Pune"},

    # Marketing
    {"name": "Ishaan Choudhury", "email": "ishaan.choudhury@gmail.com", "role": "marketing", "stage": "applied", "resume_score": None, "screen_score": None, "years_exp": 4, "current_ctc": 900000, "expected_ctc": 1300000, "location": "Bangalore"},
    {"name": "Tanvi Shah", "email": "tanvi.shah@gmail.com", "role": "marketing", "stage": "pre_screening", "resume_score": 74.0, "screen_score": None, "years_exp": 5, "current_ctc": 1100000, "expected_ctc": 1600000, "location": "Mumbai"},
    {"name": "Ashwin Menon", "email": "ashwin.menon@gmail.com", "role": "marketing", "stage": "screened", "resume_score": 85.0, "screen_score": 79.0, "years_exp": 6, "current_ctc": 1400000, "expected_ctc": 1900000, "location": "Delhi NCR"},
    {"name": "Pallavi Desai", "email": "pallavi.desai@gmail.com", "role": "marketing", "stage": "rejected", "resume_score": 51.0, "screen_score": None, "years_exp": 1, "current_ctc": 450000, "expected_ctc": 800000, "location": "Ahmedabad"},

    # Finance
    {"name": "Vivek Agarwal", "email": "vivek.agarwal@gmail.com", "role": "finance", "stage": "applied", "resume_score": None, "screen_score": None, "years_exp": 5, "current_ctc": 1000000, "expected_ctc": 1400000, "location": "Delhi NCR"},
    {"name": "Anjali Bhatt", "email": "anjali.bhatt@gmail.com", "role": "finance", "stage": "pre_screened", "resume_score": 80.0, "screen_score": None, "years_exp": 7, "current_ctc": 1500000, "expected_ctc": 2000000, "location": "Mumbai"},
    {"name": "Ramesh Nair", "email": "ramesh.nair@gmail.com", "role": "finance", "stage": "screened", "resume_score": 88.0, "screen_score": 82.5, "years_exp": 9, "current_ctc": 2000000, "expected_ctc": 2700000, "location": "Bangalore"},

    # IT
    {"name": "Tarun Bansal", "email": "tarun.bansal@gmail.com", "role": "it", "stage": "applied", "resume_score": None, "screen_score": None, "years_exp": 4, "current_ctc": 900000, "expected_ctc": 1400000, "location": "Hyderabad"},
    {"name": "Shruti Pandey", "email": "shruti.pandey@gmail.com", "role": "it", "stage": "test_invited", "resume_score": 83.0, "screen_score": None, "years_exp": 6, "current_ctc": 1600000, "expected_ctc": 2200000, "location": "Bangalore"},
    {"name": "Naveen Rajan", "email": "naveen.rajan@gmail.com", "role": "it", "stage": "rejected", "resume_score": 44.0, "screen_score": None, "years_exp": 1, "current_ctc": 400000, "expected_ctc": 900000, "location": "Chennai"},
]


async def seed():
    import sys
    sys.path.insert(0, "/app")

    from src.database import async_session_factory
    from sqlalchemy import text

    print(f"Seeding {len(CANDIDATES)} demo candidates...")

    base_time = datetime.now(UTC) - timedelta(days=45)

    async with async_session_factory() as db:
        for i, c in enumerate(CANDIDATES):
            entity_id = str(uuid.uuid4())
            app_id = str(uuid.uuid4())
            created_at = base_time + timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            updated_at = created_at + timedelta(days=random.randint(1, 10))

            attrs = json.dumps({
                "name": c["name"],
                "email": c["email"],
                "phone": f"+91 98{random.randint(10000000, 99999999)}",
                "location": c["location"],
                "years_experience": c["years_exp"],
                "current_ctc": c["current_ctc"],
                "expected_ctc": c["expected_ctc"],
                "role": c["role"],
                "source": "careers_form",
                "application_answer": f"I'm excited about YourCompany's growth in managed office spaces and believe my {c['years_exp']} years of experience will add significant value.",
            })

            # Upsert entity
            await db.execute(
                text("""
                    INSERT INTO entities (id, type, name, source, source_id, attributes, pii_fields, confidence, created_at, updated_at)
                    VALUES (:id, 'candidate', :name, 'careers_form', :email, CAST(:attrs AS jsonb), '["email","phone"]'::jsonb, 1.0, :created, :updated)
                    ON CONFLICT (source, source_id) DO NOTHING
                """),
                {"id": entity_id, "name": c["name"], "email": c["email"], "attrs": attrs, "created": created_at, "updated": updated_at},
            )

            # Check if entity was inserted or already existed
            result = await db.execute(
                text("SELECT id FROM entities WHERE source = 'careers_form' AND source_id = :email"),
                {"email": c["email"]},
            )
            row = result.fetchone()
            if not row:
                continue
            actual_entity_id = str(row.id)

            stage_history = json.dumps([{"stage": "applied", "at": created_at.isoformat()}])

            resume_text = f"""
{c['name']} | {c['location']} | {c['email']}

SUMMARY
{c['years_exp']} years of professional experience in {'business development and enterprise sales' if c['role'] == 'bd_manager' else 'facility operations and management' if c['role'] == 'operations_manager' else 'marketing and brand growth' if c['role'] == 'marketing' else 'finance and accounting' if c['role'] == 'finance' else 'IT infrastructure and development'}.

EXPERIENCE
Senior {'BD Manager' if c['role'] == 'bd_manager' else 'Operations Manager'} — Various Companies (2018-2024)
- Managed enterprise accounts worth ₹{c['current_ctc']//100000} Cr+ annually
- Led teams of 5-15 members across multiple locations
- Consistently exceeded quarterly targets by 20-30%

EDUCATION
MBA, Management — IIM / SP Jain / XLRI
B.Tech / BBA — Premier Institution

SKILLS
CRM, B2B Sales, Enterprise Negotiation, Pipeline Management, Strategic Planning
"""

            # Insert application
            await db.execute(
                text("""
                    INSERT INTO hr_applications
                    (id, candidate_entity_id, role_type, source, stage, resume_text, resume_score, screen_score, stage_history, created_at, updated_at)
                    VALUES (:id, :eid, :role, 'careers_form', :stage, :resume_text, :resume_score, :screen_score, CAST(:history AS jsonb), :created, :updated)
                    ON CONFLICT (candidate_entity_id, role_type) DO NOTHING
                """),
                {
                    "id": app_id,
                    "eid": actual_entity_id,
                    "role": c["role"],
                    "stage": c["stage"],
                    "resume_text": resume_text.strip(),
                    "resume_score": c["resume_score"],
                    "screen_score": c["screen_score"],
                    "history": stage_history,
                    "created": created_at,
                    "updated": updated_at,
                },
            )

            print(f"  ✓ {c['name']} ({c['role']}) → {c['stage']}")

        await db.commit()

    print(f"\nDone! {len(CANDIDATES)} candidates seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
