/** ML Pipeline — model training, comparison, and registry. */

const MODELS = [
  { id: 'credit_risk_v3', algo: 'XGBoost', status: 'deployed', f1: 0.892, auc: 0.941, drift: 'none', trainedAt: '2026-04-28' },
  { id: 'credit_risk_v2', algo: 'Random Forest', status: 'retired', f1: 0.867, auc: 0.923, drift: 'moderate', trainedAt: '2026-04-15' },
  { id: 'fraud_detect_v1', algo: 'LightGBM', status: 'deployed', f1: 0.934, auc: 0.967, drift: 'none', trainedAt: '2026-04-20' },
  { id: 'churn_pred_v1', algo: 'Logistic Reg', status: 'validated', f1: 0.812, auc: 0.878, drift: 'low', trainedAt: '2026-04-25' },
];

const STATUS_CLS: Record<string, string> = {
  deployed: 'badge-success', validated: 'badge-info', retired: 'badge-warning', failed: 'badge-danger',
};

const DRIFT_CLS: Record<string, string> = {
  none: 'badge-success', low: 'badge-info', moderate: 'badge-warning', high: 'badge-danger',
};

export function MLPipeline() {
  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>ML Pipeline Studio</h2>
          <p>Train, compare, deploy, and monitor ML models</p>
        </div>
        <button className="btn btn-primary">+ New Experiment</button>
      </div>

      <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="glass-card metric-card">
          <div className="metric-label">Registered Models</div>
          <div className="metric-value">{MODELS.length}</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Deployed</div>
          <div className="metric-value">{MODELS.filter(m => m.status === 'deployed').length}</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Best F1 Score</div>
          <div className="metric-value">{Math.max(...MODELS.map(m => m.f1)).toFixed(3)}</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Drift Alerts</div>
          <div className="metric-value">{MODELS.filter(m => m.drift !== 'none').length}</div>
        </div>
      </div>

      <div className="glass-card" style={{ padding: 'var(--sp-5)' }}>
        <h3 style={{ fontSize: 'var(--fs-base)', fontWeight: 600, marginBottom: 'var(--sp-4)' }}>Model Registry</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Algorithm</th>
              <th>Status</th>
              <th>F1 Score</th>
              <th>ROC AUC</th>
              <th>Drift</th>
              <th>Trained</th>
            </tr>
          </thead>
          <tbody>
            {MODELS.map((m) => (
              <tr key={m.id}>
                <td style={{ color: 'var(--c-text-primary)', fontWeight: 500, fontFamily: 'var(--font-mono)' }}>{m.id}</td>
                <td>{m.algo}</td>
                <td><span className={`badge ${STATUS_CLS[m.status]}`}>{m.status}</span></td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{m.f1.toFixed(3)}</td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{m.auc.toFixed(3)}</td>
                <td><span className={`badge ${DRIFT_CLS[m.drift]}`}>{m.drift}</span></td>
                <td>{m.trainedAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
