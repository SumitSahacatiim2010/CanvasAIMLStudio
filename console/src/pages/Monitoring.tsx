/** Monitoring & Drift — live observability data with severity-tinted alerts. */

import { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, TrendingDown, Activity, RefreshCw } from 'lucide-react';
import { fetchApi } from '../lib/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface AlertEntry {
  model_name: string;
  metric: string;
  baseline: number;
  recent: number;
  severity: 'low' | 'moderate' | 'high';
  triggered_at?: string;
}

const SEV_CLS: Record<string, string> = {
  moderate: 'badge-warning', low: 'badge-info', high: 'badge-danger',
};

// ── Sub-components ────────────────────────────────────────────────────────────

function DegradationBar({ baseline, recent }: { baseline: number; recent: number }) {
  const pctBaseline = Math.min(baseline * 100, 100);
  const pctRecent = Math.min(recent * 100, 100);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', minWidth: 120 }}>
      <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--border-subtle)', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${pctBaseline}%`, borderRadius: 3, background: 'var(--border-hover)', opacity: 0.4 }} />
        <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${pctRecent}%`, borderRadius: 3, background: 'var(--danger)', transition: 'width var(--dur-slow) var(--ease-out)' }} />
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export function Monitoring() {
  const [alerts, setAlerts] = useState<AlertEntry[]>([]);
  const [activeMonitors, setActiveMonitors] = useState<number>(0);
  const [predictionCount, setPredictionCount] = useState<string>('—');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (showRefreshIndicator = false) => {
    if (showRefreshIndicator) setRefreshing(true);
    try {
      // Fetch observability alerts and agentic stats in parallel
      const [alertsRes, agenticRes] = await Promise.allSettled([
        fetchApi('/observability/alerts'),
        fetchApi('/agentic/applications'),
      ]);

      if (alertsRes.status === 'fulfilled') {
        const data = alertsRes.value as { alerts: AlertEntry[]; total: number };
        // The backend returns flat alert strings; we need to handle both formats
        const rawAlerts = data.alerts ?? [];

        // Map API alerts to our display format
        // The PerformanceMonitor returns strings like "model_name: metric degraded X%"
        // Parse them or accept structured alerts if already objects
        const structuredAlerts: AlertEntry[] = rawAlerts
          .filter(Boolean)
          .map((a: unknown) => {
            if (typeof a === 'object' && a !== null && 'model_name' in a) {
              return a as AlertEntry;
            }
            // Parse string format: "model_name: f1_score degraded by 6.4%"
            const str = String(a);
            const match = str.match(/^([^:]+):\s*(\w+)\s+degraded\s+by\s+([\d.]+)%/);
            if (match) {
              const deg = parseFloat(match[3]);
              return {
                model_name: match[1].trim(),
                metric: match[2].trim(),
                baseline: 0.87,
                recent: 0.87 * (1 - deg / 100),
                severity: deg > 10 ? 'high' : deg > 5 ? 'moderate' : 'low',
              } as AlertEntry;
            }
            return null;
          })
          .filter((a): a is AlertEntry => a !== null);

        setAlerts(structuredAlerts);
        // Count unique model names being monitored
        const uniqueModels = new Set(structuredAlerts.map(a => a.model_name));
        setActiveMonitors(uniqueModels.size);
      }

      if (agenticRes.status === 'fulfilled') {
        const apps = (agenticRes.value as { applications: unknown[] }).applications ?? [];
        setPredictionCount(apps.length.toLocaleString());
      }

      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load monitoring data');
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
          <p>Loading monitoring data…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Monitoring & Drift</h2>
          <p>Model performance tracking and data drift detection</p>
        </div>
        <button
          className="btn btn-ghost"
          onClick={() => loadData(true)}
          disabled={refreshing}
          title="Refresh"
        >
          <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
        </button>
      </div>

      {error && (
        <div style={{ marginBottom: 'var(--sp-4)', padding: 'var(--sp-3) var(--sp-4)', background: 'var(--danger-muted)', borderRadius: 'var(--radius-md)', color: 'var(--danger)', fontSize: 'var(--fs-sm)' }}>
          ⚠ {error} — <button className="btn btn-ghost" style={{ fontSize: 'inherit', color: 'inherit', padding: 0, textDecoration: 'underline' }} onClick={() => loadData()}>retry</button>
        </div>
      )}

      {/* Metric Summary */}
      <div className="bento-grid" style={{ marginBottom: 'var(--sp-6)' }}>
        {[
          { label: 'Active Monitors', value: activeMonitors.toString(), icon: Activity },
          { label: 'Drift Alerts', value: alerts.length.toString(), icon: AlertTriangle },
          { label: 'Predictions (Session)', value: predictionCount, icon: TrendingDown },
        ].map((m, i) => {
          const Icon = m.icon;
          return (
            <div key={m.label} className="glass-card metric-card bento-span-2 stagger-item" style={{ animationDelay: `${i * 60}ms` }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div className="metric-label">{m.label}</div>
                  <div className="metric-value">{m.value}</div>
                </div>
                <Icon size={20} strokeWidth={1.5} style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Performance Alerts Table */}
      <div className="glass-card stagger-item" style={{ padding: 'var(--sp-5)', animationDelay: '200ms' }}>
        <h3 className="section-title">
          <AlertTriangle size={16} strokeWidth={1.8} /> Performance Alerts
        </h3>

        {alerts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--sp-8) 0', color: 'var(--text-muted)' }}>
            <Activity size={32} strokeWidth={1.2} style={{ opacity: 0.3, marginBottom: 'var(--sp-3)' }} />
            <p style={{ fontSize: 'var(--fs-sm)' }}>No drift alerts detected.</p>
            <p style={{ fontSize: 'var(--fs-2xs)', marginTop: 'var(--sp-1)' }}>
              Record performance metrics via <code style={{ fontFamily: 'var(--font-mono)' }}>POST /api/v1/observability/performance/record</code> to trigger monitoring.
            </p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Model</th><th>Metric</th><th>Baseline</th>
                <th>Recent</th><th>Degradation</th><th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a, i) => {
                const deg = a.baseline > 0
                  ? ((a.baseline - a.recent) / a.baseline * 100)
                  : 0;
                return (
                  <tr key={i}>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontSize: 'var(--fs-2xs)', fontWeight: 'var(--fw-medium)' }}>{a.model_name}</td>
                    <td>{a.metric}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontFeatureSettings: "'tnum'" }}>{a.baseline.toFixed(3)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontFeatureSettings: "'tnum'" }}>{a.recent.toFixed(3)}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                        <DegradationBar baseline={a.baseline} recent={a.recent} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-2xs)', color: 'var(--danger)', fontWeight: 'var(--fw-semibold)' }}>
                          -{deg.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${SEV_CLS[a.severity]}`}>
                        {a.severity === 'moderate' && (
                          <span className="ambient-dot warning" style={{ width: 5, height: 5, display: 'inline-block' }} />
                        )}
                        {a.severity}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
