# Local AI QA Agent — Full Website Testing

[![GitHub](https://img.shields.io/badge/GitHub-local--qa--agent--V4-black)](https://github.com/anantchaturvedi786/local-qa-agent-V4)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![Ollama](https://img.shields.io/badge/Ollama-Llama3-green)
![Selenium](https://img.shields.io/badge/Selenium-4.x-orange)
![Cost](https://img.shields.io/badge/Cost-$0-brightgreen)
![License](https://img.shields.io/badge/License-MIT-purple)

> **Read the full story on Medium →** [I Built an AI QA Agent That Crawls a Full Website and Tests It Automatically](https://medium.com/@anantchaturvedi786)

---

## What Is This?

As a QA engineer, I always felt that writing test cases manually is one of the most repetitive parts of the job.

Writing login tests. Checking empty fields. Testing wrong passwords. Running the same validation flows again and again.

So I built something that does all of this automatically.

This is an **autonomous QA agent** that:
- Crawls your entire website page by page
- Detects inputs, buttons, forms, and modules on each page
- Sends page details to a local AI (Llama3 via Ollama)
- AI generates test cases automatically — happy path, negative, edge cases, security
- Selenium executes every test in a real Chrome browser
- AI judges each result as PASS, FAIL, or WARNING
- Produces a full HTML report at the end

**No API key. No cloud. No paid subscription. Runs 100% on your laptop.**

---

## How It Works

```
Open website
     ↓
Crawl all pages (up to MAX_PAGES)
     ↓
Detect inputs, buttons, forms, modules
     ↓
Send page details to local Llama3
     ↓
AI generates test cases in JSON
     ↓
Selenium executes each test
     ↓
AI judges results (PASS/FAIL/WARNING)
     ↓
Generate HTML report
```

---

## Why Ollama Instead of Gemini or OpenAI?

I started this project using the Gemini free API. The problem was the **429 Too Many Requests** error. An agent that tests 15 pages makes dozens of AI calls per run. The free tier simply cannot handle that — every run would crash halfway through.

Switching to Ollama solved everything:

| | Gemini Free API | Ollama Local |
|---|---|---|
| Cost | Free but limited | Free forever |
| Rate limit | 5-15 RPM | None |
| Internet needed | Yes | No |
| Privacy | Data goes to Google | Stays on your PC |
| Good for agent? | No | Yes |

---

## Tech Stack

| Tool | Purpose | Cost |
|---|---|---|
| Python | Main framework | Free |
| Selenium WebDriver | Browser automation | Free |
| Ollama | Run AI model locally | Free |
| Llama3 | Local LLM | Free |
| Requests | Status code and link checks | Free |
| HTML/CSS | Report generation | Free |
| **Total** | | **$0** |

---

## Requirements

- Windows PC with 8GB+ RAM
- Google Chrome installed
- Python 3.11
- Ollama installed from [ollama.com](https://ollama.com)

---

## Installation

**Step 1 — Install Ollama and pull Llama3**
```bash
ollama pull llama3
ollama run llama3 "say hello"
```

**Step 2 — Install Python packages**
```bash
pip install selenium ollama webdriver-manager requests
```

**Step 3 — Clone the repository**
```bash
git clone https://github.com/anantchaturvedi786/local-qa-agent-V4
cd local-qa-agent-V4
```

---

## Usage

**Step 1 — Set your website URL**
```python
BASE_URL  = "https://your-website.com/"
AI_MODEL  = "llama3"
MAX_PAGES = 15
```

**Step 2 — Run the agent**
```bash
python qa_agent.py
```

**Step 3 — Open the report**
```
qa_report.html
```

---

## What Gets Tested

**AI-generated tests per page:**
- Happy path — valid inputs, successful flows
- Negative testing — wrong data, invalid formats
- Edge cases — empty fields, very long inputs, special characters
- Security — SQL injection, XSS attacks

**Universal tests on every page:**
- Page loads successfully (HTTP 200)
- Mobile responsiveness (375x812 iPhone size)
- Broken links check (no 404s)

---

## Module Detection

| Keyword in URL or Content | Module |
|---|---|
| login, password, sign in | Authentication |
| cart, checkout, basket | Cart/Checkout |
| search, find | Search |
| product | Product |
| account | Account |
| contact | Contact |
| shop | Shop |
| categor | Category |

---

## Real Output

```
🕷  Crawling https://laptopwalas.in/...
  ✅ [Search] Laptopwalas
  ✅ [Category] Refurbished Laptops
  ✅ [Category] Dell
  Found 15 pages across 2 modules

  Testing 15 pages...

[1/15] Module: Search
  Generated 8 test cases
  ✅ PASS — Search: Happy Path
  ✅ PASS — Search: Empty Input
  ❌ FAIL — Search: Malformed Input
  ✅ PASS — SQL Injection Test
  ⚠️  WARN — XSS Test
  ✅ PASS — Page loads successfully
  ✅ PASS — Mobile responsiveness check
  ✅ PASS — Broken links check

📋 FINAL SUMMARY
  Pages tested : 15
  Total tests  : 100+
  ✅ Passed    : 78
  ❌ Failed    : 14
  ⚠️  Warnings  : 8
```

---

## Model Recommendations

| RAM | Model | Speed |
|---|---|---|
| 8GB | gemma2:2b | Fastest |
| 8GB | llama3 | Good |
| 16GB | llama3 | Fast |
| 32GB+ | llama3:70b | Best quality |

---

## Project Structure

```
local-qa-agent-V4/
├── qa_agent.py       # Main agent
├── qa_report.html    # Generated report
└── README.md
```

---

## Known Limitations

**JSON parsing errors** — Llama3 sometimes returns malformed JSON when XSS payloads with angle brackets are involved. Agent falls back to 3 universal tests automatically.

**Chrome session crashes** — On long runs Chrome may disconnect with InvalidSessionIdException. All results collected so far are saved before exiting.

**Speed** — Llama3 on CPU takes 30-60 seconds per AI call. A 15-page site takes 45-90 minutes total.

**Public pages only** — Authenticated pages behind login are not crawled yet.

---

## Roadmap

- [ ] JSON retry logic with stricter prompt on failure
- [ ] Schema validation for every AI response
- [ ] Auto browser restart on InvalidSessionIdException
- [ ] Better locators — CSS, XPath, placeholder, label matching
- [ ] AI self-healing locators
- [ ] Screenshot capture on test failure
- [ ] CI/CD integration — Jenkins, GitHub Actions, GitLab CI
- [ ] Playwright support
- [ ] Session-based testing for authenticated pages
- [ ] Email report delivery

---

## Troubleshooting

**ModuleNotFoundError: No module named ollama**
```bash
pip install ollama
```

**InvalidSessionIdException — Chrome disconnected**
```
Happens on long runs. Run the agent again.
Fix coming: auto browser restart on session failure.
```

**AI error: Expecting comma delimiter**
```
Llama3 returned malformed JSON.
Agent falls back to universal tests automatically.
Fix coming: JSON retry logic.
```

**Ollama not found**
```bash
ollama serve
ollama run llama3 "say hello"
```

**pip not recognised on Windows**
```bash
& "C:\Users\YourName\AppData\Local\Programs\Python\Python314\python.exe" -m pip install ollama selenium webdriver-manager
```

---

## Contributing

Pull requests are welcome. If you run this on your website and find something interesting, open an issue or share your results.

---

## License

MIT License — use it, modify it, share it freely.

---

## Author

**Anant Chaturvedi**
AI QA Lead | Senior Automation Engineer | AI & Fintech Testing | Selenium | CI/CD

- Medium: [@anantchaturvedi786](https://medium.com/@anantchaturvedi786)
- GitHub: [@anantchaturvedi786](https://github.com/anantchaturvedi786)

---

*Built by a QA engineer tired of writing the same test cases manually.*

*You build. You test. You fail. You improve.*
