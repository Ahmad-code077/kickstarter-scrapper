"""
test_write_kickstarter.py
-------------------------
Verifies the WRITE (upsert) path of the Kickstarter pipeline works with the
service_role secret key while RLS is enabled (deny-all) on `kickstarter_review`.

It imports the SAME `supabase_client` from config.py, so it exercises the exact
auth path production uses. It re-inserts a real row that was deleted, then reads
it back to confirm the write landed.

Run from the project root, with the new sb_secret_ key already in .env:
    venv\\Scripts\\python.exe test_write_kickstarter.py      (Windows)
    ./venv/bin/python test_write_kickstarter.py              (macOS/Linux)

PASS  -> "✅ WRITE VERIFIED" and exit code 0
FAIL  -> full error + a plain-English reason, exit code 1
"""

import sys
import traceback

# Import the ONE shared client — do not build a new one here.
try:
    from config import supabase_client
except Exception:
    print("❌ Could not import supabase_client from config.py")
    traceback.print_exc()
    sys.exit(1)

# Fail loudly if the client never initialized (missing SUPABASE_URL/KEY in .env).
assert (
    supabase_client
), "supabase_client is None — SUPABASE_URL / SUPABASE_KEY missing or empty in .env"

# The exact record to re-insert (the row that was deleted).
RECORD = {
    "project_name": "HOUSE of MATOI｜A high-end upcycled vintage kimono brand.",
    "blurb": "Using inherited kimono fabrics, we reinterpret traditional mari forms into contemporary bags.",
    "percent_funded": 90.675,
    "backers_count": 6,
    "staff_pick": False,
    "creator_name": "HOUSE of MATOI",
    "creator_past_campaigns": 1,
    "comments_count": 0,
    "launched_at": 1781013602,
    "deadline": 1783605602,
    "country": "JP",
    "relevance_score": 70,
    "score_reason": "While the product is unique and well-crafted, its relevance to the Nomads Nation niche is limited due to its focus on fashion rather than functional carry.",
    "product_summary": "HOUSE of MATOI offers a collection of contemporary bags made from upcycled vintage kimonos, emphasizing craftsmanship and uniqueness.",
    "key_features": '["Crafted from rare vintage kimono fabrics, ensuring no two pieces are alike.", "Includes a detachable Akoya pearl charm made from upcycled materials.", "Features premium YKK double zippers and custom hardware.", "Designed for both casual and formal use with adjustable chains for different carrying styles.", "Each bag comes with a Certificate of Authenticity and is presented in a signature red box."]',
    "concerns": '["Limited functionality for everyday carry compared to traditional bags.", "Low backer count may indicate weak interest in the product.", "Focus on fashion and aesthetics may not align with Nomads Nation\'s practical carry focus."]',
    "main_image": "https://i.kickstarter.com/assets/053/996/137/e56a260c9bfc5754b54a2d8127242132_original.png?anim=false&fit=cover&gravity=auto&height=315&origin=ugc&q=92&v=1780630973&width=560&sig=g9UMk5Uu1klKcWVnR5cy9DWkjz7FS1LqlFS0xLqAiZA%3D",
    "project_url": "https://www.kickstarter.com/projects/house-of-matoi/house-of-matoi-a-high-end-upcycled-vintage-kimono-brand",
    "created_at": "2026-06-21 22:12:36.230795",
}

url = RECORD["project_url"]


def _explain(err: Exception) -> str:
    """Map a raised error to a plain-English cause so the result is unambiguous."""
    msg = str(err).lower()
    if (
        "permission denied" in msg
        or "42501" in msg
        or "row-level security" in msg
        or "401" in msg
    ):
        return (
            "PERMISSION DENIED / RLS BLOCK. The key in .env is NOT bypassing RLS — "
            "it is almost certainly still the anon (publishable) key, not the "
            "sb_secret_ service_role key. Fix SUPABASE_KEY in .env and rerun."
        )
    if (
        "could not find" in msg
        or "column" in msg
        or "schema cache" in msg
        or "invalid input" in msg
    ):
        return (
            "SCHEMA / COLUMN MISMATCH — this is NOT a key or RLS problem. A field "
            "in RECORD does not match the table (name or type, e.g. key_features / "
            "concerns as text vs json). The service_role key is working; the row "
            "shape needs fixing (reuse map_project_to_review_table from "
            "phase4_supabase.py)."
        )
    if "does not exist" in msg or "relation" in msg:
        return (
            "TABLE NOT FOUND — 'kickstarter_review' does not exist in the schema "
            "this key points at. Check SUPABASE_URL points at the right project."
        )
    return "Unrecognized error — see the full traceback above."


# ---- WRITE: same upsert call shape as phase4_supabase.py -------------------
print(f"→ Upserting into kickstarter_review (on_conflict=project_url):\n  {url}")
try:
    upsert_resp = (
        supabase_client.table("kickstarter_review")
        .upsert(
            RECORD,
            on_conflict="project_url",
        )
        .execute()
    )
    print(f"  upsert response data: {upsert_resp.data}")
except Exception as err:  # do NOT swallow — surface it clearly, then stop
    print("\n❌ UPSERT FAILED\n")
    traceback.print_exc()
    print("\nREASON: " + _explain(err))
    sys.exit(1)

# ---- READ BACK: confirm the row is actually there -------------------------
try:
    read_resp = (
        supabase_client.table("kickstarter_review")
        .select("project_name, project_url, relevance_score, created_at")
        .eq("project_url", url)
        .execute()
    )
except Exception as err:
    print("\n❌ READ-BACK FAILED (upsert may have worked, but the read did not)\n")
    traceback.print_exc()
    print("\nREASON: " + _explain(err))
    sys.exit(1)

print(f"→ Read-back result: {read_resp.data}")
assert read_resp.data, (
    "Upsert returned no error but read-back found no row — investigate RLS / "
    "return behavior before trusting the full pipeline."
)

print("\n✅ WRITE VERIFIED — service_role key bypasses RLS on kickstarter_review.")
print("   The real row has been restored. Phase 4 of the pipeline will work.")
