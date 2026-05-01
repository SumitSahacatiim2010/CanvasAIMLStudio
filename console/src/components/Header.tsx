import { useLocation } from 'react-router-dom';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Command Center',
  '/data': 'Data Platform',
  '/ml': 'ML Pipeline Studio',
  '/decisioning': 'Credit Decisioning',
  '/knowledge': 'Knowledge Base',
  '/monitoring': 'Monitoring & Drift',
};

export function Header() {
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] || 'CanvasML Studio';

  return (
    <header className="app-header">
      <div>
        <h2 style={{ fontSize: 'var(--fs-md)', fontWeight: 600 }}>{title}</h2>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
        <span className="badge badge-success">● Live</span>
        <div style={{
          width: 32, height: 32, borderRadius: 'var(--radius-full)',
          background: 'var(--c-accent-gradient)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 'var(--fs-sm)', fontWeight: 600, color: 'white',
        }}>
          A
        </div>
      </div>
    </header>
  );
}
