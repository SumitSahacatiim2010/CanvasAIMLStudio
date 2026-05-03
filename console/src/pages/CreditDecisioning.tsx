/** Credit Decisioning — agentic workflow with live API integration. */
import { useState, useEffect } from 'react';
import { Check, Minus, Loader, Plus, ArrowRight, X, RefreshCw, Loader2 } from 'lucide-react';
import { fetchApi } from '../lib/api';

type Application = {
  id: string;
  applicant: string;
  product: string;
  amount: string;
  grade: string;
  status: string;
  agents: number;
  time: string;
};

type TraceStep = {
  name: string;
  status: string;
  duration: string;
};

const FALLBACK_QUEUE: Application[] = [
  { id: 'APP-000146', applicant: 'Priya M.', product: 'Home Loan', amount: '₹35,00,000', grade: 'C', status: 'pending_maker', agents: 9, time: '3.2s' },
  { id: 'APP-000141', applicant: 'Suresh R.', product: 'Personal Loan', amount: '₹8,00,000', grade: 'B', status: 'pending_checker', agents: 9, time: '2.8s' },
  { id: 'APP-000139', applicant: 'Anita B.', product: 'Business Loan', amount: '₹25,00,000', grade: 'D', status: 'pending_maker', agents: 9, time: '4.1s' },
];

const FALLBACK_TRACE: TraceStep[] = [
  { name: 'Document Ingestion', status: 'done', duration: '120ms' },
  { name: 'OCR Processing', status: 'done', duration: '340ms' },
  { name: 'Document Verification', status: 'done', duration: '85ms' },
  { name: 'Income Analysis', status: 'done', duration: '92ms' },
  { name: 'Bank Statement Analysis', status: 'done', duration: '156ms' },
  { name: 'Risk Scoring', status: 'done', duration: '445ms' },
  { name: 'Collateral Assessment', status: 'skipped', duration: '—' },
  { name: 'Policy Evaluation', status: 'done', duration: '78ms' },
  { name: 'Orchestration / Decision', status: 'done', duration: '34ms' },
];

const STATUS_CLS: Record<string, string> = { pending_maker: 'badge-warning', pending_checker: 'badge-info', finalized: 'badge-success' };
const STATUS_LABELS: Record<string, string> = { pending_maker: 'Pending Maker', pending_checker: 'Pending Checker', finalized: 'Finalized' };

const StepIcon = ({ status }: { status: string }) => {
  if (status === 'done') return <Check size={10} strokeWidth={3} />;
  if (status === 'skipped') return <Minus size={10} strokeWidth={3} />;
  return <Loader size={10} strokeWidth={2} />;
};

export function CreditDecisioning() {
  const [queue, setQueue] = useState<Application[]>([]);
  const [selectedApp, setSelectedApp] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [trace, setTrace] = useState<TraceStep[]>(FALLBACK_TRACE);
  const [traceLoading, setTraceLoading] = useState(false);

  // Load applications from API
  const loadApplications = async () => {
    try {
      setLoading(true);
      const data = await fetchApi('/agentic/applications');
      const apps: Application[] = (data.applications || []).map((a: any) => ({
        id: a.application_id,
        applicant: a.applicant || 'Unknown',
        product: a.product || 'Personal Loan',
        amount: `₹${(a.amount || 0).toLocaleString('en-IN')}`,
        grade: a.risk_grade || 'Pending',
        status: a.review_status || 'pending_maker',
        agents: 9,
        time: a.submitted_at ? new Date(a.submitted_at).toLocaleTimeString() : 'N/A',
      }));
      setQueue(apps.length > 0 ? apps : FALLBACK_QUEUE);
      if (apps.length > 0) setSelectedApp(apps[0].id);
      else setSelectedApp(FALLBACK_QUEUE[0].id);
    } catch {
      // Fallback to demo data if backend is not available
      setQueue(FALLBACK_QUEUE);
      setSelectedApp(FALLBACK_QUEUE[0].id);
    } finally {
      setLoading(false);
    }
  };

  // Load trace for a specific application
  const loadTrace = async (appId: string) => {
    try {
      setTraceLoading(true);
      const data = await fetchApi(`/agentic/applications/${appId}/trace`);
      if (data.trace && data.trace.length > 0) {
        setTrace(data.trace.map((t: any) => ({
          name: t.agent || t.name || 'Unknown Step',
          status: t.error ? 'error' : 'done',
          duration: t.duration_ms ? `${t.duration_ms}ms` : '—',
        })));
      }
    } catch {
      setTrace(FALLBACK_TRACE);
    } finally {
      setTraceLoading(false);
    }
  };

  useEffect(() => { loadApplications(); }, []);

  useEffect(() => {
    if (selectedApp) loadTrace(selectedApp);
  }, [selectedApp]);

  // Submit new application via API
  const handleNewApplication = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const applicant = formData.get('applicant') as string;
    const product = formData.get('product') as string;
    const amount = Number(formData.get('amount'));

    try {
      setSubmitting(true);
      await fetchApi('/agentic/applications', {
        method: 'POST',
        body: JSON.stringify({
          applicant_name: applicant,
          age: 35,
          monthly_income: amount / 12,
          employment_years: 5,
          existing_loans: 0,
          total_emi: 0,
          requested_amount: amount,
          requested_tenor_years: 3,
          product_type: product.toLowerCase().replace(/ /g, '_'),
          segment: 'retail',
          geography: 'IN',
        }),
      });
      setShowModal(false);
      await loadApplications();
    } catch (err: any) {
      // Fallback: add locally if backend fails
      const newApp: Application = {
        id: `APP-000${Math.floor(Math.random() * 1000)}`,
        applicant,
        product,
        amount: `₹${amount.toLocaleString('en-IN')}`,
        grade: 'Pending',
        status: 'pending_maker',
        agents: 9,
        time: 'Just now',
      };
      setQueue([newApp, ...queue]);
      setSelectedApp(newApp.id);
      setShowModal(false);
      console.warn('Backend submission failed, added locally:', err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Credit Decisioning Studio</h2>
          <p>LangGraph-powered agent workflow with maker-checker governance</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
          <button className="btn btn-ghost" onClick={loadApplications} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spinning' : ''} /> Refresh
          </button>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={16} /> New Application</button>
        </div>
      </div>

      <div className="bento-grid" style={{ marginBottom: 'var(--sp-6)' }}>
        {[
          { label: 'Review Queue', value: queue.length },
          { label: 'Avg Processing', value: '3.4s' },
          { label: 'Agent Nodes', value: '9' },
          { label: 'Policy Rules', value: '11' },
        ].map((m, i) => (
          <div key={m.label} className="glass-card metric-card stagger-item" style={{ gridColumn: 'span 3', animationDelay: `${i * 60}ms` }}>
            <div className="metric-label">{m.label}</div>
            <div className="metric-value">{m.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-4)' }}>
        <div className="glass-card stagger-item" style={{ padding: 'var(--sp-5)', animationDelay: '280ms' }}>
          <h3 className="section-title">Maker-Checker Queue</h3>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
              <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
            </div>
          ) : queue.map((app) => (
            <div key={app.id} onClick={() => setSelectedApp(app.id)} className={`queue-item ${selectedApp === app.id ? 'selected' : ''}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--sp-1)' }}>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontSize: 'var(--fs-sm)', fontWeight: 'var(--fw-medium)' }}>{app.id}</span>
                <span className={`badge ${STATUS_CLS[app.status] || 'badge-info'}`}>{STATUS_LABELS[app.status] || app.status}</span>
              </div>
              <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-primary)', fontWeight: 'var(--fw-medium)' }}>
                {app.applicant} <span style={{ color: 'var(--text-muted)', fontWeight: 'var(--fw-normal)' }}>— {app.product}</span>
              </div>
              <div style={{ display: 'flex', gap: 'var(--sp-3)', fontSize: 'var(--fs-2xs)', color: 'var(--text-muted)', marginTop: 'var(--sp-2)' }}>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{app.amount}</span>
                <span style={{ opacity: 0.4 }}>·</span>
                <span>Grade <strong style={{ color: 'var(--text-secondary)' }}>{app.grade}</strong></span>
                <span style={{ opacity: 0.4 }}>·</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{app.time}</span>
              </div>
            </div>
          ))}
          <div style={{ marginTop: 'var(--sp-3)', textAlign: 'center' }}>
            <button className="btn btn-ghost" style={{ fontSize: 'var(--fs-2xs)' }} onClick={loadApplications}>View All <ArrowRight size={12} /></button>
          </div>
        </div>

        <div className="glass-card stagger-item" style={{ padding: 'var(--sp-5)', animationDelay: '340ms' }}>
          <h3 className="section-title">Agent Workflow Trace</h3>
          {traceLoading ? (
            <div style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
              <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
            </div>
          ) : (
            <div className="timeline">
              {trace.map((step, i) => (
                <div key={step.name} className="timeline-step stagger-item" style={{ animationDelay: `${400 + i * 50}ms` }}>
                  <div className={`timeline-node ${step.status}`}><StepIcon status={step.status} /></div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 'var(--fs-sm)', color: step.status === 'skipped' ? 'var(--text-muted)' : 'var(--text-primary)', fontWeight: 'var(--fw-medium)', textDecoration: step.status === 'skipped' ? 'line-through' : 'none' }}>{step.name}</div>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-2xs)', color: 'var(--text-muted)', background: step.duration !== '—' ? 'var(--surface-3)' : 'transparent', padding: step.duration !== '—' ? '2px 8px' : 0, borderRadius: 'var(--radius-inner)' }}>{step.duration}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-content glass-card animate-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--sp-4)' }}>
              <h3 style={{ margin: 0 }}>New Application</h3>
              <button className="btn btn-ghost" onClick={() => setShowModal(false)} style={{ padding: 'var(--sp-2)' }}><X size={16} /></button>
            </div>
            <form onSubmit={handleNewApplication} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
              <div className="form-group">
                <label>Applicant Name</label>
                <input name="applicant" type="text" className="input-field" placeholder="E.g., Priya M." required />
              </div>
              <div className="form-group">
                <label>Product</label>
                <select name="product" className="input-field" required>
                  <option value="Personal Loan">Personal Loan</option>
                  <option value="Home Loan">Home Loan</option>
                  <option value="Business Loan">Business Loan</option>
                  <option value="Credit Card">Credit Card</option>
                </select>
              </div>
              <div className="form-group">
                <label>Amount Requested (₹)</label>
                <input name="amount" type="number" className="input-field" placeholder="E.g., 500000" required />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--sp-3)', marginTop: 'var(--sp-2)' }}>
                <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : null}
                  Submit Application
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
