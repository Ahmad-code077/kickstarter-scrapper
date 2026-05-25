# test_graphql_debug.py - Isolated GraphQL debugging
# Test GraphQL endpoint with different curl_cffi impersonate versions
# Tests various browser fingerprints to bypass Cloudflare blocks

from curl_cffi.requests import Session
import time
import json
import logging

# Setup basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# Different impersonate versions to test
IMPERSONATE_VERSIONS = [
    "chrome",           # Latest Chrome
    "chrome136",        # Chrome 136
    "chrome135",        # Chrome 135
    "chrome134",        # Chrome 134
    "safari",           # Safari
]

# Hardcoded test values
GRAPHQL_URL = "https://www.kickstarter.com/graph"
CSRF_TOKEN = "i9AL8qp1pfas10I_1Nya32lzb8pW1xkWaYPMYPR2cHjpZhRvlt0ledTTRtwIQAdPpNisxAcKjUiP85K7S4P4Cw"
COOKIES = "vis=b68c4b7a7db85ba3-83d824c2462fb0c7-1e1cf6d500c971ffv1; ajs_anonymous_id=b68c4b7a7db85ba3-83d824c2462fb0c7-1e1cf6d500c971ffv1; _gcl_au=1.1.1566695133.1778597682; _fbp=fb.1.1778597682894.956484052675046979; _ga=GA1.1.166872624.1778597683; __stripe_mid=25547acf-5b10-45cd-8ab7-b0663fa90acd6fc2f6; _tt_enable_cookie=1; _ttp=01KREAXS9P12C84J0HT5MN957T_.tt.1; __ssid=efaa3b7b-2e1e-41c8-a2c6-052d8981feb6; _ga_694BZY431E=GS2.1.s1778597683$o1$g1$t1778597814$j15$l0$h0; _gcl_gs=2.1.k1$i1779289387$u194274487; _gcl_aw=GCL.1779289393.Cj0KCQjwlLDQBhDjARIsAPlIefEeP3pS_8hHLH4-9rRdhOPwZocmEmn4GBSuqG2hg3BVhCOHX4UapGAaAnKGEALw_wcB; intercom-id-dclio1b4=a4c202f0-26d1-4cdc-b8c0-d40bce69843c; intercom-session-dclio1b4=; intercom-device-id-dclio1b4=688ca9b0-c8aa-49ba-b1e2-ac46ec7415fa; _ga_4QJHD3JJL9=GS2.1.s1779373755$o2$g0$t1779373755$j60$l0$h1730641583; lang=en; woe_id=70N%2BTd2OzabIuJkwvsU6Lbhe3QJc1gAGc6EdoJ56Ca433K0O6ulLn9rkMVqAd8kxdF%2BFVYP2Xe1yCvnpxR5rS%2F4sSn9FW91m9UjCM9SuRaVjUcSxzmFXaGS5Du8%3D--SIghePHm3sc8Xl90--WaTz7Z4DO8HtE6ECLUpcOw%3D%3D; ksr_consent=%7B%22purposes%22%3A%7B%22SaleOfInfo%22%3Atrue%7C%22Analytics%22%3Atrue%7C%22Functional%22%3Atrue%7C%22Advertising%22%3Atrue%7D%7C%22confirmed%22%3Atrue%7C%22prompted%22%3Atrue%7C%22timestamp%22%3A%222026-05-12T14%3A56%3A12.619Z%22%7C%22updated%22%3Atrue%7D; _ga_0RQ4C371SV=GS2.1.s1779708139$o11$g0$t1779708139$j60$l0$h0; _ga_7VSTPHXGXL=GS2.1.s1779708924$o1$g1$t1779709238$j60$l0$h0; _ga_802QHNB5QQ=GS2.1.s1779728380$o6$g0$t1779728380$j60$l0$h128513647; _rdt_uuid=1779289393105.ec0fc939-a16d-433d-8fa6-7dc0a0fdca76; _rdt_em=:7f645f91525e17ef1f33ef5cf2b90da3f2db3479caa18c2234cbe57b4a05ff00,cde8e38823cae3781981922a4f6136dd01c4b4e03ade1b99f7d2f2c3e4adadd7; cf_clearance=V.InZv2IG2ZwxbtTgdZ.szpJzoT2oTjo1LqDfwCyR_E-1779737627-1.2.1.1-oZ27QrfyUkYA6LkFfYNEantPnQO6.dreh2QiK8qCovBAPiAQOnPDTloNDhOlsUwmfvS90g7DJoR_DyPkMXeTSSJynmGKmHsAZkh5MudblLX_74oRtTPx57QYc5lRwgAV92sdQZGF6yM.zVSFosyRn2DIbO7OlxylZlrr14YVFHa0YVTV4BfCx4cfeOatdg9VViPJdEJxl2ROOsCDst7sCxqZ9nzP70msPY9RiVN6nqS4G_hzq1oUFFuyNVaDL1vJ1SU4zWM8mtYv.TOaExw3sZAZcDtXesavQyeJT3TjOEkem2ISoInr7bexEY7vW2v5zJDzOXDhrQKIRJbFoluGwA; __cf_bm=vghHTcdaktJQXGEsjLg8YnYw7.apogZBG3sulJVSMMY-1779737627.2444358-1.0.1.1-Z6hzOOy166Kz0O7uVJZDGEumegLX_YjeFQN8s5tXg2u09p0nnF7IWOtJfov5RQxashRRCivQRn03GCvXzeS4U1qZjxmw81SlTy5VmH1Ti0LqaEgF.VDi6b3iBVZdiuXU; ttcsid=1779736373823::jwrQ3mxArzeNltpEm63R.24.1779737626341.0::1.1238522.1252013::1237192.9.534.32::1235888.70.0; ttcsid_CQFU0SBC77UAS759MMVG=1779737625834::GjR4UtOhAhzgw21e7gFy.18.1779737626342.0; last_page=https%3A%2F%2Fwww.kickstarter.com%2Fprojects%2F1207952088%2Freusable-grocery-shopping-bag-thats-not-pain-in-the-hand%3Fref%3Ddiscovery%26term%3Dtravel%2520bag%26total_hits%3D476%26category_id%3D28; _ga_C7KQJW1SFV=GS2.1.s1779708144$o5$g1$t1779737627$j47$l0$h1512861406; local_offset=-1766; request_time=Mon%2C+25+May+2026+19%3A33%3A52+-0000; _ksr_session=lWbyXKG%2FzfQLZBgB39f%2BFXU%2FSYM2hrCeBXJzcklsv4j%2BEAsmrB3IRXzndnyHxTO9K173bGCIRsItJfhjNQ%2Bg1hLThOr3FQ3YKEvLCpRmv5ZHXcKxjABTUvCkiMzPil1fKoxhFSAfvCsHrWDF0mbUL2kXEiU7aEuePBgTMUmxRjXvSf%2Fb%2Bhv%2FnhvlNOAxFx8YzQKHTv5u%2FmNOr0VnukK0gEDBzEF06ufB5OCfZs0lWZcsddmyj%2B44JakeQntGfYRH07gkBiGr0bwXC%2B29Ul1K1LRIoDJbNmVh9csqC6IlkUzWzxaA9jaw9gC6Qs8YX53yAjTiwSyugunldMTh9%2FI%2BkSAZqmQHKWQLWlJZNLUQUyTlsNm%2B--%2BaF%2BUZKALs%2Frq0%2FI--0tMRfPBFkXhxpvwiPlcdRQ%3D%3D"
# Test slug from logs
TEST_SLUG = "1207952088/reusable-grocery-shopping-bag-thats-not-pain-in-the-hand"

GRAPHQL_QUERY = """
query GetCompleteProjectData($slug: String!) {
  project(slug: $slug) {
    risks
    story(assetWidth: 680)
    environmentalCommitments {
      commitmentCategory
      description
    }
    creator {
      id
      url
      location {
        displayableName
      }
      launchedProjects {
        totalCount
      }
    }
    comments {
      totalCount
    }
  }
}
"""


def test_graphql_all_impersonate():
    """Test GraphQL with all impersonate versions + CSRF/cookies"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: GraphQL with different impersonate versions (+ CSRF/Cookies)")
    logger.info("="*80)
    
    for impersonate in IMPERSONATE_VERSIONS:
        logger.info(f"\n[TEST1] Testing with impersonate='{impersonate}'")
        
        try:
            session = Session(impersonate=impersonate, timeout=30)
            
            headers = {
                "accept": "*/*",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "content-type": "application/json",
                "origin": "https://www.kickstarter.com",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-csrf-token": CSRF_TOKEN,
                "cookie": COOKIES,
            }
            
            payload = {
                "query": GRAPHQL_QUERY,
                "variables": {"slug": TEST_SLUG}
            }
            
            response = session.post(GRAPHQL_URL, json=payload, headers=headers, allow_redirects=True, timeout=30)
            
            logger.info(f"[TEST1] {impersonate:15} -> Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "errors" in data:
                        logger.warning(f"[TEST1]                  GraphQL errors: {data['errors']}")
                    else:
                        logger.info(f"[TEST1]                  ✅ SUCCESS - Valid response")
                except json.JSONDecodeError:
                    logger.warning(f"[TEST1]                  Invalid JSON response")
            elif response.status_code == 403:
                logger.warning(f"[TEST1]                  Cloudflare block (403)")
            else:
                logger.warning(f"[TEST1]                  Response: {response.text[:100]}")
            
            time.sleep(2)
        
        except Exception as e:
            logger.error(f"[TEST1] {impersonate:15} -> Exception: {e}")
            time.sleep(2)


def test_graphql_with_warmup_all_impersonate():
    """Test 2: Warmup then GraphQL with all impersonate versions"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Warmup (homepage + discovery + project page) + GraphQL")
    logger.info("="*80)
    
    for impersonate in IMPERSONATE_VERSIONS:
        logger.info(f"\n[TEST2] Testing warmup + GraphQL with impersonate='{impersonate}'")
        
        try:
            session = Session(impersonate=impersonate, timeout=30)
            
            document_headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "referer": "https://www.kickstarter.com/",
            }
            
            # Warmup steps
            logger.debug(f"[TEST2] {impersonate:15} -> Warmup: homepage")
            session.get("https://www.kickstarter.com/", headers=document_headers, allow_redirects=True, timeout=30)
            time.sleep(3)
            
            logger.debug(f"[TEST2] {impersonate:15} -> Warmup: discovery")
            session.get("https://www.kickstarter.com/discover/advanced", headers=document_headers, allow_redirects=True, timeout=30)
            time.sleep(5)
            
            logger.debug(f"[TEST2] {impersonate:15} -> Warmup: project page")
            project_url = f"https://www.kickstarter.com/projects/{TEST_SLUG}"
            session.get(project_url, headers=document_headers, allow_redirects=True, timeout=30)
            time.sleep(2)
            
            # GraphQL request
            headers = {
                "accept": "*/*",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "content-type": "application/json",
                "origin": "https://www.kickstarter.com",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-csrf-token": CSRF_TOKEN,
                "cookie": COOKIES,
            }
            
            payload = {
                "query": GRAPHQL_QUERY,
                "variables": {"slug": TEST_SLUG}
            }
            
            response = session.post(GRAPHQL_URL, json=payload, headers=headers, allow_redirects=True, timeout=30)
            
            logger.info(f"[TEST2] {impersonate:15} -> GraphQL Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "errors" in data:
                        logger.warning(f"[TEST2]                  GraphQL errors: {data['errors']}")
                    else:
                        logger.info(f"[TEST2]                  ✅ SUCCESS - Valid response")
                except json.JSONDecodeError:
                    logger.warning(f"[TEST2]                  Invalid JSON response")
            elif response.status_code == 403:
                logger.warning(f"[TEST2]                  Cloudflare block (403)")
            
            time.sleep(2)
        
        except Exception as e:
            logger.error(f"[TEST2] {impersonate:15} -> Exception: {e}")
            time.sleep(2)


def test_graphql_minimal_impersonate():
    """Test 3: GraphQL with minimal headers (no cookies/CSRF) - different impersonate versions"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: GraphQL with minimal headers (no cookies/CSRF)")
    logger.info("="*80)
    
    for impersonate in IMPERSONATE_VERSIONS:
        logger.info(f"\n[TEST3] Testing minimal with impersonate='{impersonate}'")
        
        try:
            session = Session(impersonate=impersonate, timeout=30)
            
            headers = {
                "accept": "*/*",
                "content-type": "application/json",
                "origin": "https://www.kickstarter.com",
            }
            
            payload = {
                "query": GRAPHQL_QUERY,
                "variables": {"slug": TEST_SLUG}
            }
            
            response = session.post(GRAPHQL_URL, json=payload, headers=headers, allow_redirects=True, timeout=30)
            
            logger.info(f"[TEST3] {impersonate:15} -> Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "errors" in data:
                        logger.warning(f"[TEST3]                  GraphQL errors: {data['errors']}")
                    else:
                        logger.info(f"[TEST3]                  ✅ SUCCESS - Valid response")
                except json.JSONDecodeError:
                    logger.warning(f"[TEST3]                  Invalid JSON response")
            elif response.status_code == 403:
                logger.warning(f"[TEST3]                  Cloudflare block (403)")
            
            time.sleep(1)
        
        except Exception as e:
            logger.error(f"[TEST3] {impersonate:15} -> Exception: {e}")
            time.sleep(1)


if __name__ == "__main__":
    logger.info("Starting GraphQL debug tests with multiple impersonate versions...")
    logger.info(f"Impersonate versions: {IMPERSONATE_VERSIONS}")
    logger.info(f"Test slug: {TEST_SLUG}")
    
    # Run all tests
    test_graphql_all_impersonate()
    time.sleep(5)
    test_graphql_with_warmup_all_impersonate()
    time.sleep(5)
    test_graphql_minimal_impersonate()
    
    logger.info("\n" + "="*80)
    logger.info("All tests completed")
    logger.info("="*80)
    logger.info("\nSummary:")
    logger.info("- If TEST1 shows a SUCCESS: Direct GraphQL works with that impersonate version")
    logger.info("- If TEST2 shows a SUCCESS: Warmup + GraphQL works with that impersonate version")
    logger.info("- If TEST3 shows a SUCCESS: GraphQL works without cookies (public data)")
    logger.info("\nIf all show 403: May need proxies or different approach")
    logger.info("="*80)
