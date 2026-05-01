/** Monitoring — drift detection and performance tracking. */
export function Monitoring() {
  const alerts = [
    { model: 'credit_risk_v2', metric: 'f1_score', baseline: 0.867, recent: 0.812, severity: 'moderate' },
    { model: 'churn_pred_v1', metric: 'accuracy', baseline: 0.891, recent: 0.855, severity: 'low' },
  ];
  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>Monitoring &amp; Drift</h2>
        <p>Model performance tracking and data drift detection</p>
      </div>
      <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="glass-card metric-card">
          <div className="metric-label">Active Monitors</div>
          <div className="metric-value">4</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Drift Alerts</div>
          <div className="metric-value">{alerts.length}</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Predictions (24h)</div>
          <div className="metric-value">2,847</div>
        </div>
      </div>
      <div className="glass-card" style={{ padding: 'var(--sp-5)' }}>
        <h3 style={{ fontSize: 'var(--fs-base)', fontWeight: 600, marginBottom: 'var(--sp-4)' }}>Performance Alerts</h3>
        <table className="data-table">
          <thead><tr><th>Model</th><th>Metric</th><th>Baseline</th><th>Recent</th><th>Degradation</th><th>Severity</th></tr></thead>
          <tbody>
            {alerts.map((a, i) => (
              <tr key={i}>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--c-text-primary)' }}>{a.model}</td>
                <td>{a.metric}</td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{a.baseline.toFixed(3)}</td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{a.recent.toFixed(3)}</td>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--c-danger)' }}>
                  {((a.baseline - a.recent) / a.baseline * 100).toFixed(1)}%
                </td>
                <td><span className={`badge ${a.severity === 'moderate' ? 'badge-warning' : 'badge-info'}`}>{a.severity}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
