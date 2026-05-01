/** Data Sources — connector management and catalog view. */

const SOURCES = [
  { id: 'src-001', name: 'Core Banking DB', type: 'postgres', status: 'active', datasets: 24, lastSync: '5 min ago' },
  { id: 'src-002', name: 'Document Store', type: 's3', status: 'active', datasets: 156, lastSync: '12 min ago' },
  { id: 'src-003', name: 'Bureau Data Feed', type: 'api', status: 'active', datasets: 3, lastSync: '1 hr ago' },
  { id: 'src-004', name: 'Risk Analytics DW', type: 'postgres', status: 'active', datasets: 42, lastSync: '30 min ago' },
  { id: 'src-005', name: 'HR Records', type: 'csv', status: 'inactive', datasets: 8, lastSync: '2 days ago' },
];

const STATUS_BADGE: Record<string, string> = { active: 'badge-success', inactive: 'badge-warning', error: 'badge-danger' };
const TYPE_ICONS: Record<string, string> = { postgres: '🐘', s3: '☁️', csv: '📄', api: '🔌' };

export function DataSources() {
  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Data Sources</h2>
          <p>Manage connectors, discover schemas, and browse the data catalog</p>
        </div>
        <button className="btn btn-primary">+ Add Source</button>
      </div>

      <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="glass-card metric-card">
          <div className="metric-label">Total Sources</div>
          <div className="metric-value">{SOURCES.length}</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Active Connections</div>
          <div className="metric-value">{SOURCES.filter(s => s.status === 'active').length}</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-label">Total Datasets</div>
          <div className="metric-value">{SOURCES.reduce((a, s) => a + s.datasets, 0)}</div>
        </div>
      </div>

      <div className="glass-card" style={{ padding: 'var(--sp-5)' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Type</th>
              <th>Status</th>
              <th>Datasets</th>
              <th>Last Sync</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {SOURCES.map((s) => (
              <tr key={s.id}>
                <td style={{ color: 'var(--c-text-primary)', fontWeight: 500 }}>
                  {s.name}
                  <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--c-text-muted)', fontFamily: 'var(--font-mono)' }}>{s.id}</div>
                </td>
                <td>{TYPE_ICONS[s.type] || '📦'} {s.type}</td>
                <td><span className={`badge ${STATUS_BADGE[s.status]}`}>{s.status}</span></td>
                <td>{s.datasets}</td>
                <td>{s.lastSync}</td>
                <td>
                  <button className="btn btn-secondary" style={{ fontSize: 'var(--fs-xs)', padding: '2px 8px' }}>
                    Discover
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
