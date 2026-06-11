#!/usr/bin/env python3
"""email-validator — Bulk email checker via ychecker.com (sonjj API)
   Option 1: API key mode  — full endpoints, credit-based
   Option 2: Free mode     — JWT relay, 100 checks/day/IP, no key needed
"""

import os
import sys
import csv
import time
import argparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import requests
from rich.console import Console
from rich.progress import (
    Progress, BarColumn, SpinnerColumn,
    TextColumn, TimeElapsedColumn, MofNCompleteColumn,
)
from rich.table import Table
from rich import box

console = Console(highlight=False)

API_BASE          = "https://app.sonjj.com"
YCHECKER_BASE     = "https://ychecker.com"
FREE_API_BASE     = "https://api.sonjj.com"
UA_BROWSER        = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/147.0.0.0 Safari/537.36")
UA_API            = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"

GMAIL_DOMAINS     = {"gmail.com"}
MICROSOFT_DOMAINS = {"outlook.com", "hotmail.com", "live.com", "msn.com",
                     "outlook.co.uk", "hotmail.co.uk", "live.co.uk"}


# ── colour helpers ─────────────────────────────────────────────────────────────

def oinfo(msg):    console.print(f"  [bold cyan]\\[*][/bold cyan] {msg}")
def osuccess(msg): console.print(f"  [bold green]\\[+][/bold green] [green]{msg}[/green]")
def owarn(msg):    console.print(f"  [bold yellow]\\[!][/bold yellow] [yellow]{msg}[/yellow]")
def oerror(msg):   console.print(f"  [bold red]\\[-][/bold red] [red]{msg}[/red]")
def ostep(msg):    console.print(f"  [bold magenta]\\[>][/bold magenta] [bold white]{msg}[/bold white]")
def odetail(msg):  console.print(f"      [dim]{msg}[/dim]")

def odivider():
    console.print(f"  [dim]{'─' * 62}[/dim]")

def oheader(title):
    console.print()
    odivider()
    console.print(f"  [bold white]{title}[/bold white]")
    odivider()
    console.print()

def obanner():
    console.print()
    console.print("  [green]+══════════════════════════════════════════════════════════+[/green]")
    console.print("  [green]|[/green]  [bold cyan] ███████╗███╗   ███╗ █████╗ ██╗██╗      [/bold cyan]              [green]|[/green]")
    console.print("  [green]|[/green]  [bold cyan] ██╔════╝████╗ ████║██╔══██╗██║██║      [/bold cyan]              [green]|[/green]")
    console.print("  [green]|[/green]  [bold cyan] █████╗  ██╔████╔██║███████║██║██║      [/bold cyan]              [green]|[/green]")
    console.print("  [green]|[/green]  [bold cyan] ██╔══╝  ██║╚██╔╝██║██╔══██║██║██║      [/bold cyan]             [green]|[/green]")
    console.print("  [green]|[/green]  [bold cyan] ███████╗██║ ╚═╝ ██║██║  ██║██║███████╗ [/bold cyan]             [green]|[/green]")
    console.print("  [green]|[/green]  [bold cyan] ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝ [/bold cyan]            [green]|[/green]")
    console.print("  [green]|[/green]                                                            [green]|[/green]")
    console.print("  [green]|[/green]  [white]Email Checker[/white]  [dim]powered by ychecker.com[/dim]               [green]|[/green]")
    console.print("  [green]+══════════════════════════════════════════════════════════+[/green]")
    odivider()
    console.print()


# ══════════════════════════════════════════════════════════════════════════════
# Option 1 — API key mode  (app.sonjj.com, X-Api-Key header)
# ══════════════════════════════════════════════════════════════════════════════

def _api_get(endpoint: str, params: dict, api_key: str, retries: int = 3) -> dict:
    headers = {"X-Api-Key": api_key, "User-Agent": UA_API, "Accept": "application/json"}
    url = f"{API_BASE}{endpoint}"
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=20)
            if r.status_code == 401: return {"_error": "invalid_key"}
            if r.status_code == 402: return {"_error": "no_credits"}
            if r.status_code == 422: return {"_error": "invalid_email"}
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            if attempt == retries - 1: return {"_error": "timeout"}
            time.sleep(1)
        except Exception as e:
            if attempt == retries - 1: return {"_error": str(e)}
            time.sleep(1)
    return {"_error": "max_retries"}


def check_email_api(email: str, api_key: str, mode: str = "auto") -> dict:
    """Route to the best API endpoint based on domain."""
    email  = email.strip().lower()
    domain = _domain(email)
    result = {"email": email, "domain": domain}

    if mode == "disposable":
        r = _api_get("/v1/check_disposable_email/", {"domain": domain}, api_key)
        result.update({"disposable_score": r.get("score"), "_error": r.get("_error")})
        return result

    if mode == "gmail" or (mode == "auto" and domain in GMAIL_DOMAINS):
        r = _api_get("/v1/check_gmail/", {"email": email}, api_key)
        result.update({"status": r.get("status"), "avatar": r.get("avatar"),
                        "check_type": "gmail", "_error": r.get("_error")})
        if not r.get("_error"):
            d = _api_get("/v1/check_disposable_email/", {"domain": domain}, api_key)
            result["disposable_score"] = d.get("score", 0)
        return result

    if mode == "microsoft" or (mode == "auto" and domain in MICROSOFT_DOMAINS):
        r = _api_get("/v1/check_microsoft/", {"email": email}, api_key)
        result.update({"status": r.get("status"), "details": r.get("details", {}),
                        "check_type": "microsoft", "_error": r.get("_error")})
        if not r.get("_error"):
            d = _api_get("/v1/check_disposable_email/", {"domain": domain}, api_key)
            result["disposable_score"] = d.get("score", 0)
        return result

    # general
    r = _api_get("/v1/check_email/", {"email": email}, api_key)
    result.update({"type": r.get("type"), "disposable": r.get("disposable"),
                   "status": r.get("status"), "avatar": r.get("avatar"),
                   "check_type": "general", "_error": r.get("_error")})
    if not r.get("_error") and result.get("disposable") is None:
        d = _api_get("/v1/check_disposable_email/", {"domain": domain}, api_key)
        result["disposable_score"] = d.get("score", 0)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Option 2 — Free mode  (ychecker.com JWT relay, no API key needed)
# ══════════════════════════════════════════════════════════════════════════════

class FreeSession:
    """Manages the two-step JWT relay used by ychecker.com's own frontend.

    Flow:
      1. GET ychecker.com/app/payload?email=EMAIL&use_credit_first=0
         → returns {"code":200,"msg":"OK","items":"<JWT>"}
      2. GET api.sonjj.com/v1/check_email/?payload=<JWT>
         → returns {type, disposable, status, avatar}

    Rate limit: 100 requests / 86 400 s per IP (tracked in x-ratelimit-remaining).
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent":      UA_BROWSER,
            "Accept":          "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer":         "https://ychecker.com/",
            "DNT":             "1",
        })
        self._lock            = Lock()
        self.rate_remaining   = 100
        self.rate_limit       = 100
        self._initialised     = False

    def _init_session(self):
        """Hit the homepage once to grab CSRF + session cookies."""
        try:
            self.session.get(f"{YCHECKER_BASE}/", timeout=15)
            self._initialised = True
        except Exception as e:
            raise RuntimeError(f"Could not reach ychecker.com: {e}")

    def check(self, email: str, retries: int = 3) -> dict:
        email = email.strip().lower()
        domain = _domain(email)
        result = {"email": email, "domain": domain, "check_type": "free"}

        with self._lock:
            if not self._initialised:
                self._init_session()
            if self.rate_remaining <= 0:
                result["_error"] = "rate_limit"
                return result

        for attempt in range(retries):
            try:
                # Step 1 — get JWT
                r1 = self.session.get(
                    f"{YCHECKER_BASE}/app/payload",
                    params={"email": email, "use_credit_first": 0},
                    timeout=15,
                )

                # update rate limit counter from headers
                with self._lock:
                    rem = r1.headers.get("x-ratelimit-remaining")
                    lim = r1.headers.get("x-ratelimit-limit")
                    if rem is not None:
                        self.rate_remaining = int(rem)
                    if lim is not None:
                        self.rate_limit = int(lim)

                if r1.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue

                r1.raise_for_status()
                data1 = r1.json()

                if data1.get("code") != 200:
                    result["_error"] = data1.get("msg", "payload_error")
                    return result

                jwt_token = data1["items"]

                # Step 2 — resolve with JWT
                r2 = requests.get(
                    f"{FREE_API_BASE}/v1/check_email/",
                    params={"payload": jwt_token},
                    headers={
                        "User-Agent": UA_BROWSER,
                        "Referer":    "https://ychecker.com/",
                        "Origin":     "https://ychecker.com",
                        "Accept":     "*/*",
                    },
                    timeout=20,
                )

                if r2.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue

                r2.raise_for_status()
                data2 = r2.json()

                result.update({
                    "type":       data2.get("type"),
                    "disposable": data2.get("disposable"),
                    "status":     data2.get("status"),
                    "avatar":     data2.get("avatar"),
                    "_error":     None,
                })
                return result

            except requests.exceptions.Timeout:
                if attempt == retries - 1:
                    result["_error"] = "timeout"
                else:
                    time.sleep(1)
            except Exception as e:
                if attempt == retries - 1:
                    result["_error"] = str(e)
                else:
                    time.sleep(1)

        result.setdefault("_error", "max_retries")
        return result


# ══════════════════════════════════════════════════════════════════════════════
# Shared helpers
# ══════════════════════════════════════════════════════════════════════════════

def _domain(email: str) -> str:
    return email.split("@")[-1].lower() if "@" in email else ""


def _status_colour(status: str | None) -> str:
    if not status:
        return "dim"
    s = str(status).lower()
    # red: startswith("not") catches NotExist, NotFound, not found, not_found …
    if s.startswith("not") or any(k in s for k in (
            "invalid", "dead", "error", "fail", "disable", "disabled", "suspended")):
        return "red"
    # yellow before green — "unverified" contains "verified", "unknown" contains "ok"
    if any(k in s for k in ("unverified", "unknown", "pending")):
        return "yellow"
    if any(k in s for k in ("ok", "exist", "valid", "active", "found", "verified", "enable")):
        return "green"
    return "yellow"


def _disposable_colour(score) -> str:
    if score is None: return "dim"
    if score <= 20:   return "green"
    if score <= 60:   return "yellow"
    return "red"


def _disposable_label(score) -> str:
    if score is None:  return "?"
    if score == 0:     return "No (0)"
    if score <= 20:    return f"Low ({score})"
    if score <= 60:    return f"Medium ({score})"
    if score <= 85:    return f"High ({score})"
    return f"Very High ({score})"


def _disp_from_result(r: dict):
    """Return (label_str, colour_str) for disposable field."""
    score = r.get("disposable_score")
    raw   = r.get("disposable")
    if score is not None:
        return _disposable_label(score), _disposable_colour(score)
    if raw is not None:
        s = str(raw).lower()
        if s in ("no", "false", "0"): return raw, "green"
        if s in ("yes", "true", "1"): return raw, "red"
        return raw, "yellow"
    return "—", "dim"


# ── display ────────────────────────────────────────────────────────────────────

def print_single_result(r: dict) -> None:
    console.print()
    odivider()
    console.print(f"  [bold white]Email:[/bold white]  [cyan]{r['email']}[/cyan]")
    odivider()

    err = r.get("_error")
    if err == "invalid_key":
        oerror("API key rejected — check your key at my.sonjj.com"); return
    if err == "no_credits":
        oerror("No credits remaining — top up at my.sonjj.com"); return
    if err == "invalid_email":
        oerror("Email address format rejected by API"); return
    if err == "rate_limit":
        oerror("Daily rate limit reached (100/day per IP) — try again tomorrow"); return
    if err:
        oerror(f"Error: {err}"); return

    ctype  = r.get("check_type", "—")
    status = r.get("status")
    sc     = _status_colour(status)
    disp_label, disp_col = _disp_from_result(r)

    console.print(f"  [dim]Mode:[/dim]        [white]{ctype}[/white]")
    console.print(f"  [dim]Status:[/dim]      [{sc}]{status or '—'}[/{sc}]")
    if r.get("type"):
        console.print(f"  [dim]Email type:[/dim]  [white]{r['type']}[/white]")
    console.print(f"  [dim]Disposable:[/dim]  [{disp_col}]{disp_label}[/{disp_col}]")
    if r.get("avatar"):
        console.print(f"  [dim]Avatar:[/dim]      [blue]{r['avatar']}[/blue]")
    details = r.get("details")
    if details and isinstance(details, dict):
        for k, v in details.items():
            console.print(f"  [dim]{k}:[/dim]  [white]{v}[/white]")
    odivider()
    console.print()


def build_results_table(results: list[dict]) -> Table:
    t = Table(box=box.SIMPLE_HEAD, show_edge=False, pad_edge=False)
    t.add_column("Email",      style="cyan",  no_wrap=True)
    t.add_column("Type",       style="white")
    t.add_column("Status",     style="white")
    t.add_column("Disposable", style="white")
    t.add_column("Error",      style="red",   no_wrap=True)

    for r in results:
        status = r.get("status") or "—"
        sc     = _status_colour(status)
        disp_label, disp_col = _disp_from_result(r)
        err    = r.get("_error") or ""
        ctype  = r.get("check_type") or r.get("type") or "—"
        t.add_row(
            r.get("email", ""),
            ctype,
            f"[{sc}]{status}[/{sc}]",
            f"[{disp_col}]{disp_label}[/{disp_col}]",
            f"[red]{err}[/red]" if err else "",
        )
    return t


# ── export ─────────────────────────────────────────────────────────────────────

def export_csv(results: list[dict], path: str) -> None:
    fields = ["email", "domain", "check_type", "type", "status",
              "disposable", "disposable_score", "avatar", "_error"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    osuccess(f"Results saved → {path}")


# ── bulk engine ────────────────────────────────────────────────────────────────

def run_bulk(
    emails: list[str],
    checker,           # callable(email) -> dict  OR  FreeSession instance
    workers: int = 5,
    export:  str | None = None,
) -> list[dict]:
    emails = [e.strip() for e in emails if e.strip() and "@" in e]
    if not emails:
        oerror("No valid email addresses found.")
        return []

    is_free = isinstance(checker, FreeSession)

    if is_free:
        start_remaining = checker.rate_remaining
        oinfo(f"{len(emails)} email(s)  —  {workers} worker(s)  —  "
              f"[yellow]free mode ({start_remaining} requests remaining today)[/yellow]")
        if len(emails) > start_remaining:
            owarn(f"Only {start_remaining} requests left today — "
                  f"first {start_remaining} will be checked")
    else:
        oinfo(f"{len(emails)} email(s)  —  {workers} worker(s)")
    console.print()

    results: list[dict] = []
    lock = Lock()
    completed = 0

    def _run(email):
        if is_free:
            return checker.check(email)
        return checker(email)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )
    task_id = progress.add_task("[cyan]Checking...", total=len(emails))

    with progress:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_run, e): e for e in emails}
            for future in as_completed(futures):
                r = future.result()
                with lock:
                    results.append(r)
                    err = r.get("_error")
                    if err in ("invalid_key", "no_credits"):
                        progress.update(task_id, description="[red]Stopped — API error[/red]")
                        progress.stop()
                        oerror(f"Fatal: {err} — halting")
                        pool.shutdown(wait=False, cancel_futures=True)
                        break
                    completed += 1
                    progress.update(task_id, advance=1)
                    if err == "rate_limit":
                        progress.update(task_id,
                                        description="[yellow]Rate limit reached[/yellow]")
                    else:
                        sc = _status_colour(r.get("status", ""))
                        label = f"[{sc}]{r['email']}[/{sc}]"
                        progress.update(task_id,
                                        description=f"[dim]Last:[/dim] {label}")

    # results table
    console.print()
    oheader(f"Results  —  {len(results)} checked")
    console.print(build_results_table(results))

    ok    = sum(1 for r in results if not r.get("_error") and
                _status_colour(r.get("status", "")) == "green")
    bad   = sum(1 for r in results if _status_colour(r.get("status", "")) == "red")
    errs  = sum(1 for r in results if r.get("_error"))
    disps = sum(1 for r in results if (r.get("disposable_score") or 0) > 60
                or str(r.get("disposable", "")).lower() in ("yes", "true"))

    console.print()
    console.print(f"  [green]Valid/OK[/green]     {ok}")
    console.print(f"  [red]Invalid[/red]      {bad}")
    console.print(f"  [yellow]Disposable[/yellow]   {disps}")
    console.print(f"  [red]Errors[/red]       {errs}")
    console.print()

    if export:
        export_csv(results, export)

    # rate limit footer — after everything else
    if is_free:
        used = sum(1 for r in results if not r.get("_error") == "rate_limit")
        remaining = max(0, start_remaining - used)
        console.print(f"  [dim]Rate limit: used [yellow]{used}[/yellow]  —  "
                      f"[yellow]{remaining}/{checker.rate_limit}[/yellow] remaining today[/dim]")
        console.print()

    return results


# ── config persistence ─────────────────────────────────────────────────────────

_CONFIG_PATH = os.path.expanduser("~/.emailchkrc")


def load_config() -> dict:
    cfg = {"api_key": "", "mode": "free"}
    if os.path.isfile(_CONFIG_PATH):
        try:
            import json
            with open(_CONFIG_PATH) as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    # env var overrides stored key
    env = os.environ.get("SONJJ_API_KEY", "").strip()
    if env:
        cfg["api_key"] = env
    # if a key exists, switch mode to api unless explicitly stored as free
    if cfg["api_key"] and cfg.get("mode") != "free":
        cfg["mode"] = "api"
    return cfg


def save_config(cfg: dict) -> None:
    import json
    try:
        with open(_CONFIG_PATH, "w") as f:
            json.dump({"api_key": cfg.get("api_key", ""),
                       "mode": cfg.get("mode", "free")}, f)
    except Exception as e:
        owarn(f"Could not save config: {e}")


# ── interactive helpers ─────────────────────────────────────────────────────────

def _prompt_api_mode() -> str:
    console.print()
    console.print("  [dim]Check mode:[/dim]")
    console.print("    [cyan]1[/cyan]  Auto       (Gmail/Outlook → provider API, others → General)")
    console.print("    [cyan]2[/cyan]  General    (any domain, 2 credits each)")
    console.print("    [cyan]3[/cyan]  Gmail only")
    console.print("    [cyan]4[/cyan]  Microsoft  (Outlook/Hotmail/Live)")
    console.print("    [cyan]5[/cyan]  Disposable domain score only  (0.05 credits, cheapest)")
    console.print()
    raw = console.input("  [bold magenta]\\[>][/bold magenta] [bold white]Mode (1–5, default 1):[/bold white] ").strip()
    return {"1":"auto","2":"general","3":"gmail","4":"microsoft","5":"disposable","":"auto"}.get(raw,"auto")


def _prompt_workers(cap: int = 20) -> int:
    raw = console.input("  [bold magenta]\\[>][/bold magenta] [bold white]Workers (default 5):[/bold white] ").strip()
    try:
        return max(1, min(int(raw), cap))
    except (ValueError, TypeError):
        return 5


def _prompt_export() -> str | None:
    raw = console.input("  [bold magenta]\\[>][/bold magenta] [bold white]Export CSV path (Enter to skip):[/bold white] ").strip()
    return os.path.expanduser(raw) if raw else None


# ── menu flows ─────────────────────────────────────────────────────────────────

def _get_checker(cfg: dict, fs_cache: list):
    """Return (checker_callable_or_FreeSession, is_free)."""
    if cfg["mode"] == "free" or not cfg.get("api_key"):
        if not fs_cache:
            s = FreeSession()
            s._init_session()
            fs_cache.append(s)
        return fs_cache[0], True
    return cfg["api_key"], False


def menu_single(cfg: dict, fs_cache: list) -> None:
    checker, is_free = _get_checker(cfg, fs_cache)
    mode_tag = "[yellow]free[/yellow]" if is_free else "[green]API key[/green]"
    oheader(f"Single Check  [{mode_tag}]")
    email = console.input("  [bold magenta]\\[>][/bold magenta] [bold white]Email address:[/bold white] ").strip()
    if not email or "@" not in email:
        oerror("Invalid email address."); return
    ostep(f"Checking {email} ...")
    if is_free:
        result = checker.check(email)
        print_single_result(result)
        console.print(f"  [dim]Rate limit: [yellow]{checker.rate_remaining}/{checker.rate_limit}[/yellow] remaining today[/dim]")
        console.print()
    else:
        check_mode = _prompt_api_mode()
        result = check_email_api(email, checker, mode=check_mode)
        print_single_result(result)


def menu_bulk_input(cfg: dict, fs_cache: list) -> None:
    checker, is_free = _get_checker(cfg, fs_cache)
    mode_tag = "[yellow]free[/yellow]" if is_free else "[green]API key[/green]"
    oheader(f"Bulk Check — Type Emails  [{mode_tag}]")
    console.print("  [dim]Enter one email per line. Empty line when done.[/dim]")
    console.print()
    emails = []
    while True:
        line = console.input("  [bold cyan]email:[/bold cyan] ").strip()
        if not line:
            break
        if "@" in line:
            emails.append(line)
        else:
            owarn(f"Skipped (no @): {line}")
    if not emails:
        owarn("No emails entered."); return

    if not is_free:
        check_mode = _prompt_api_mode()
        workers = _prompt_workers(cap=20)
        def _c(e): return check_email_api(e, checker, mode=check_mode)
        run_bulk(emails, _c, workers=workers, export=_prompt_export())
    else:
        run_bulk(emails, checker, workers=_prompt_workers(cap=5), export=_prompt_export())


def menu_bulk_file(cfg: dict, fs_cache: list) -> None:
    checker, is_free = _get_checker(cfg, fs_cache)
    mode_tag = "[yellow]free[/yellow]" if is_free else "[green]API key[/green]"
    oheader(f"Bulk Check — Load File  [{mode_tag}]")
    console.print("  [dim]One email per line. Blank lines and invalid lines ignored.[/dim]")
    console.print()
    path = console.input("  [bold magenta]\\[>][/bold magenta] [bold white]File path:[/bold white] ").strip()
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        oerror(f"File not found: {path}"); return

    with open(path, encoding="utf-8", errors="ignore") as f:
        emails = [l.strip() for l in f if l.strip() and "@" in l]
    oinfo(f"Loaded {len(emails)} email(s) from {path}")

    if not is_free:
        check_mode = _prompt_api_mode()
        workers = _prompt_workers(cap=20)
        def _c(e): return check_email_api(e, checker, mode=check_mode)
        run_bulk(emails, _c, workers=workers, export=_prompt_export())
    else:
        run_bulk(emails, checker, workers=_prompt_workers(cap=5), export=_prompt_export())


def menu_settings(cfg: dict, fs_cache: list) -> None:
    oheader("Settings")

    stored_key = cfg.get("api_key", "")
    key_display = (f"[green]{'*' * 8}{stored_key[-4:]}[/green]"
                   if stored_key else "[dim]not set[/dim]")
    mode_display = ("[yellow]Free (ychecker relay)[/yellow]"
                    if cfg["mode"] == "free" else "[green]API key[/green]")

    console.print(f"  [dim]Current mode:[/dim]    {mode_display}")
    console.print(f"  [dim]Stored API key:[/dim]  {key_display}")
    console.print()
    console.print("    [cyan]1[/cyan]  Set API key")
    console.print("    [cyan]2[/cyan]  Clear API key")
    console.print("    [cyan]3[/cyan]  Use API key mode")
    console.print("    [cyan]4[/cyan]  Use free mode  [dim](no key needed)[/dim]")
    console.print("    [cyan]b[/cyan]  Back")
    console.print()
    choice = console.input("  [bold magenta]\\[>][/bold magenta] [bold white]Choice:[/bold white] ").strip().lower()

    if choice == "1":
        console.print()
        console.print("  [dim]Get your key at [blue]my.sonjj.com[/blue][/dim]")
        key = console.input("  [bold magenta]\\[>][/bold magenta] [bold white]Paste API key:[/bold white] ").strip()
        if key:
            cfg["api_key"] = key
            cfg["mode"]    = "api"
            fs_cache.clear()
            save_config(cfg)
            osuccess("API key saved — switched to API key mode")
        else:
            owarn("No key entered, nothing changed")

    elif choice == "2":
        cfg["api_key"] = ""
        cfg["mode"]    = "free"
        fs_cache.clear()
        save_config(cfg)
        osuccess("API key cleared — switched to free mode")

    elif choice == "3":
        if not cfg.get("api_key"):
            owarn("No API key stored — add one first (option 1)")
        else:
            cfg["mode"] = "api"
            fs_cache.clear()
            save_config(cfg)
            osuccess("Switched to API key mode")

    elif choice == "4":
        cfg["mode"] = "free"
        fs_cache.clear()
        save_config(cfg)
        osuccess("Switched to free mode")

    elif choice in ("b", ""):
        pass
    else:
        owarn("Unknown option")


def show_main_menu(cfg: dict) -> str:
    mode_label = ("[yellow]Free[/yellow]" if cfg["mode"] == "free" or not cfg.get("api_key")
                  else "[green]API Key[/green]")
    console.print(f"  [bold white]Mode:[/bold white] {mode_label}   "
                  f"[dim](4 to change)[/dim]")
    console.print()
    console.print("    [cyan]1[/cyan]  Single email check")
    console.print("    [cyan]2[/cyan]  Bulk check — type emails in")
    console.print("    [cyan]3[/cyan]  Bulk check — load from file")
    console.print("    [cyan]4[/cyan]  Settings  [dim](API key, mode)[/dim]")
    console.print("    [cyan]q[/cyan]  Quit")
    console.print()
    return console.input("  [bold magenta]\\[>][/bold magenta] [bold white]Choice:[/bold white] ").strip().lower()


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="emailchk",
        description="Email checker — free mode (no key) or API key mode",
    )
    parser.add_argument("emails",          nargs="*",    help="Email(s) to check inline")
    parser.add_argument("--key",           dest="key",   help="API key (or set SONJJ_API_KEY)")
    parser.add_argument("--free",          action="store_true", help="Force free mode")
    parser.add_argument("--file", "-f",    dest="file",  help="File of emails, one per line")
    parser.add_argument("--mode", "-m",    dest="mode",  default="auto",
                        choices=["auto","general","gmail","microsoft","disposable"],
                        help="Check mode for API key mode (default: auto)")
    parser.add_argument("--workers", "-w", dest="workers", type=int, default=5,
                        help="Parallel workers (default: 5)")
    parser.add_argument("--export", "-e",  dest="export", help="Export results to CSV")
    args = parser.parse_args()

    obanner()

    # Load persisted config; CLI flags override
    cfg = load_config()
    if args.key:
        cfg["api_key"] = args.key.strip()
        cfg["mode"]    = "api"
    if args.free:
        cfg["mode"] = "free"

    # ── non-interactive: inline emails or --file ──────────────────────────────
    if args.emails or args.file:
        is_free = cfg["mode"] == "free" or not cfg.get("api_key")
        if is_free:
            fs = FreeSession()
            fs._init_session()
            oinfo(f"Free mode — [yellow]{fs.rate_remaining}/{fs.rate_limit}[/yellow] checks remaining today")
            console.print()
            if args.emails:
                if len(args.emails) == 1:
                    print_single_result(fs.check(args.emails[0]))
                else:
                    run_bulk(args.emails, fs, workers=min(args.workers, 5), export=args.export)
            else:
                path = os.path.expanduser(args.file)
                with open(path, encoding="utf-8", errors="ignore") as f:
                    emails = [l.strip() for l in f if l.strip() and "@" in l]
                oinfo(f"Loaded {len(emails)} email(s)")
                run_bulk(emails, fs, workers=min(args.workers, 5), export=args.export)
        else:
            api_key = cfg["api_key"]
            if args.emails:
                if len(args.emails) == 1:
                    print_single_result(check_email_api(args.emails[0], api_key, args.mode))
                else:
                    def _c(e): return check_email_api(e, api_key, args.mode)
                    run_bulk(args.emails, _c, workers=args.workers, export=args.export)
            else:
                path = os.path.expanduser(args.file)
                with open(path, encoding="utf-8", errors="ignore") as f:
                    emails = [l.strip() for l in f if l.strip() and "@" in l]
                oinfo(f"Loaded {len(emails)} email(s)")
                def _c(e): return check_email_api(e, api_key, args.mode)
                run_bulk(emails, _c, workers=args.workers, export=args.export)
        return

    # ── interactive menu ──────────────────────────────────────────────────────
    # FreeSession is created lazily inside _get_checker, cached in fs_cache
    fs_cache: list = []

    while True:
        console.print()
        choice = show_main_menu(cfg)

        if choice == "1":
            menu_single(cfg, fs_cache)
        elif choice == "2":
            menu_bulk_input(cfg, fs_cache)
        elif choice == "3":
            menu_bulk_file(cfg, fs_cache)
        elif choice == "4":
            menu_settings(cfg, fs_cache)
        elif choice in ("q", "quit", "exit"):
            osuccess("Bye.")
            break
        else:
            owarn("Enter 1, 2, 3, 4 or q")


if __name__ == "__main__":
    main()
