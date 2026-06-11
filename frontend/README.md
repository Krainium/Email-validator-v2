# ValiMail Frontend

This is the Next.js (TypeScript/React) web frontend for the email validator.

It offers a clean dark-themed SaaS-style interface for checking single emails or bulk lists, with live status badges, stats cards, file upload (TXT/CSV), CSV export and copy-to-clipboard.

All API calls go through Next.js server-side proxies to the Python backend for CORS safety and to keep keys server-only.

See the root README for:

- How to run the full stack (backend on 8000 + frontend on 3000)
- Backend details and the original CLI
- API usage and deployment notes

The root also contains the FastAPI service, the core emailchk logic and supporting files.
