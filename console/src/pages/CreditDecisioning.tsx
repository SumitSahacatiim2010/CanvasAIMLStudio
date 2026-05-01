/** Credit Decisioning — agentic workflow status and maker-checker queue. */

import { useState } from 'react';

const QUEUE = [
  { id: 'APP-000146', applicant: 'Priya M.', product: 'Home Loan', amount: '₹35,00,000', grade: 'C', status: 'pending_maker', agents: 9, time: '3.2s' },
  { id: 'APP-000141', applicant: 'Suresh R.', product: 'Personal Loan', amount: '₹8,00,000', grade: 'B', status: 'pending_checker', agents: 9, time: '2.8s' },
  { id: 'APP-000139', applicant: 'Anita B.', product: 'Business Loan', amount: '₹25,00,000', grade: 'D', status: 'pending_maker', agents: 9, time: '4.1s' },
];

const AGENT_STEPS = [
  { name: 'Document Ingestion', status: 'done', duration: '120ms' },
  { name: 'OCR Processing', status: 'done', duration: '340ms' },
  { name: 'Document Verification', status: 'done', duration: '85ms' },
  { name: 'Income Analysis', status: 'done', duration: '92ms' },
  { name: 'Bank Statement Analysis', status: 'done', duration: '156ms' },
  { name: 'Risk Scoring', status: 'done', duration: '445ms' },
  { name: 'Collateral Assessment', status: 'skipped', duration: '—' },
  { name: 'Policy Evaluation', status: 'done', duration: '78ms' },
  { name: 'Orchestration/Decision', status: 'done', duration: '34ms' },
];

const STATUS_CLS: Record<string, string> = {
  pending_maker: 'badge-warning', pending_checker: 'badge-info', finalized: 'badge-success',
};

export function CreditDecisioning() {
  const [selectedApp, setSelectedApp] = useState<string | null>(null);

  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Credit Decisioning Studio</h2>
          <p>LangGraph-powered agent workflow with maker-checker governance</p>
        </div>
        <button className="btn btn-primary">+ New Application</button>
      </div>

      <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="glass-card metric-card">
          <div className="metric-label">Review Queue</div>
          <div className="metric-value">{QUEUE.length}</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Avg Processing</div>
          <div className="metric-value">3.4s</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Agent Nodes</div>
          <div className="metric-value">9</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Policy Rules</div>
          <div className="metric-value">11</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-4)' }}>
        {/* Review Queue */}
        <div className="glass-card" style={{ padding: 'var(--sp-5)' }}>
          <h3 style={{ fontSize: 'var(--fs-base)', fontWeight: 600, marginBottom: 'var(--sp-4)' }}>
            Maker-Checker Queue
          </h3>
          {QUEUE.map((app) => (
            <div
              key={app.id}
              onClick={() => setSelectedApp(app.id)}
              style={{
                padding: 'var(--sp-3)',
                borderRadius: 'var(--radius-md)',
                border: `1px solid ${selectedApp === app.id ? 'var(--c-accent)' : 'var(--c-border)'}`,
                marginBottom: 'var(--sp-2)',
                cursor: 'pointer',
                background: selectedApp === app.id ? 'var(--c-accent-glow)' : 'transparent',
                transition: 'all var(--transition)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--sp-1)' }}>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--c-accent)', fontSize: 'var(--fs-sm)' }}>{app.id}</span>
                <span className={`badge ${STATUS_CLS[app.status]}`}>{app.status.replace('_', ' ')}</span>
              </div>
              <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--c-text-primary)' }}>{app.applicant} — {app.product}</div>
              <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--c-text-muted)', marginTop: 'var(--sp-1)' }}>
                {app.amount} · Grade {app.grade} · {app.time}
              </div>
            </div>
          ))}
        </div>

        {/* Agent Workflow Trace */}
        <div className="glass-card" style={{ padding: 'var(--sp-5)' }}>
          <h3 style={{ fontSize: 'var(--fs-base)', fontWeight: 600, marginBottom: 'var(--sp-4)' }}>
            Agent Workflow Trace
          </h3>
          {AGENT_STEPS.map((step, i) => (
            <div key={step.name} style={{
              display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
              padding: 'var(--sp-2) 0',
              borderBottom: i < AGENT_STEPS.length - 1 ? '1px solid rgba(42, 48, 66, 0.3)' : 'none',
            }}>
              <div style={{
                width: 24, height: 24, borderRadius: 'var(--radius-full)',
                background: step.status === 'done' ? 'var(--c-success)' : step.status === 'skipped' ? 'var(--c-text-muted)' : 'var(--c-warning)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '12px', color: 'white', flexShrink: 0,
              }}>
                {step.status === 'done' ? '✓' : step.status === 'skipped' ? '—' : '⋯'}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--c-text-primary)' }}>{step.name}</div>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-xs)', color: 'var(--c-text-muted)' }}>
                {step.duration}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
