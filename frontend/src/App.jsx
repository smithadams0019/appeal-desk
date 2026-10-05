import { useEffect, useMemo, useState } from 'react'

const MS = 86400000
const parse = (iso) => new Date(iso + 'T00:00:00Z')
const iso = (d) => d.toISOString().slice(0, 10)
const addDays = (s, n) => iso(new Date(parse(s).getTime() + n * MS))
const fmt = (s, opts) =>
  parse(s).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC', ...opts })
const short = (s) => fmt(s, { month: 'short' })
const num = (n) => n.toLocaleString('en-US')

const IMAGES = { 'home-safe-to-occupy': '/api/asset/letter-home-safe.png' }
const DECISION_LABEL = {
  appeal_merits: 'Appeal on the merits',
  document_cure: 'Send a document',
  nothing_to_fix: 'Nothing to fix',
}

export default function App() {
  const [tab, setTab] = useState('letter')
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header>
        <div className="bar-inner">
          <h1>Appeal Desk</h1>
          <p>
            FEMA denial letter: your deadline, today's rules, a draft to sign.
          </p>
        </div>
      </header>
      <nav className="tabs" aria-label="Sections">
        <div className="tabs-inner" role="tablist">
          {[['letter', 'Your letter'], ['queue', 'Caseworker queue'], ['record', 'The record']].map(([k, label]) => (
            <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
              {label}
            </button>
          ))}
        </div>
      </nav>
      <main id="main" className="shell">
        {tab === 'letter' && <LetterTab />}
        {tab === 'queue' && <QueueTab />}
        {tab === 'record' && <RecordTab />}
      </main>
      <footer>
        <div className="bar-inner">
          Legal information, not legal advice. You file the appeal yourself.
        </div>
      </footer>
    </>
  )
}

/* ---------------------------------------------------------------- letter */

function LetterTab() {
  const [examples, setExamples] = useState([])
  const [sel, setSel] = useState(0)
  const [custom, setCustom] = useState(null)
  const [live, setLive] = useState({})      // keyed by case id
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [pasted, setPasted] = useState('')
  const [letterDates, setLetterDates] = useState({})

  useEffect(() => { fetch('/api/examples').then((r) => r.json()).then(setExamples) }, [])

  const base = custom || examples[sel]
  const key = custom ? 'custom' : base?.id
  let result = base && live[key] ? { ...base, ...live[key] } : base
  if (base && live[key] && !live[key].liveRules?.quotedPassage && base.liveRules?.quotedPassage) {
    result = { ...result, liveRules: { ...live[key].liveRules, quotedPassage: base.liveRules.quotedPassage,
      citations: [base.liveRules.citations[0], ...live[key].liveRules.citations] } }
  }

  const letterDate = (key && letterDates[key]) || base?.parsed?.letterDate || ''
  const due = letterDate ? addDays(letterDate, 60) : null

  async function run(body, k) {
    setBusy(true); setErr('')
    try {
      const r = await fetch('/api/run', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
      const j = await r.json()
      if (!r.ok) throw new Error(j.detail || 'The live run failed.')
      return j
    } catch (e) { setErr(e.message); return null } finally { setBusy(false) }
  }

  async function runExample() {
    const j = await run({ caseId: base.id }, base.id)
    if (j) setLive((l) => ({ ...l, [base.id]: j }))
  }
  async function readMine() {
    const j = await run({ letterText: pasted })
    if (!j) return
    const first = j.parsed?.determinations?.[0]
    setCustom({
      id: 'custom', title: 'Your letter', subtitle: 'Read from the text you pasted',
      disasterName: j.parsed?.disasterNumber ? `DR-${j.parsed.disasterNumber}` : '', ...j,
      checklist: null,
    })
    setLive((l) => ({ ...l, custom: j }))
    if (j.parsed?.letterDate) setLetterDates((d) => ({ ...d, custom: j.parsed.letterDate }))
    if (!first) setErr('No decision lines were found in that text.')
  }

  if (!base) return <p className="hint" style={{ marginTop: 32 }}>Loading…</p>
  const isLive = !!live[key]

  return (
    <div className="grid">
      <Hero base={result} letterDate={letterDate} due={due}
        onDate={(v) => setLetterDates((d) => ({ ...d, [key]: v }))} />

      <section className="block">
        <h2><span className="n">Step 1</span>Letter</h2>
        <div className="picker" role="radiogroup" aria-label="Example letters">
          {examples.map((ex, i) => (
            <label key={ex.id} className={'pick' + (!custom && sel === i ? ' on' : '')}>
              <input type="radio" name="ex" checked={!custom && sel === i} onChange={() => { setSel(i); setCustom(null); setErr('') }} />
              <span className="pick-t">{ex.title}</span>
              <span className="pick-s">{ex.subtitle}</span>
            </label>
          ))}
        </div>
        <details className="paste">
          <summary>Paste your own letter</summary>
          <label htmlFor="paste" className="visually-hidden">Letter text</label>
          <textarea id="paste" rows={6} value={pasted} onChange={(e) => setPasted(e.target.value)}
            placeholder="Type or paste what your FEMA letter says, including the disaster number and the date at the top." />
          <button className="btn" disabled={busy || pasted.trim().length < 40} onClick={readMine}>
            {busy ? 'Reading…' : 'Read letter'}
          </button>
        </details>
      </section>

      <section className="block run">
        <h2><span className="n">Live</span>Check FEMA now</h2>
        <p className="hint">Searches fema.gov, decides, and redrafts. About 10 seconds.</p>
        <button className="btn primary" disabled={busy || !!custom} onClick={runExample}>
          {busy ? 'Running…' : isLive ? 'Run again' : 'Run live'}
        </button>
        {isLive && <span className="meta inline">Live result shown{live[key].fromCache ? '' : ` · ${live[key].elapsedSec}s`}</span>}
        {err && <p className="err" role="alert">{err}</p>}
      </section>
      <section className="block">
        <h2><span className="n">Step 2</span>The letter</h2>
        {IMAGES[base.id] && !custom && (
          <figure className="letter-fig">
            <img src={IMAGES[base.id]} alt="The determination section of FEMA's template ineligibility letter: ASSISTANCE NOT APPROVED, Ineligible – Home is Safe to Occupy." />
            <figcaption>{base.source}</figcaption>
          </figure>
        )}
        <dl className="facts">
          <div><dt>Disaster</dt><dd>{base.disasterName || (result.parsed?.disasterNumber ? `DR-${result.parsed.disasterNumber}` : '—')}</dd></div>
          <div><dt>Letter date</dt><dd>{letterDate ? fmt(letterDate) : '—'}</dd></div>
        </dl>
        <ul className="dets">
          {(result.parsed?.determinations || []).map((d, i) => (
            <li key={i}>
              <strong>{d.line}</strong>
              <span>{d.codeMeaning}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="block">
        <h2><span className="n">Step 3</span>FEMA today</h2>
        {result.liveRules?.quotedPassage ? (
          <blockquote className="quote">
            “{result.liveRules.quotedPassage}”
            {result.liveRules.citations?.[0] && (
              <cite><a href={result.liveRules.citations[0].url} target="_blank" rel="noreferrer">{result.liveRules.citations[0].title}</a></cite>
            )}
          </blockquote>
        ) : <p className="hint">No passage was returned for this search.</p>}
        {result.liveRules?.citations?.length > 1 && (
          <ul className="cites">
            {result.liveRules.citations.slice(1).filter((c) => !/^\d+(\s*\|.*)?$/.test(c.title || '')).map((c) => (
              <li key={c.url}>
                <a href={c.url} target="_blank" rel="noreferrer">{c.title || c.url}</a>
                <span>{c.snippet?.replace(/[#\n]+/g, ' ').slice(0, 200)}{c.snippet?.length > 200 ? '…' : ''}</span>
              </li>
            ))}
          </ul>
        )}
        {isLive && result.liveRules?.query && (
          <p className="meta">Search: “{result.liveRules.query}” · Tavily, {Math.round((result.liveRules.tavily?.elapsedMs || 0) / 100) / 10}s</p>
        )}
      </section>

      <section className="block">
        <h2><span className="n">Step 4</span>Appeal or fix?</h2>
        <div className={'decision ' + (result.decision?.decision || '')}>
          <p className="decision-tag">{DECISION_LABEL[result.decision?.decision] || 'Decision'}</p>
          <p className="decision-line">{result.decision?.oneLine}</p>
          <p className="decision-why">{result.decision?.rationale}</p>
        </div>
        {result.checklist && (
          <>
            <h3>What to send</h3>
            <ul className="checks">
              {result.checklist.map((c, i) => (
                <li key={i}><span>{c.item}</span><em>{c.where}</em></li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="block">
        <h2><span className="n">Step 5</span>Draft</h2>
        <p className="hint">Fill the [brackets], sign, mail{due ? <> by <strong>{fmt(due)}</strong></> : null}.</p>
        <Draft text={result.draft} />
      </section>

    </div>
  )
}

function Hero({ base, letterDate, due, onDate }) {
  const today = iso(new Date())
  const left = due ? Math.round((parse(due) - parse(today)) / MS) : null
  const rs = base?.ruleSet
  return (
    <aside className="hero" aria-label="Your appeal date">
      <p className="hero-eyebrow">Deadline</p>
      <h2>Postmark by</h2>
      {due ? (
        <>
          <p className="hero-date">{fmt(due, { weekday: 'long' })}</p>
          <p className="hero-sub">60 days after the letter date.</p>
        </>
      ) : <p className="hero-sub">Enter the letter date.</p>}
      <label className="date-field">
        <span>Date on the letter</span>
        <input type="date" value={letterDate} onChange={(e) => onDate(e.target.value)} />
      </label>
      {due && (
        <p className="hero-note">
          {left > 0 ? `${left} days from today.` : left === 0 ? 'That is today.' : `That date was ${-left} days ago.`}
        </p>
      )}
      {rs && (
        <div className="hero-rule">
          <p className="hero-rule-t">
            {rs.appliesEquityRule ? 'Declared after 22 March 2024' : 'Declared before 22 March 2024'}
          </p>
          <p>{rs.explanation}</p>
          <p className="hero-cite"><a href={rs.citationUrl} target="_blank" rel="noreferrer">{rs.citation}</a></p>
        </div>
      )}
    </aside>
  )
}

function Draft({ text }) {
  const [done, setDone] = useState(false)
  if (!text) return null
  return (
    <div className="draft">
      <pre>{text}</pre>
      <button className="btn" onClick={() => { navigator.clipboard?.writeText(text); setDone(true); setTimeout(() => setDone(false), 1800) }}>
        {done ? 'Copied' : 'Copy draft'}
      </button>
    </div>
  )
}

/* ----------------------------------------------------------------- queue */

function QueueTab() {
  const [q, setQ] = useState(null)
  useEffect(() => { fetch('/api/queue').then((r) => r.json()).then(setQ) }, [])
  if (!q) return <p className="hint" style={{ marginTop: 32 }}>Loading…</p>
  const { summary, rows, recheck } = q
  return (
    <div className="wide">
      <section className="block">
        <h2><span className="n">{summary.county} · {summary.disaster}</span>Documents outstanding</h2>
        <p className="hint">{num(summary.totalCode4)} registrations coded “needs documentation”; first {summary.shown} shown, homeowners first. Deadline = 60 days from application, the earliest it can be.</p>
        <div className="tablewrap">
          <table>
            <thead>
              <tr><th>Case</th><th>Where</th><th>Who</th><th>Applied</th><th>Earliest deadline</th><th>What FEMA is missing</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.ref}>
                  <td className="mono">{r.ref}</td>
                  <td>{r.city} {r.zip}</td>
                  <td>{r.ownRent}</td>
                  <td>{short(r.appliedDate)}</td>
                  <td><strong>{short(r.earliestDue)}</strong></td>
                  <td>{r.missing.join(', ')}{r.utilitiesOut ? ' · utilities out' : ''}{r.flood ? ' · flood damage' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="block">
        <h2><span className="n">Overnight re-check</span>Deadline change caught</h2>
        <div className="recheck">
          <p className="recheck-d">{fmt(recheck.releaseDate)}</p>
          <p><strong>{recheck.finding}</strong> The new date was {fmt(recheck.newDeadline)}.</p>
          <blockquote className="quote small">“{recheck.quote}”<cite><a href={recheck.url} target="_blank" rel="noreferrer">FEMA press release</a></cite></blockquote>
          <p className="meta">Read from fema.gov with Tavily Extract.</p>
        </div>
      </section>
    </div>
  )
}

/* ---------------------------------------------------------------- record */

function RecordTab() {
  const [f, setF] = useState(null)
  useEffect(() => { fetch('/api/facts').then((r) => r.json()).then(setF) }, [])
  if (!f) return <p className="hint" style={{ marginTop: 32 }}>Loading…</p>
  const d = f.dr4827
  const bar = [
    ['Eligible', d.eligible, 'ok'],
    ['Did not respond', d.byReason['3'], 'warn'],
    ['Needs documents', d.byReason['4'], 'warn'],
    ['Other ineligible', d.ineligible - d.byReason['3'] - d.byReason['4'], 'rest'],
  ]
  return (
    <div className="wide">
      <section className="block">
        <h2><span className="n">Hurricane Helene, North Carolina · DR-{d.disasterNumber}</span>
          {d.ineligiblePct}% of registrations were turned down</h2>
        <p className="hint">{num(d.ineligible)} of {num(d.registrations)} registrations ineligible; {num(d.actionable)} for no response or missing documents.</p>
        <div className="stack" role="img" aria-label={bar.map(([l, v]) => `${l} ${num(v)}`).join(', ')}>
          {bar.map(([l, v, c]) => <span key={l} className={c} style={{ flexGrow: v }} />)}
        </div>
        <ul className="legend">
          {bar.map(([l, v, c]) => <li key={l}><i className={c} />{l} <strong>{num(v)}</strong></li>)}
        </ul>
        <p className="meta">Source: <a href={d.sourceUrl} target="_blank" rel="noreferrer">OpenFEMA Individuals and Households Program registrations</a>, pulled 4 October 2026.</p>
      </section>
      <section className="block two">
        <div>
          <h2><span className="n">GAO-20-503</span>Appeals</h2>
          <p className="big">{f.gao.appealRate}%</p>
          <p className="hint">of denied applicants appealed ({f.gao.appealRateWindow}); about {Math.round(f.gao.winRate)}% of those got more help.</p>
          <p className="hint">{f.gao.letterFinding} <span className="meta">({f.gao.letterFindingPage})</span></p>
          <p className="meta"><a href={f.gao.url} target="_blank" rel="noreferrer">Read the GAO report</a></p>
        </div>
        <figure className="photo">
          <img src="/api/asset/helene-buncombe.jpg" alt="Flood-damaged road and washed-out bank in Buncombe County, North Carolina, after Hurricane Helene." />
          <figcaption>Buncombe County after Helene. Photo: NCDOT.</figcaption>
        </figure>
      </section>
      <section className="block">
        <h2><span className="n">Court record</span>Cases</h2>
        <ul className="cases">
          {f.cases.map((c) => (
            <li key={c.caption}>
              <h3><a href={c.url} target="_blank" rel="noreferrer">{c.caption}</a></h3>
              <p className="meta">{c.court}, {c.year} · {c.cite}</p>
              <p>{c.holding}</p>
              <p className="subseq"><strong>What happened next.</strong> {c.subsequent}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
