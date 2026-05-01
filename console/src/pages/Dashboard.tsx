/** Command Center — executive overview of the entire platform. */

const METRICS = [
  { label: 'Data Sources', value: '12', change: '+2 this week', positive: true },
  { label: 'ML Models', value: '8', change: '3 deployed', positive: true },
  { label: 'Applications Today', value: '147', change: '+23% vs yesterday', positive: true },
  { label: 'Approval Rate', value: '68.4%', change: '-2.1% vs baseline', positive: false },
  { label: 'Avg Latency', value: '1.2s', change: 'P99: 3.4s', positive: true },
  { label: 'Drift Alerts', value: '2', change: 'Moderate severity', positive: false },
];

const RECENT_DECISIONS = [
  { id: 'APP-000147', applicant: 'Rajesh K.', product: 'Personal Loan', amount: '₹5,00,000', decision: 'approved', grade: 'B', time: '2m ago' },
  { id: 'APP-000146', applicant: 'Priya M.', product: 'Home Loan', amount: '₹35,00,000', decision: 'referred', grade: 'C', time: '8m ago' },
  { id: 'APP-000145', applicant: 'Amit S.', product: 'Credit Card', amount: '₹2,00,000', decision: 'approved', grade: 'A', time: '15m ago' },
  { id: 'APP-000144', applicant: 'Neha D.', product: 'Personal Loan', amount: '₹3,50,000', decision: 'rejected', grade: 'E', time: '22m ago' },
  { id: 'APP-000143', applicant: 'Vikram P.', product: 'Business Loan', amount: '₹12,00,000', decision: 'approved', grade: 'B', time: '31m ago' },
];

const BADGE_MAP: Record<string, string> = {
  approved: 'badge-success',
  rejected: 'badge-danger',
  referred: 'badge-warning',
};

export function Dashboard() {
  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>Command Center</h2>
        <p>Real-time overview of CanvasML Studio platform operations</p>
      </div>

      {/* Metric Cards */}
      <div className="metric-grid">
        {METRICS.map((m) => (
          <div key={m.label} className="glass-card metric-card">
            <div className="metric-label">{m.label}</div>
            <div className="metric-value">{m.value}</div>
            <div className={`metric-change ${m.positive ? 'positive' : 'negative'}`}>
              {m.change}
            </div>
          </div>
        ))}
      </div>

      {/* Recent Decisions Table */}
      <div className="glass-card" style={{ padding: 'var(--sp-5)' }}>
        <h3 style={{ fontSize: 'var(--fs-base)', fontWeight: 600, marginBottom: 'var(--sp-4)' }}>
          Recent Credit Decisions
        </h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Application</th>
              <th>Applicant</th>
              <th>Product</th>
              <th>Amount</th>
              <th>Grade</th>
              <th>Decision</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {RECENT_DECISIONS.map((d) => (
              <tr key={d.id}>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--c-accent)' }}>{d.id}</td>
                <td style={{ color: 'var(--c-text-primary)' }}>{d.applicant}</td>
                <td>{d.product}</td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{d.amount}</td>
                <td><span className="badge badge-info">{d.grade}</span></td>
                <td><span className={`badge ${BADGE_MAP[d.decision]}`}>{d.decision}</span></td>
                <td>{d.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
