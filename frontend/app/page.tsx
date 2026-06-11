"use client";

import React, { useState } from 'react';
import { 
  CheckCircle, XCircle, AlertTriangle, Upload, Download, 
  RefreshCw, Copy, Zap, Shield, Users, BarChart3, Mail 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import Papa from 'papaparse';

// All API calls now go through Next.js internal proxies (/api/*)
// These forward to the backend (configurable via BACKEND_URL env var on server-side).
// Works for local dev and production deployments (e.g. Vercel).

interface ValidationResult {
  email: string;
  status: string;
  type?: string;
  disposable?: boolean | string;
  [key: string]: any;
}

interface BulkResult {
  count: number;
  results: ValidationResult[];
}

export default function ValiMail() {
  // Single email state
  const [singleEmail, setSingleEmail] = useState('');
  const [singleKey, setSingleKey] = useState('');
  const [singleMode, setSingleMode] = useState('auto');
  const [singleResult, setSingleResult] = useState<ValidationResult | null>(null);
  const [singleLoading, setSingleLoading] = useState(false);

  // Bulk state
  const [bulkText, setBulkText] = useState('');
  const [bulkKey, setBulkKey] = useState('');
  const [bulkMode, setBulkMode] = useState('auto');
  const [bulkResults, setBulkResults] = useState<ValidationResult[]>([]);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [bulkStats, setBulkStats] = useState({ valid: 0, invalid: 0, disposable: 0, total: 0 });

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
  };

  const getStatusConfig = (status: string) => {
    const s = (status || '').toLowerCase();
    if (s.includes('ok') || s.includes('enable')) return { 
      color: 'status-ok', icon: CheckCircle, label: 'Deliverable' 
    };
    if (s.includes('disable') || s.includes('notexist')) return { 
      color: 'status-bad', icon: XCircle, label: status 
    };
    return { 
      color: 'status-warn', icon: AlertTriangle, label: status || 'Unknown' 
    };
  };

  // === SINGLE EMAIL VALIDATION ===
  const validateSingle = async () => {
    if (!singleEmail.trim()) {
      toast.error('Please enter an email address');
      return;
    }

    setSingleLoading(true);
    setSingleResult(null);

    try {
      const res = await fetch(`/api/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: singleEmail.trim(),
          api_key: singleKey.trim() || null,
          mode: singleMode,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const data = await res.json();
      setSingleResult(data);
      
      const statusCfg = getStatusConfig(data.status);
      toast.success(`Validated: ${statusCfg.label}`, {
        description: data.email,
      });
    } catch (err: any) {
      console.error(err);
      toast.error('Validation failed', {
        description: err.message || 'Could not reach backend. Ensure BACKEND_URL env var is set to a running backend instance (e.g. your deployed Python API).',
      });
    } finally {
      setSingleLoading(false);
    }
  };

  // === BULK VALIDATION ===
  const parseEmails = (text: string): string[] => {
    return text
      .split(/[\n,\s]+/)
      .map(e => e.trim())
      .filter(e => e && e.includes('@'))
      .slice(0, 50); // hard limit to match backend
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setBulkText(content);
      toast.info(`Loaded ${content.split('\n').length} lines from file`);
    };
    reader.readAsText(file);
    e.target.value = ''; // reset
  };

  const validateBulk = async () => {
    const emails = parseEmails(bulkText);
    
    if (emails.length === 0) {
      toast.error('No valid emails found');
      return;
    }
    if (emails.length > 50) {
      toast.error('Maximum 50 emails per bulk request (backend limit)');
      return;
    }

    setBulkLoading(true);
    setBulkResults([]);

    try {
      const res = await fetch(`/api/check-bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          emails,
          api_key: bulkKey.trim() || null,
          mode: bulkMode,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data: BulkResult = await res.json();
      const results = data.results || [];
      
      setBulkResults(results);

      // Calculate stats
      const stats = {
        valid: results.filter(r => (r.status || '').toLowerCase().includes('ok')).length,
        invalid: results.filter(r => 
          (r.status || '').toLowerCase().includes('disable') || 
          (r.status || '').toLowerCase().includes('notexist')
        ).length,
        disposable: results.filter(r => r.disposable === true || r.disposable === 'yes').length,
        total: results.length,
      };
      setBulkStats(stats);

      toast.success(`Validated ${results.length} emails`, {
        description: `${stats.valid} deliverable • ${stats.invalid} invalid`,
      });
    } catch (err: any) {
      toast.error('Bulk validation failed', { description: err.message });
    } finally {
      setBulkLoading(false);
    }
  };

  const exportCSV = () => {
    if (bulkResults.length === 0) return;

    const csv = Papa.unparse(bulkResults.map(r => ({
      ...r,
      status: r.status,
      type: r.type || '',
      disposable: r.disposable || '',
    })));

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = `validation-results-${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);

    toast.success('CSV exported');
  };

  const clearBulk = () => {
    setBulkText('');
    setBulkResults([]);
    setBulkStats({ valid: 0, invalid: 0, disposable: 0, total: 0 });
  };

  // Reusable result row component
  const ResultRow = ({ result }: { result: ValidationResult }) => {
    const cfg = getStatusConfig(result.status);
    const Icon = cfg.icon;

    return (
      <div className="table-row flex items-center justify-between gap-4 rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] px-5 py-3.5 text-sm">
        <div className="flex min-w-0 flex-1 items-center gap-3 font-mono text-[13px] text-zinc-400">
          <Mail className="h-3.5 w-3.5 shrink-0 text-[var(--text-subtle)]" />
          <span className="truncate text-[var(--text)]">{result.email}</span>
        </div>
        
        <div className="flex items-center gap-4">
          <div className={`status-badge ${cfg.color} flex items-center gap-1.5`}>
            <Icon className="h-3 w-3" />
            {cfg.label}
          </div>
          
          {result.type && (
            <span className="rounded bg-[var(--bg)] px-2.5 py-px text-[10px] uppercase tracking-[0.5px] text-[var(--text-muted)]">
              {result.type}
            </span>
          )}
          
          {result.disposable && (
            <span className="text-[10px] text-amber-400">DISPOSABLE</span>
          )}

          <button 
            onClick={() => copyToClipboard(JSON.stringify(result, null, 2), 'Result')}
            className="rounded p-1 text-[var(--text-subtle)] hover:bg-[var(--bg)] hover:text-[var(--text)]"
          >
            <Copy className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#0a0c10] text-zinc-200 selection:bg-emerald-500/30">
      {/* NAV */}
      <nav className="sticky top-0 z-50 border-b border-[var(--border)] bg-[#0a0c10]/95 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-8 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500 text-[#052e16]">
              <Mail className="h-4 w-4" />
            </div>
            <div>
              <div className="font-semibold tracking-[-0.02em] text-xl">ValiMail</div>
              <div className="text-[10px] text-[var(--text-subtle)] -mt-1">V2 • POWERED BY SONJJ</div>
            </div>
          </div>

          <div className="flex items-center gap-8 text-sm font-medium">
            <a href="#single" className="nav-link">Single</a>
            <a href="#bulk" className="nav-link">Bulk</a>
            <a href="#features" className="nav-link">Features</a>
            <a href="#api" className="nav-link">API</a>
          </div>

          <div className="flex items-center gap-3">
            <a 
              href="https://my.sonjj.com" 
              target="_blank" 
              className="btn-secondary rounded-full px-5 py-1.5 text-xs font-semibold"
            >
              GET API KEY
            </a>
            <a 
              href="#api" 
              className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20"
            >
              API
            </a>
          </div>
        </div>
      </nav>

      {/* HERO — High-end, dynamic */}
      <div className="relative overflow-hidden border-b border-[var(--border)]">
        <div className="mx-auto max-w-5xl px-8 pt-20 pb-24 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-4 py-1 text-xs tracking-[1px] text-emerald-400 mb-6">
            <Zap className="h-3 w-3" /> REAL-TIME PROVIDER VERIFICATION
          </div>
          
          <h1 className="mx-auto max-w-4xl text-balance text-7xl font-semibold tracking-tighter leading-[0.9]">
            The modern way to<br />validate email lists.
          </h1>
          <p className="mx-auto mt-6 max-w-md text-xl text-[var(--text-muted)]">
            Catch dead inboxes, disposables, and disabled accounts before they cost you.
          </p>

          <div className="mt-10 flex justify-center gap-4">
            <a href="#single" className="btn-primary flex h-12 items-center gap-2 rounded-2xl px-8 text-base">
              Validate an email <Mail className="h-4 w-4" />
            </a>
            <a href="#bulk" className="btn-secondary flex h-12 items-center gap-2 rounded-2xl px-8 text-base font-semibold">
              Run bulk check
            </a>
          </div>

          <div className="mt-8 flex justify-center gap-8 text-xs text-[var(--text-subtle)]">
            <div>Free: 100 checks / day / IP</div>
            <div>API key: Unlimited + provider-specific</div>
            <div>Max 50 per bulk request</div>
          </div>
        </div>
      </div>

      {/* SINGLE EMAIL — Primary high-level interaction */}
      <div id="single" className="mx-auto max-w-4xl px-8 pt-20">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <div className="text-xs uppercase tracking-[2px] text-emerald-500">PREMIUM EXPERIENCE</div>
            <h2 className="text-5xl font-semibold tracking-tighter">Single Email Validation</h2>
          </div>
          <p className="max-w-[260px] text-right text-sm text-[var(--text-muted)]">
            Instant, accurate checks. Supports free mode and full API keys.
          </p>
        </div>

        <div className="card rounded-3xl p-8">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="md:col-span-2">
              <label className="mb-2 block text-xs font-medium tracking-widest text-[var(--text-muted)]">EMAIL ADDRESS</label>
              <input
                type="email"
                value={singleEmail}
                onChange={(e) => setSingleEmail(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && validateSingle()}
                placeholder="name@company.com"
                className="input w-full rounded-2xl px-6 py-4 text-lg placeholder:text-[var(--text-subtle)]"
              />
            </div>

            <div>
              <label className="mb-2 block text-xs font-medium tracking-widest text-[var(--text-muted)]">MODE</label>
              <select 
                value={singleMode} 
                onChange={e => setSingleMode(e.target.value)}
                className="input w-full rounded-2xl px-5 py-[17px] text-base"
              >
                <option value="auto">Auto (recommended)</option>
                <option value="general">General</option>
                <option value="gmail">Gmail specific</option>
                <option value="microsoft">Microsoft / Outlook</option>
                <option value="disposable">Disposable only</option>
              </select>
            </div>
          </div>

          <div className="mt-4">
            <label className="mb-2 block text-xs font-medium tracking-widest text-[var(--text-muted)]">
              API KEY <span className="font-normal text-[var(--text-subtle)]">(optional — leave blank for free mode)</span>
            </label>
            <input
              type="text"
              value={singleKey}
              onChange={(e) => setSingleKey(e.target.value)}
              placeholder="sonjj_xxxxxxxxxxxxxxxx"
              className="input w-full rounded-2xl px-6 py-3.5 font-mono text-sm"
            />
          </div>

          <button 
            onClick={validateSingle} 
            disabled={singleLoading || !singleEmail.trim()}
            className="btn-primary mt-6 flex h-14 w-full items-center justify-center gap-3 rounded-2xl text-base disabled:opacity-60"
          >
            {singleLoading ? (
              <>VALIDATING <RefreshCw className="h-4 w-4 animate-spin" /></>
            ) : (
              <>VALIDATE EMAIL <Zap className="h-4 w-4" /></>
            )}
          </button>

          {/* Single Result */}
          <AnimatePresence>
            {singleResult && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }} 
                animate={{ opacity: 1, y: 0 }} 
                className="result-card mt-8 rounded-2xl border border-[var(--border)] bg-[var(--bg-elevated)] p-6"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-mono text-sm text-[var(--text-muted)]">{singleResult.email}</div>
                    <div className="mt-1 flex items-center gap-3">
                      {(() => {
                        const cfg = getStatusConfig(singleResult.status);
                        const Icon = cfg.icon;
                        return (
                          <div className={`status-badge ${cfg.color} flex items-center gap-2 px-4 py-1 text-sm`}>
                            <Icon className="h-4 w-4" /> {cfg.label}
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                  <button 
                    onClick={() => copyToClipboard(JSON.stringify(singleResult, null, 2), 'Full result')}
                    className="rounded-xl p-2 text-[var(--text-subtle)] hover:bg-[var(--bg)]"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>

                <div className="mt-6 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                  {singleResult.type && (
                    <div><span className="text-[var(--text-subtle)]">Type</span><div className="font-medium">{singleResult.type}</div></div>
                  )}
                  {singleResult.disposable !== undefined && (
                    <div><span className="text-[var(--text-subtle)]">Disposable</span><div className="font-medium">{String(singleResult.disposable)}</div></div>
                  )}
                  {Object.entries(singleResult).filter(([k]) => !['email','status','type','disposable'].includes(k)).slice(0,4).map(([k,v]) => (
                    <div key={k}><span className="text-[var(--text-subtle)] capitalize">{k.replace(/_/g,' ')}</span><div className="font-medium truncate">{String(v)}</div></div>
                  ))}
                </div>

                <button 
                  onClick={() => { setSingleEmail(''); setSingleResult(null); }}
                  className="mt-6 text-xs text-[var(--text-subtle)] hover:text-[var(--text)]"
                >
                  CLEAR RESULT
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* BULK — High-level dynamic experience */}
      <div id="bulk" className="mx-auto max-w-6xl px-8 pt-24 pb-12">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <div className="text-xs uppercase tracking-[2px] text-emerald-500">BATCH PROCESSING</div>
            <h2 className="text-5xl font-semibold tracking-tighter">Bulk Email Validation</h2>
          </div>
          <div className="text-right text-sm text-[var(--text-muted)]">Up to 50 at a time • Export CSV • Live stats</div>
        </div>

        <div className="grid gap-6 lg:grid-cols-5">
          {/* Input panel */}
          <div className="lg:col-span-2">
            <div className="card rounded-3xl p-8">
              <div className="mb-4 flex items-center justify-between">
                <div className="text-xs font-medium tracking-widest text-[var(--text-muted)]">EMAIL LIST</div>
                <label className="cursor-pointer text-xs text-emerald-400 hover:underline flex items-center gap-1">
                  <Upload className="h-3.5 w-3.5" /> UPLOAD FILE
                  <input type="file" accept=".txt,.csv,.list" className="hidden" onChange={handleFileUpload} />
                </label>
              </div>

              <textarea
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
                placeholder={`user1@company.com\nuser2@gmail.com\n...`}
                className="input h-48 w-full resize-y rounded-2xl p-5 font-mono text-sm"
              />

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div>
                  <div className="mb-1.5 text-[10px] text-[var(--text-subtle)]">MODE</div>
                  <select value={bulkMode} onChange={e=>setBulkMode(e.target.value)} className="input w-full rounded-xl py-2.5 text-sm">
                    <option value="auto">auto</option>
                    <option value="general">general</option>
                    <option value="gmail">gmail</option>
                    <option value="microsoft">microsoft</option>
                    <option value="disposable">disposable</option>
                  </select>
                </div>
                <div>
                  <div className="mb-1.5 text-[10px] text-[var(--text-subtle)]">API KEY (OPTIONAL)</div>
                  <input value={bulkKey} onChange={e=>setBulkKey(e.target.value)} placeholder="sonjj_..." className="input w-full rounded-xl py-2.5 text-sm font-mono" />
                </div>
              </div>

              <div className="mt-5 flex gap-3">
                <button 
                  onClick={validateBulk} 
                  disabled={bulkLoading || !bulkText.trim()} 
                  className="btn-primary flex-1 rounded-2xl py-3 text-sm font-semibold disabled:opacity-50"
                >
                  {bulkLoading ? 'VALIDATING BULK...' : 'VALIDATE LIST'}
                </button>
                <button onClick={clearBulk} className="btn-secondary rounded-2xl px-6 text-sm">CLEAR</button>
              </div>

              <div className="mt-3 text-center text-[10px] text-[var(--text-subtle)]">Max 50 emails • Free mode limited to ~100 total/day</div>
            </div>
          </div>

          {/* Results panel */}
          <div className="lg:col-span-3">
            <div className="card min-h-[420px] rounded-3xl p-8">
              {!bulkResults.length ? (
                <div className="flex h-full flex-col items-center justify-center text-center">
                  <BarChart3 className="mb-4 h-10 w-10 text-[var(--text-subtle)]" />
                  <div className="font-medium">Bulk results will appear here</div>
                  <p className="mt-1 max-w-xs text-sm text-[var(--text-muted)]">Paste or upload a list and hit validate. Results are fully dynamic and exportable.</p>
                </div>
              ) : (
                <>
                  {/* Stats */}
                  <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
                    {[
                      { label: 'VALID', value: bulkStats.valid, color: 'text-emerald-400' },
                      { label: 'INVALID', value: bulkStats.invalid, color: 'text-red-400' },
                      { label: 'DISPOSABLE', value: bulkStats.disposable, color: 'text-amber-400' },
                      { label: 'TOTAL', value: bulkStats.total, color: 'text-white' },
                    ].map((s, i) => (
                      <div key={i} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-elevated)] px-5 py-4">
                        <div className="text-[10px] tracking-widest text-[var(--text-subtle)]">{s.label}</div>
                        <div className={`mt-1 text-4xl font-semibold tabular-nums tracking-tighter ${s.color}`}>{s.value}</div>
                      </div>
                    ))}
                  </div>

                  <div className="mb-3 flex items-center justify-between text-xs uppercase tracking-widest text-[var(--text-subtle)]">
                    <div>RESULTS • {bulkResults.length} CHECKED</div>
                    <button onClick={exportCSV} className="flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300">
                      <Download className="h-3.5 w-3.5" /> EXPORT CSV
                    </button>
                  </div>

                  <div className="max-h-[380px] space-y-2 overflow-auto pr-2">
                    <AnimatePresence>
                      {bulkResults.map((r, idx) => (
                        <motion.div key={idx} initial={{opacity:0}} animate={{opacity:1}} transition={{delay: idx * 0.015}}>
                          <ResultRow result={r} />
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* FEATURES — High-level website polish */}
      <div id="features" className="border-t border-[var(--border)] bg-[#07090d] py-16">
        <div className="mx-auto max-w-5xl px-8">
          <div className="text-center">
            <div className="text-emerald-500 text-xs tracking-[3px]">TRUSTED BY GROWTH TEAMS</div>
            <h3 className="mt-3 text-4xl font-semibold tracking-tighter">Built for serious list hygiene</h3>
          </div>

          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {[
              { icon: Shield, title: "Provider-level accuracy", desc: "Queries Gmail, Microsoft, and general providers directly. Not just syntax or DNS." },
              { icon: Zap, title: "Blazing fast bulk", desc: "Parallel workers. Up to 50 emails in seconds. Real progress and instant CSV export." },
              { icon: Users, title: "Free + Premium tiers", desc: "100 free checks/day. Unlock full power (Gmail/Microsoft specific) with a sonjj.com key." },
            ].map((f, idx) => (
              <div key={idx} className="card rounded-3xl p-8">
                <f.icon className="mb-6 h-8 w-8 text-emerald-400" />
                <div className="text-xl font-semibold tracking-tight">{f.title}</div>
                <p className="mt-3 text-[15px] leading-relaxed text-[var(--text-muted)]">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* API + POWERED BY */}
      <div id="api" className="mx-auto max-w-4xl px-8 py-20 text-center">
        <div className="mx-auto max-w-md">
          <div className="inline text-emerald-400 text-sm font-medium tracking-widest">DEVELOPER FIRST</div>
          <h3 className="mt-3 text-4xl font-semibold tracking-tighter">Full REST API included</h3>
          <p className="mt-4 text-[var(--text-muted)]">The Next.js frontend is a beautiful client for the exact same FastAPI backend that powers the original CLI tool.</p>
        </div>

        <div className="mt-10 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-8 text-left font-mono text-sm">
          <div className="text-emerald-400 mb-1">POST /api/check</div>
          <pre className="text-[13px] leading-snug text-[var(--text-muted)]">{`{
  "email": "user@company.com",
  "api_key": "sonjj_xxx",   // optional
  "mode": "auto"
}`}</pre>

          <div className="mt-6 text-[10px] text-[var(--text-subtle)]">
            The backend (FastAPI + uvicorn) runs independently on port 8000. The frontend is pure Next.js — fully dynamic, TypeScript, beautiful dark interface.
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-10 text-center text-xs text-[var(--text-subtle)]">
        ValiMail V2 — Modern frontend for the Krainium Email-validator-V2 engine.<br />
        source code: <a href="https://github.com/Krainium/Email-validator-V2" className="text-emerald-400 hover:underline">github.com/Krainium/Email-validator-V2</a>
      </footer>
    </div>
  );
}
