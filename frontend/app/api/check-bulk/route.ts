import { NextRequest, NextResponse } from 'next/server';

const API_BASE      = 'https://app.sonjj.com';
const YCHECKER_BASE = 'https://ychecker.com';
const FREE_API_BASE = 'https://api.sonjj.com';

const UA_BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const UA_API     = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0';

const GMAIL_DOMAINS     = new Set(['gmail.com']);
const MICROSOFT_DOMAINS = new Set(['outlook.com','hotmail.com','live.com','msn.com','outlook.co.uk','hotmail.co.uk','live.co.uk']);

function getDomain(email: string) {
  return email.includes('@') ? email.split('@').pop()!.toLowerCase() : '';
}

async function apiGet(endpoint: string, params: Record<string, string>, apiKey: string) {
  const url = new URL(`${API_BASE}${endpoint}`);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const res = await fetch(url.toString(), {
    headers: { 'X-Api-Key': apiKey, 'User-Agent': UA_API, 'Accept': 'application/json' },
  });
  if (res.status === 401) return { _error: 'invalid_key' };
  if (res.status === 402) return { _error: 'no_credits' };
  if (res.status === 422) return { _error: 'invalid_email' };
  if (res.status === 429) return { _error: 'rate_limited' };
  return res.json();
}

async function checkWithApiKey(email: string, apiKey: string, mode: string) {
  const d = getDomain(email);
  const base = { email, domain: d };

  if (mode === 'disposable') {
    const r = await apiGet('/v1/check_disposable_email/', { domain: d }, apiKey);
    return { ...base, disposable_score: r.score ?? null, _error: r._error ?? null };
  }
  if (mode === 'gmail' || (mode === 'auto' && GMAIL_DOMAINS.has(d))) {
    const r = await apiGet('/v1/check_gmail/', { email }, apiKey);
    const disp = r._error ? {} : await apiGet('/v1/check_disposable_email/', { domain: d }, apiKey);
    return { ...base, status: r.status, avatar: r.avatar, check_type: 'gmail', disposable_score: (disp as any).score ?? null, _error: r._error ?? null };
  }
  if (mode === 'microsoft' || (mode === 'auto' && MICROSOFT_DOMAINS.has(d))) {
    const r = await apiGet('/v1/check_microsoft/', { email }, apiKey);
    const disp = r._error ? {} : await apiGet('/v1/check_disposable_email/', { domain: d }, apiKey);
    return { ...base, status: r.status, details: r.details ?? {}, check_type: 'microsoft', disposable_score: (disp as any).score ?? null, _error: r._error ?? null };
  }
  const r = await apiGet('/v1/check_email/', { email }, apiKey);
  const disp = (!r._error && r.disposable == null)
    ? await apiGet('/v1/check_disposable_email/', { domain: d }, apiKey)
    : {};
  return { ...base, type: r.type, disposable: r.disposable, status: r.status, avatar: r.avatar, check_type: 'general', disposable_score: (disp as any).score ?? null, _error: r._error ?? null };
}

async function checkFree(email: string) {
  const d = getDomain(email);
  const base = { email, domain: d, check_type: 'free' };

  const r1 = await fetch(
    `${YCHECKER_BASE}/app/payload?email=${encodeURIComponent(email)}&use_credit_first=0`,
    { headers: { 'User-Agent': UA_BROWSER, 'Accept': '*/*', 'Referer': 'https://ychecker.com/' } },
  );
  if (r1.status === 429) return { ...base, _error: 'rate_limited' };
  const d1 = await r1.json();
  if (d1.code !== 200) return { ...base, _error: d1.msg || 'payload_error' };

  const r2 = await fetch(
    `${FREE_API_BASE}/v1/check_email/?payload=${encodeURIComponent(d1.items)}`,
    { headers: { 'User-Agent': UA_BROWSER, 'Referer': 'https://ychecker.com/', 'Origin': 'https://ychecker.com', 'Accept': '*/*' } },
  );
  if (r2.status === 429) return { ...base, _error: 'rate_limited' };
  const d2 = await r2.json();
  return { ...base, type: d2.type, disposable: d2.disposable, status: d2.status, avatar: d2.avatar, _error: null };
}

async function checkOne(email: string, apiKey?: string, mode = 'auto') {
  try {
    return apiKey?.trim()
      ? await checkWithApiKey(email, apiKey.trim(), mode)
      : await checkFree(email);
  } catch (err: any) {
    return { email, status: 'error', _error: err.message };
  }
}

export async function POST(request: NextRequest) {
  try {
    const { emails, api_key, mode = 'auto' } = await request.json();
    const list: string[] = (emails || []).map((e: string) => e.trim().toLowerCase()).filter(Boolean);
    if (!list.length) return NextResponse.json({ error: 'emails is required' }, { status: 400 });
    if (list.length > 50) return NextResponse.json({ error: 'max 50 emails per request' }, { status: 400 });

    const results = [];
    for (const email of list) {
      results.push(await checkOne(email, api_key, mode));
    }
    return NextResponse.json({ count: results.length, results });
  } catch (err: any) {
    return NextResponse.json({ error: 'Internal error', details: err.message }, { status: 500 });
  }
}
