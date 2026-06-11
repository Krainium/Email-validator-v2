# Email Validator V2

  **Live:** [https://email-validator-v2-krainiums-projects.vercel.app](https://email-validator-v2-krainiums-projects.vercel.app)

  Checks if email addresses are real and deliverable. Paste one in or drop a whole list — you get back whether the inbox exists, if it's disabled, and if it's a throwaway address.

  Runs without any API key (100 free checks per day per IP via ychecker.com). Add a sonjj.com key to unlock unlimited checks and provider-specific lookups for Gmail and Outlook.

  ## What it does

  - Single email check or bulk up to 50 at once
  - Auto-picks the right check for Gmail, Outlook, and everything else
  - Flags disposable/temporary addresses with a confidence score
  - Export results to CSV straight from the browser
  - CLI tool for running checks from the terminal or scripts

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

  The frontend is deployed on Vercel at https://email-validator-v2-krainiums-projects.vercel.app

  Set `BACKEND_URL` in your Vercel project environment variables to point at your hosted Python backend (Railway, Render, Fly, etc.).

  ## Stack

  - **Frontend**: Next.js 16, React 19, Tailwind CSS v4, Framer Motion
  - **Backend**: Python, FastAPI, uvicorn
  - **Email checking**: ychecker.com (free) / sonjj.com (API key)

  ---

  MIT License

  ---

  ### Labels

  email validation · email checker · bulk email validation · email verifier · disposable email detector · email bounce prevention · email list cleaning · email deliverability tool · SMTP checker · email address verification · real-time email validation · email hygiene · invalid email filter · email marketing tool · dead inbox detection · email validation API · free email checker · US email validator · UK email validator · global email verification · Europe email checker · worldwide email validation · email validation online · check if email exists · verify email address
  