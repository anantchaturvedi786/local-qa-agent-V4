import json, time, ollama, requests
from datetime import datetime
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ══════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════
BASE_URL  = "https://laptopwalas.in/"
AI_MODEL  = "llama3"
MAX_PAGES = 15  # limit crawl to 15 pages (increase if needed)

SYSTEM_PROMPT = """You are a Senior QA Automation Engineer with 15 years experience.
You generate comprehensive test cases covering:
- Happy path (valid inputs, successful flows)
- Negative testing (wrong data, invalid formats)
- Edge cases (empty fields, very long inputs, special characters)
- Security (SQL injection: ' OR 1=1--, XSS: <script>alert(1)</script>)
Always reply in raw JSON only. No explanation. No markdown."""

# ══════════════════════════════════════════
# BROWSER
# ══════════════════════════════════════════
def open_browser():
    opt = webdriver.ChromeOptions()
    opt.add_argument("--start-maximized")
    opt.add_argument("--disable-notifications")
    opt.add_argument("--ignore-certificate-errors")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opt)

# ══════════════════════════════════════════
# LOCAL AI
# ══════════════════════════════════════════
def ask_ai(prompt):
    try:
        response = ollama.chat(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ]
        )
        raw = response["message"]["content"]
        raw = raw.replace("```json","").replace("```","").strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start == -1: return None
        return json.loads(raw[start:end])
    except Exception as e:
        print(f"  AI error: {e}")
        return None

# ══════════════════════════════════════════
# STEP 1 — CRAWL ENTIRE WEBSITE
# ══════════════════════════════════════════
def crawl_website(driver):
    print(f"\n🕷  Crawling {BASE_URL}...")
    visited = set()
    to_visit = [BASE_URL]
    pages = []

    while to_visit and len(visited) < MAX_PAGES:
        url = to_visit.pop(0)
        if url in visited: continue
        if urlparse(url).netloc != urlparse(BASE_URL).netloc: continue

        try:
            driver.get(url)
            time.sleep(2)
            visited.add(url)

            # detect page module/type
            title    = driver.title
            headings = [h.text.strip() for h in driver.find_elements(By.XPATH,"//h1|//h2") if h.text.strip()][:3]
            inputs   = [i.get_attribute("name") for i in driver.find_elements(By.TAG_NAME,"input") if i.is_displayed() and i.get_attribute("name")]
            buttons  = [b.text.strip() for b in driver.find_elements(By.TAG_NAME,"button") if b.is_displayed() and b.text.strip()]
            links    = [a.get_attribute("href") for a in driver.find_elements(By.TAG_NAME,"a") if a.get_attribute("href")]
            forms    = len(driver.find_elements(By.TAG_NAME,"form"))
            has_cart = any(w in driver.page_source.lower() for w in ["cart","checkout","basket"])
            has_login= any(w in driver.page_source.lower() for w in ["login","sign in","password"])
            has_search=any(w in driver.page_source.lower() for w in ["search","find"])

            # detect module name
            module = "General"
            if has_login:   module = "Authentication"
            if has_cart:    module = "Cart/Checkout"
            if has_search:  module = "Search"
            if "product" in url.lower(): module = "Product"
            if "account" in url.lower(): module = "Account"
            if "contact" in url.lower(): module = "Contact"
            if "shop"    in url.lower(): module = "Shop"
            if "categor" in url.lower(): module = "Category"

            page_info = {
                "url":      url,
                "title":    title,
                "module":   module,
                "headings": headings,
                "inputs":   inputs,
                "buttons":  buttons,
                "forms":    forms,
                "has_cart": has_cart,
                "has_login":has_login,
            }
            pages.append(page_info)
            print(f"  ✅ [{module}] {title[:40]} — {url}")

            # add new links to visit
            for link in links:
                full = urljoin(BASE_URL, link)
                if full not in visited and urlparse(full).netloc == urlparse(BASE_URL).netloc:
                    to_visit.append(full)

        except Exception as e:
            print(f"  ❌ Failed: {url} — {e}")

    print(f"\n  Found {len(pages)} pages across {len(set(p['module'] for p in pages))} modules")
    return pages

# ══════════════════════════════════════════
# STEP 2 — GENERATE TEST CASES PER MODULE
# ══════════════════════════════════════════
def generate_tests_for_page(page):
    print(f"  🧠 Generating tests for [{page['module']}] {page['title'][:30]}...")

    result = ask_ai(f"""Page module: {page['module']}
URL: {page['url']}
Title: {page['title']}
Inputs: {page['inputs']}
Buttons: {page['buttons']}
Has forms: {page['forms']}
Has cart: {page['has_cart']}
Has login: {page['has_login']}

Generate ALL test cases for this specific page module.
Use ONLY exact input names from inputs list.
Use ONLY exact button texts from buttons list.
If no inputs/buttons exist generate navigation and visual tests.

JSON only:
{{"tests":[
  {{
    "name":"test name",
    "type":"happy_path or negative or edge_case or security",
    "priority":"high or medium or low",
    "steps":[
      {{"action":"fill","target":"input_name","value":"test value"}},
      {{"action":"click","target":"Button Text"}},
      {{"action":"wait","target":"","value":"2"}}
    ],
    "expect":"what should happen",
    "risk":"what breaks if this fails"
  }}
]}}""")

    tests = result.get("tests", []) if result else []

    # always add these universal tests for every page
    tests.extend([
        {
            "name": "Page loads successfully",
            "type": "happy_path",
            "priority": "high",
            "steps": [],
            "expect": "Page loads with status 200",
            "risk": "Page is down"
        },
        {
            "name": "Mobile responsiveness check",
            "type": "edge_case",
            "priority": "medium",
            "steps": [{"action":"resize","target":"375x812","value":""}],
            "expect": "Page renders correctly on mobile",
            "risk": "Broken layout on mobile"
        },
        {
            "name": "Broken links check",
            "type": "edge_case",
            "priority": "medium",
            "steps": [],
            "expect": "No 404 links on page",
            "risk": "Users hitting dead links"
        }
    ])

    return tests

# ══════════════════════════════════════════
# STEP 3 — RUN ONE TEST
# ══════════════════════════════════════════
def run_test(driver, test, page_url):
    driver.get(page_url)
    time.sleep(2)

    # close popup
    try:
        for x in driver.find_elements(By.XPATH,"//*[text()='x' or text()='×' or text()='✕']"):
            if x.is_displayed(): x.click(); time.sleep(1); break
    except: pass

    # special tests
    if test["name"] == "Page loads successfully":
        try:
            r = requests.get(page_url, timeout=10)
            return {"status":"PASS" if r.status_code==200 else "FAIL",
                    "reason": f"Status code: {r.status_code}",
                    "errors":[]}
        except Exception as e:
            return {"status":"FAIL","reason":str(e),"errors":[]}

    if test["name"] == "Mobile responsiveness check":
        driver.set_window_size(375, 812)
        time.sleep(2)
        body = driver.find_elements(By.TAG_NAME,"body")
        visible = body[0].is_displayed() if body else False
        driver.maximize_window()
        return {"status":"PASS" if visible else "FAIL",
                "reason":"Page visible on mobile" if visible else "Page not visible on mobile",
                "errors":[]}

    if test["name"] == "Broken links check":
        links = driver.find_elements(By.TAG_NAME,"a")
        broken = []
        for link in links[:10]:  # check first 10 links
            href = link.get_attribute("href")
            if href and href.startswith("http"):
                try:
                    r = requests.get(href, timeout=5)
                    if r.status_code == 404:
                        broken.append(href)
                except: pass
        return {"status":"FAIL" if broken else "PASS",
                "reason": f"Broken links: {broken}" if broken else "No broken links found",
                "errors": broken}

    # run normal steps
    for step in test.get("steps", []):
        try:
            if step["action"] == "fill":
                try:    el = driver.find_element(By.NAME, step["target"])
                except: el = driver.find_element(By.ID,   step["target"])
                el.clear()
                el.send_keys(step.get("value",""))
            elif step["action"] == "click":
                driver.find_element(By.XPATH,
                    f"//button[contains(text(),'{step['target']}')]").click()
            elif step["action"] == "wait":
                time.sleep(int(step.get("value",2)))
            time.sleep(0.5)
        except: pass

    errors = [e.text for e in driver.find_elements(By.XPATH,
              "//*[contains(@class,'error') or @role='alert']") if e.text]

    # ask AI to judge
    verdict = ask_ai(f"""Test: {test['name']}
Expected: {test['expect']}
Errors on page: {errors}
Still on page: {page_url in driver.current_url}
JSON: {{"status":"PASS or FAIL or WARNING","reason":"one sentence"}}""")

    if verdict:
        return {"status":  verdict.get("status","UNKNOWN"),
                "reason":  verdict.get("reason",""),
                "errors":  errors}
    return {"status":"UNKNOWN","reason":"No verdict","errors":errors}

# ══════════════════════════════════════════
# STEP 4 — GENERATE HTML REPORT
# ══════════════════════════════════════════
def generate_html_report(all_results, start_time):
    total   = sum(len(r["tests"]) for r in all_results)
    passed  = sum(1 for r in all_results for t in r["tests"] if t["status"]=="PASS")
    failed  = sum(1 for r in all_results for t in r["tests"] if t["status"]=="FAIL")
    warned  = sum(1 for r in all_results for t in r["tests"] if t["status"]=="WARNING")
    duration = round((datetime.now() - start_time).total_seconds() / 60, 1)

    module_rows = ""
    for r in all_results:
        p = sum(1 for t in r["tests"] if t["status"]=="PASS")
        f = sum(1 for t in r["tests"] if t["status"]=="FAIL")
        w = sum(1 for t in r["tests"] if t["status"]=="WARNING")
        test_rows = ""
        for t in r["tests"]:
            icon = {"PASS":"✅","FAIL":"❌","WARNING":"⚠️"}.get(t["status"],"❓")
            badge = {"PASS":"pass","FAIL":"fail","WARNING":"warn"}.get(t["status"],"")
            test_rows += f"""
            <tr>
                <td>{icon} {t['name']}</td>
                <td><span class="type {t['type']}">{t['type']}</span></td>
                <td><span class="priority {t['priority']}">{t['priority']}</span></td>
                <td><span class="badge {badge}">{t['status']}</span></td>
                <td>{t.get('reason','')}</td>
                <td>{t.get('risk','')}</td>
            </tr>"""

        module_rows += f"""
        <div class="module">
            <div class="module-header" onclick="toggle(this)">
                <span class="module-name">📄 {r['module']} — {r['title'][:40]}</span>
                <span class="module-url">{r['url']}</span>
                <span class="module-stats">
                    ✅ {p} &nbsp; ❌ {f} &nbsp; ⚠️ {w}
                </span>
            </div>
            <div class="module-body">
                <table>
                    <thead>
                        <tr>
                            <th>Test Name</th>
                            <th>Type</th>
                            <th>Priority</th>
                            <th>Status</th>
                            <th>Result</th>
                            <th>Risk</th>
                        </tr>
                    </thead>
                    <tbody>{test_rows}</tbody>
                </table>
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<title>QA Report — {BASE_URL}</title>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; color: #1a1a1a; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 2rem; }}
  .header h1 {{ font-size: 28px; margin-bottom: 4px; }}
  .header p  {{ opacity: 0.7; font-size: 14px; }}
  .summary {{ display: grid; grid-template-columns: repeat(5,1fr); gap: 16px; padding: 1.5rem; }}
  .card {{ background: white; border-radius: 12px; padding: 1.2rem; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .card .num {{ font-size: 36px; font-weight: 700; }}
  .card .lbl {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .green {{ color: #1D9E75; }} .red {{ color: #E24B4A; }}
  .amber {{ color: #BA7517; }} .blue {{ color: #378ADD; }}
  .modules {{ padding: 0 1.5rem 2rem; }}
  .module {{ background: white; border-radius: 12px; margin-bottom: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .module-header {{ display: flex; align-items: center; gap: 12px; padding: 14px 18px; cursor: pointer; border-bottom: 1px solid #f0f0f0; }}
  .module-header:hover {{ background: #f8f9fa; }}
  .module-name {{ font-weight: 600; flex: 1; }}
  .module-url  {{ font-size: 11px; color: #888; flex: 2; }}
  .module-stats {{ font-size: 13px; }}
  .module-body {{ display: none; padding: 0; overflow-x: auto; }}
  .module-body.open {{ display: block; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #f8f9fa; padding: 10px 14px; text-align: left; font-weight: 500; color: #555; }}
  td {{ padding: 10px 14px; border-top: 1px solid #f0f0f0; vertical-align: top; }}
  tr:hover td {{ background: #fafafa; }}
  .badge {{ padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }}
  .pass {{ background: #E1F5EE; color: #085041; }}
  .fail {{ background: #FCEBEB; color: #501313; }}
  .warn {{ background: #FAEEDA; color: #633806; }}
  .type {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; background: #EEEDFE; color: #3C3489; }}
  .priority {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; }}
  .high   {{ background: #FCEBEB; color: #501313; }}
  .medium {{ background: #FAEEDA; color: #633806; }}
  .low    {{ background: #E1F5EE; color: #085041; }}
  .footer {{ text-align: center; padding: 1.5rem; color: #888; font-size: 12px; }}
</style>
</head>
<body>

<div class="header">
  <h1>🤖 Autonomous QA Agent Report</h1>
  <p>{BASE_URL} &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp; Model: {AI_MODEL} (Local) &nbsp;|&nbsp; Duration: {duration} mins</p>
</div>

<div class="summary">
  <div class="card"><div class="num blue">{len(all_results)}</div><div class="lbl">Pages Tested</div></div>
  <div class="card"><div class="num blue">{total}</div><div class="lbl">Total Tests</div></div>
  <div class="card"><div class="num green">{passed}</div><div class="lbl">Passed</div></div>
  <div class="card"><div class="num red">{failed}</div><div class="lbl">Failed</div></div>
  <div class="card"><div class="num amber">{warned}</div><div class="lbl">Warnings</div></div>
</div>

<div class="modules">
  <h2 style="margin-bottom:1rem;font-size:16px;color:#555">Results by Module</h2>
  {module_rows}
</div>

<div class="footer">
  Generated by Autonomous QA Agent &nbsp;|&nbsp; 100% Local &nbsp;|&nbsp; Ollama + Selenium &nbsp;|&nbsp; $0 cost
</div>

<script>
function toggle(el){{
  el.nextElementSibling.classList.toggle('open');
}}
// open first module by default
document.querySelector('.module-body').classList.add('open');
</script>
</body>
</html>"""

    with open("qa_report.html","w",encoding="utf-8") as f:
        f.write(html)
    print(f"\n  💾 Report saved → qa_report.html")

# ══════════════════════════════════════════
# MAIN — RUN THE FULL AGENT
# ══════════════════════════════════════════
def run_full_agent():
    start_time = datetime.now()
    print("="*60)
    print("  🤖 AUTONOMOUS FULL-WEBSITE QA AGENT")
    print(f"  Target:  {BASE_URL}")
    print(f"  Model:   {AI_MODEL} (100% Local)")
    print(f"  Depth:   Full — Security + Edge Cases")
    print("="*60)

    driver = open_browser()
    all_results = []

    try:
        # PHASE 1 — Crawl entire website
        pages = crawl_website(driver)

        # PHASE 2 — Generate + run tests per page
        print(f"\n🧪 Testing {len(pages)} pages...\n")
        for i, page in enumerate(pages):
            print(f"\n[{i+1}/{len(pages)}] Module: {page['module']} — {page['url']}")

            # generate tests
            tests = generate_tests_for_page(page)
            print(f"  Generated {len(tests)} test cases")

            # run each test
            page_results = []
            for j, test in enumerate(tests):
                print(f"  [{j+1}/{len(tests)}] {test['name'][:45]}...")
                outcome = run_test(driver, test, page["url"])
                icon = {"PASS":"✅","FAIL":"❌","WARNING":"⚠️"}.get(outcome["status"],"❓")
                print(f"  {icon} {outcome['status']} — {outcome.get('reason','')[:50]}")
                page_results.append({
                    "name":     test["name"],
                    "type":     test.get("type",""),
                    "priority": test.get("priority",""),
                    "expect":   test.get("expect",""),
                    "risk":     test.get("risk",""),
                    "status":   outcome["status"],
                    "reason":   outcome.get("reason",""),
                    "errors":   outcome.get("errors",[])
                })

            all_results.append({
                "module":  page["module"],
                "url":     page["url"],
                "title":   page["title"],
                "tests":   page_results
            })

        # PHASE 3 — Generate HTML report
        print("\n📊 Generating HTML report...")
        generate_html_report(all_results, start_time)

        # Print summary
        total  = sum(len(r["tests"]) for r in all_results)
        passed = sum(1 for r in all_results for t in r["tests"] if t["status"]=="PASS")
        failed = sum(1 for r in all_results for t in r["tests"] if t["status"]=="FAIL")

        print("\n" + "="*60)
        print("  📋 FINAL SUMMARY")
        print(f"  Pages tested : {len(all_results)}")
        print(f"  Total tests  : {total}")
        print(f"  ✅ Passed    : {passed}")
        print(f"  ❌ Failed    : {failed}")
        print(f"  ⏱  Duration  : {round((datetime.now()-start_time).total_seconds()/60,1)} mins")
        print("="*60)
        print("  Open qa_report.html in your browser!")
        print("="*60)

    finally:
        driver.quit()

if __name__ == "__main__":
    run_full_agent()