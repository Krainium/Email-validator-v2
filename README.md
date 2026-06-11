# Email Validator V2

  **Live:** [https://email-validator-v2-seven.vercel.app/](https://email-validator-v2-seven.vercel.app/)

  Checks if email addresses are real and deliverable. Paste one in or drop a whole list — you get back whether the inbox exists, if it's disabled, and if it's a throwaway address.

  Runs without any API key (100 free checks per day per IP via ychecker.com). Add a sonjj.com key to unlock unlimited checks and provider-specific lookups for Gmail and Outlook.
  
```
  +══════════════════════════════════════════════════════════+
  |   ███████╗███╗   ███╗ █████╗ ██╗██╗                    |
  |   ██╔════╝████╗ ████║██╔══██╗██║██║                    |
  |   █████╗  ██╔████╔██║███████║██║██║                    |
  |   ██╔══╝  ██║╚██╔╝██║██╔══██║██║██║                   |
  |   ███████╗██║ ╚═╝ ██║██║  ██║██║███████╗              |
  |   ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝             |
  |                                                          |
  |  Email Validator  powered by ychecker.com                 |
  +══════════════════════════════════════════════════════════+

  Mode: Free   (4 to change)

    1  Single email check
    2  Bulk check — type emails in
    3  Bulk check — load from file
    4  Settings  (API key, mode)
    q  Quit
```
  ## What it does

  - Single email check or bulk up to 50 at once
  - Auto-picks the right check for Gmail, Outlook, and everything else
  - Flags disposable/temporary addresses with a confidence score
  - Export results to CSV straight from the browser
  - CLI tool for running checks from the terminal or scripts
  - 
  ## Modes

**Free mode** — no account needed. 100 checks per day per IP. This is the default when you run the script with no key set.

**API key mode** — full access via sonjj.com. Routes each email to the right endpoint automatically. Gmail addresses go through the Gmail check. Outlook goes through Microsoft. Everything else goes through the general check. Credit-based. Get a key at [my.sonjj.com](https://my.sonjj.com).

| Endpoint | Cost |
|---|---|
| General | 2 credits |
| Gmail | 0.5 credits |
| Microsoft | 0.5 credits |
| Disposable score only | 0.05 credits |

The API key is saved locally once entered. It loads on every run after that with no extra steps.
  ## Running it locally

  **Backend** (Python 3.10+):
  ```bash
  pip install -r requirements.txt
  uvicorn app:app --host 0.0.0.0 --port 8000
  ```

  **Frontend**:
  ```bash
  cd frontend
  npm install
  BACKEND_URL=http://localhost:8000 npm run dev
  ```

  ## CLI

  ```bash
  # Single check
  python emailchk.py user@gmail.com

  # Bulk from file, export CSV
  python emailchk.py --file emails.txt --export results.csv

  # With API key
  python emailchk.py --key YOUR_SONJJ_KEY user@company.com
  ```

  ## Deployment

  The frontend is deployed on Vercel at https://email-validator-v2-seven.vercel.app/

  Set `BACKEND_URL` in your Vercel project environment variables to point at your hosted Python backend (Railway, Render, Fly, etc.).

  ## Stack

  - **Frontend**: Next.js 16, React 19, Tailwind CSS v4, Framer Motion
  - **Backend**: Python, FastAPI, uvicorn
  - **Email checking**: ychecker.com (free) / sonjj.com (API key)
  ## Flags

| Flag | Short | What it does |
|---|---|---|
| `--file PATH` | `-f` | Load emails from a file, one per line |
| `--export PATH` | `-e` | Save results to a CSV file |
| `--key KEY` | | Use this API key for the session |
| `--free` | | Force free mode |
| `--mode MODE` | `-m` | Check mode: `auto` `general` `gmail` `microsoft` `disposable` |
| `--workers N` | `-w` | Parallel workers (default 5, max 20 for API key, max 5 for free) |

---

## Bulk check output -  DEMO

```
  [*] 5 email(s)  —  3 worker(s)  —  free mode (98 requests remaining today)

  Last: thomassmark51@gmail.com ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5/5 0:00:01


  ──────────────────────────────────────────────────────────────
  Results  —  5 checked
  ──────────────────────────────────────────────────────────────

Email                    Type   Status     Disposable
─────────────────────────────────────────────────────
baronn2929@outlook.com   free   NotExist   No
sgsuuq8992@gmail.com     free   Disable    No
mamata920@aol.com        free   Ok         No
chloegriter@gmail.com    free   Ok         No
bammygerrado@gmail.com   free   Ok         No

  Valid/OK     4
  Invalid      1
  Disposable   0
  Errors       0

  [+] Results saved → results.csv

  Rate limit: used 5  —  93/100 remaining today
```
## Modern Web Frontend (New in V2)

Added a full-featured, dynamic web interface built with Next.js, TypeScript, and React. It provides a professional, high-level user experience with a sleek dark theme.

### Features
- **Single Email Validation**: Real-time checks with detailed results, status badges, and mode selection (auto, general, Gmail, Microsoft, disposable).
- **Bulk Email Processing**: Paste emails or upload files (TXT/CSV), support for up to 50 at a time. Includes live results table, statistics cards (valid/invalid/disposable counts), and one-click CSV export.
- **API Key Support**: Optional integration with premium keys for advanced provider-specific checks.
- **Secure Architecture**: Next.js API routes act as proxies to the Python backend, handling CORS and keeping sensitive operations server-side.
- **Modern UX**: Smooth animations (Framer Motion), toast notifications, responsive design, file drag-and-drop support, and copy-to-clipboard functionality.
