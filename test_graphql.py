from curl_cffi.requests import Session
import json
from pathlib import Path

url = "https://www.kickstarter.com/graph"

slug = "reusable-grocery-shopping-bag-thats-not-pain-in-the-hand"
project_pid = 1207952088

# Paste fresh values from browser DevTools
CSRF_TOKEN = "PWuJwKUPacL6dyWdkZR5JRuh93qpflVTR1CIceEU2649DtqVw9hCvn3DeBRcWWQw_0vXxdS0DhFPIaS3HIKYjw"
COOKIE_STRING = "vis=b68c4b7a7db85ba3-83d824c2462fb0c7-1e1cf6d500c971ffv1; ajs_anonymous_id=b68c4b7a7db85ba3-83d824c2462fb0c7-1e1cf6d500c971ffv1; _gcl_au=1.1.1566695133.1778597682; _fbp=fb.1.1778597682894.956484052675046979; _ga=GA1.1.166872624.1778597683; __stripe_mid=25547acf-5b10-45cd-8ab7-b0663fa90acd6fc2f6; _tt_enable_cookie=1; _ttp=01KREAXS9P12C84J0HT5MN957T_.tt.1; __ssid=efaa3b7b-2e1e-41c8-a2c6-052d8981feb6; _ga_694BZY431E=GS2.1.s1778597683$o1$g1$t1778597814$j15$l0$h0; lang=en; woe_id=gY%2Fm2J2xgzhvfMbsnHA8XWu0KCkrecK2wtkEfjlFgCpVaBi3sv3V%2B%2BQenh4D%2BqM%2BAo7rzM4EwGknjcByP4Kh%2BkRHUQhee8uOPGNj6uuydzPPN1pIQcXQf05zq7Y%3D--Nq2vHoGG0gXqfPuE--%2Fph4G9573ooC978CIknmzQ%3D%3D; ksr_consent=%7B%22purposes%22%3A%7B%22SaleOfInfo%22%3Atrue%7C%22Analytics%22%3Atrue%7C%22Functional%22%3Atrue%7C%22Advertising%22%3Atrue%7D%7C%22confirmed%22%3Atrue%7C%22prompted%22%3Atrue%7C%22timestamp%22%3A%222026-05-12T14%3A56%3A12.619Z%22%7C%22updated%22%3Atrue%7D; _gcl_gs=2.1.k1$i1779289387$u194274487; _gcl_aw=GCL.1779289393.Cj0KCQjwlLDQBhDjARIsAPlIefEeP3pS_8hHLH4-9rRdhOPwZocmEmn4GBSuqG2hg3BVhCOHX4UapGAaAnKGEALw_wcB; _ga_802QHNB5QQ=GS2.1.s1779289392$o1$g1$t1779292720$j60$l0$h389434474; intercom-id-dclio1b4=a4c202f0-26d1-4cdc-b8c0-d40bce69843c; intercom-session-dclio1b4=; intercom-device-id-dclio1b4=688ca9b0-c8aa-49ba-b1e2-ac46ec7415fa; cf_clearance=JZ05cuZ1kqlrbT8APOaMRL7LPIu4ZoOO_dXOltH_ss8-1779305379-1.2.1.1-dRbTPLUL0nAFkFJbQYneN3879m5a1t03cD7Q8XfOhdgVvDjsO8i8bUVFg6U5Tz0cDON89Nz3gIzRjj.edvGSidJEmfkDeBNAr2jvDpcV3lmTc97XYntJQaEkwiWhRCt_c47p3mrj2SHn7F2LK50US9mTYnPOwATc5nlWe1UpdshXWvScrZdjZN8bhFPxyWuusNcygBP30eK.PPZrhXzoU7Dnh40FtIIQ1ymiOLwT9c2eX_k90gQp24_SDmtLPohh2YiWRzr79h05MRnGS9oTn3j7g2U0qeCdHKbxHgoZfszivFJg2x_VvmedoLRPnxNkoByi551TgA.Y0aBIEx4dng; __cf_bm=8.ugzDcaoE0WUsFX8cFjfQip8wK1nL8moB6av7_R3ls-1779305379.2602177-1.0.1.1-3tAdKaw.6aYRA85jG0AYu7lgYkkEPSkalXnreqyYXXZ3uwIFfRm.nWf63wW5wi8hHQ72sagE7FfS8R1PYJWhZtXcKUvA00S1AHtb6ff7HWFN09yA39H6K7j__w6AQDQ.; __stripe_sid=8d616dac-95fe-44ff-938f-1e93985a9a9e1aa5f0; last_page=https%3A%2F%2Fwww.kickstarter.com%2Fprojects%2Fpeak-design%2F4-new-travel-bags-by-peak-design%3Fref%3Ddiscovery_staff_picks_newest%26term%3Dtravel%2520bags%26total_hits%3D49%26category_id%3D28; _ga_0RQ4C371SV=GS2.1.s1779305407$o1$g1$t1779305726$j60$l0$h0; _rdt_uuid=1779289393105.ec0fc939-a16d-433d-8fa6-7dc0a0fdca76; _rdt_em=:cde8e38823cae3781981922a4f6136dd01c4b4e03ade1b99f7d2f2c3e4adadd7; ttcsid=1779305509974::eLA-GS3veJ765AgKiY36.6.1779305745992.0::1.216593.220509::235950.93.406.2228::226074.869.1834; ttcsid_CQFU0SBC77UAS759MMVG=1779302934051::yrlXOWVRacl9ICNbsQZS.5.1779305745992.1; _ksr_session=As18ASLrAqLPF8GIpcDOCb%2FyxIRprErDmbx2HtrBLKwIs2OE1c%2Bnf13N4e773ue3%2FvZ9YCMLqbl0xB7gIIVbreug4EOr2BPZfoSyCIUzboEMcJ66MzFV3sGW16NgW8rLMyxiX4Av49eLPYvIE3DHU4LlUwQuFkNVe4cqbGzCTjeucJByQ4G9x3kPHWnVTx5bNTbhJBuMq2hnM9n6ekLmSbahNDwjft6NO3Q8oqaDYNfVKfiKGa7dYyQSAeOwJ8b0ZP2WVmEZZFPWzQ3HSPJcNvYsWqWGx7Oqhus22unB6QQRnlA1lDGDtJuUklquYCnDG3M3scAi%2BBm%2FmX6LIZ5tFCwXTbq0cy0dZUQem2ikimy8a6Fi--R1tK3yaNXRhNxeg4--lO2VYI3i3NMPqQtXa1QSnw%3D%3D; _ga_C7KQJW1SFV=GS2.1.s1779289393$o2$g1$t1779305747$j39$l0$h666314850; request_time=Wed%2C+20+May+2026+19%3A35%3A48+-0000; local_offset=-1173"

headers = {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "origin": "https://www.kickstarter.com",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "x-csrf-token": CSRF_TOKEN,
    "cookie": COOKIE_STRING,
}
payload = {
    "query": """
    query GetCompleteProjectData($slug: String!) {
      project(slug: $slug) {
        id
        pid
        name
        state
        deadlineAt
        launchedAt
        
        # Funding stats
        pledged {
          amount
          currency
        }
        goal {
          amount
          currency
        }
        backersCount
        percentFunded
        
        # Campaign content
        risks
        story(assetWidth: 680)
        currency
        fxRate
        environmentalCommitments {
          commitmentCategory
          description
        }        
        # Creator info
        creator {
          id
          name
          imageUrl(width: 100)
          url
          biography
          location {
            displayableName
          }
          launchedProjects {
            totalCount
          }
        }
        
        # Comments count (updates doesn't exist, but comments does)
        comments {
          totalCount
        }
      }
    }
    """,
    "variables": {
        "slug": slug
    }
}

session = Session(impersonate="chrome", headers=headers, timeout=30)
response = session.post(url, json=payload, allow_redirects=True)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(response.text[:500])
    raise SystemExit

data = response.json()

# Save the response
with open("complete_project_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Saved: complete_project_data.json")

# Print key stats
project = data.get("data", {}).get("project", {})
if project:
    print("\n" + "=" * 50)
    print(f"📌 Project: {project.get('name')}")
    
    pledged = project.get('pledged', {})
    goal = project.get('goal', {})
    print(f"💰 Pledged: {pledged.get('amount')} {pledged.get('currency')}")
    print(f"🎯 Goal: {goal.get('amount')} {goal.get('currency')}")
    print(f"👥 Backers: {project.get('backersCount')}")
    print(f"📈 {project.get('percentFunded')}% funded")
    
    comments = project.get('comments', {})
    print(f"💬 Comments: {comments.get('totalCount')}")
    
    rewards = project.get('rewards', {}).get('nodes', [])
    if rewards:
        print(f"\n🎁 Reward Tiers: {len(rewards)}")
        for r in rewards[:3]:
            print(f"   - {r.get('name')}: {r.get('backersCount')} backers, {r.get('remainingQuantity')} left")
else:
    print("❌ No project data found")
    print(json.dumps(data, indent=2)[:500])
