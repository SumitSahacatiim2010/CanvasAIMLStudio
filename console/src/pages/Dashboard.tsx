/** Command Center — executive overview with live API data and asymmetric bento grid. */

import { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, ArrowUpRight, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { fetchApi } from '../lib/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface MetricCard {
  label: string;
  value: string;
  change: string;
  positive: boolean;
}

interface Decision {
  id: string;
  applicant: string;
  product: string;
  amount: string;
  decision: string;
  grade: string;
  time: string;
}

const BADGE_MAP: Record<string, string> = {
  approved: 'badge-success',
  rejected: 'badge-danger',
  referred: 'badge-warning',
  pending: 'badge-info',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgo(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatCurrency(amount: number): string {
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(1)}Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  return `₹${amount.toLocaleString('en-IN')}`;
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function Dashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<MetricCard[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = useCallback(async (showRefreshIndicator = false) => {
    if (showRefreshIndicator) setRefreshing(true);
    try {
      // Fetch in parallel: catalog sources, agentic applications, ML summary, observability alerts
      const [catalogRes, agenticRes, mlRes, alertsRes] = await Promise.allSettled([
        fetchApi('/catalog/sources'),
        fetchApi('/agentic/applications'),
        fetchApi('/ml/summary'),
        fetchApi('/observability/alerts'),
      ]);

      // Parse results (each can independently succeed/fail)
      const sources = catalogRes.status === 'fulfilled'
        ? (catalogRes.value as { sources: unknown[] }).sources ?? []
        : [];

      const applications: Array<{
        application_id: string;
        applicant_name: string;
        product_type: string;
        loan_amount: number;
        decision?: string;
        risk_grade?: string;
        submitted_at?: string;
        created_at?: string;
      }> = agenticRes.status === 'fulfilled'
        ? (agenticRes.value as { applications: typeof applications }).applications ?? []
        : [];

      const mlSummary = mlRes.status === 'fulfilled'
        ? mlRes.value as { total_models: number; deployed: number; drift_alerts: number; best_f1: number | null }
        : null;

      const alerts: unknown[] = alertsRes.status === 'fulfilled'
        ? (alertsRes.value as { alerts: unknown[] }).alerts ?? []
        : [];

      // Build metric cards from live data
      const approvedApps = applications.filter(a => a.decision === 'approved').length;
      const totalApps = applications.length;
      const approvalRate = totalApps > 0 ? ((approvedApps / totalApps) * 100).toFixed(1) : '—';

      const liveMetrics: MetricCard[] = [
        {
          label: 'Data Sources',
          value: sources.length.toString(),
          change: sources.length > 0 ? `${sources.length} connected` : 'None configured',
          positive: sources.length > 0,
        },
        {
          label: 'ML Models',
          value: mlSummary ? mlSummary.total_models.toString() : '—',
          change: mlSummary ? `${mlSummary.deployed} deployed` : 'Loading…',
          positive: true,
        },
        {
          label: 'Applications Today',
          value: totalApps.toString(),
          change: totalApps > 0 ? `${approvedApps} approved` : 'No applications yet',
          positive: totalApps > 0,
        },
        {
          label: 'Approval Rate',
          value: totalApps > 0 ? `${approvalRate}%` : '—',
          change: totalApps > 0 ? `${totalApps} total processed` : 'Awaiting data',
          positive: parseFloat(approvalRate) >= 60,
        },
        {
          label: 'Best F1 Score',
          value: mlSummary?.best_f1 != null ? mlSummary.best_f1.toFixed(3) : '—',
          change: mlSummary?.best_f1 != null ? 'Model registry' : 'No models yet',
          positive: (mlSummary?.best_f1 ?? 0) > 0.8,
        },
        {
          label: 'Drift Alerts',
          value: alerts.length.toString(),
          change: alerts.length > 0 ? 'Action required' : 'All systems nominal',
          positive: alerts.length === 0,
        },
      ];
      setMetrics(liveMetrics);

      // Recent decisions from live applications (last 5)
      const recentDecisions: Decision[] = applications.slice(0, 5).map(app => ({
        id: app.application_id,
        applicant: app.applicant_name ?? 'Unknown',
        product: app.product_type ?? '—',
        amount: app.loan_amount ? formatCurrency(app.loan_amount) : '—',
        decision: app.decision ?? 'pending',
        grade: app.risk_grade ?? '—',
        time: timeAgo(app.submitted_at ?? app.created_at ?? new Date().toISOString()),
      }));
      setDecisions(recentDecisions);

    } catch {
      // Silent fail — dashboard shows fallback values
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="animate-in" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 320 }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="spin" style={{ marginBottom: 'var(--sp-3)' }} />
          <p>Loading platform overview…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Command Center</h2>
          <p>Real-time overview of CanvasML Studio platform operations</p>
        </div>
        <button
          className="btn btn-ghost"
          onClick={() => loadData(true)}
          disabled={refreshing}
          title="Refresh metrics"
          style={{ marginTop: 'var(--sp-1)' }}
        >
          <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Bento Metric Grid — Asymmetric */}
      <div className="bento-grid">
        {metrics.map((m, i) => (
          <div
            key={m.label}
            className={`glass-card metric-card stagger-item ${i < 2 ? 'bento-span-3' : 'bento-span-2'}`}
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <div className="metric-label">{m.label}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--sp-2)' }}>
              <div className="metric-value">{m.value}</div>
              {m.positive ? (
                <TrendingUp size={16} style={{ color: 'var(--success)', opacity: 0.7 }} />
              ) : (
                <TrendingDown size={16} style={{ color: 'var(--danger)', opacity: 0.7 }} />
              )}
            </div>
            <div className={`metric-change ${m.positive ? 'positive' : 'negative'}`}>
              {m.change}
            </div>
          </div>
        ))}
      </div>

      {/* Recent Decisions */}
      <div className="glass-card stagger-item" style={{ padding: 'var(--sp-5)', animationDelay: '400ms' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--sp-4)' }}>
          <h3 className="section-title" style={{ marginBottom: 0 }}>Recent Credit Decisions</h3>
          <button
            className="btn btn-ghost"
            style={{ fontSize: 'var(--fs-2xs)' }}
            onClick={() => navigate('/decisioning')}
          >
            View All <ArrowUpRight size={12} />
          </button>
        </div>

        {decisions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--sp-8) 0', color: 'var(--text-muted)' }}>
            <p style={{ fontSize: 'var(--fs-sm)' }}>No decisions yet.</p>
            <p style={{ fontSize: 'var(--fs-2xs)', marginTop: 'var(--sp-1)' }}>
              Submit an application from the{' '}
              <button
                className="btn btn-ghost"
                style={{ padding: 0, fontSize: 'inherit', color: 'var(--accent)', textDecoration: 'underline' }}
                onClick={() => navigate('/decisioning')}
              >
                Credit Decisioning
              </button>{' '}
              page to see results here.
            </p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Application</th><th>Applicant</th><th>Product</th>
                <th>Amount</th><th>Grade</th><th>Decision</th><th>Time</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((d) => (
                <tr key={d.id} style={{ cursor: 'pointer' }} onClick={() => navigate('/decisioning')}>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 'var(--fw-medium)' }}>{d.id}</td>
                  <td style={{ color: 'var(--text-primary)', fontWeight: 'var(--fw-medium)' }}>{d.applicant}</td>
                  <td>{d.product}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontFeatureSettings: "'tnum'" }}>{d.amount}</td>
                  <td><span className="badge badge-info">{d.grade}</span></td>
                  <td><span className={`badge ${BADGE_MAP[d.decision] ?? 'badge-info'}`}>{d.decision}</span></td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-2xs)' }}>{d.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
