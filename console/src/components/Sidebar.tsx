import { NavLink, useLocation } from 'react-router-dom';

const NAV_SECTIONS = [
  {
    title: 'Overview',
    items: [
      { path: '/', label: 'Dashboard', icon: '📊' },
    ],
  },
  {
    title: 'Data Platform',
    items: [
      { path: '/data', label: 'Data Sources', icon: '🗄️' },
    ],
  },
  {
    title: 'ML Platform',
    items: [
      { path: '/ml', label: 'ML Pipeline', icon: '🧠' },
    ],
  },
  {
    title: 'Agentic',
    items: [
      { path: '/decisioning', label: 'Credit Decisioning', icon: '⚡' },
    ],
  },
  {
    title: 'Knowledge',
    items: [
      { path: '/knowledge', label: 'RAG Knowledge Base', icon: '📚' },
    ],
  },
  {
    title: 'Ops',
    items: [
      { path: '/monitoring', label: 'Monitoring & Drift', icon: '📈' },
    ],
  },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <aside className="app-sidebar">
      <div className="sidebar-logo">
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: 'var(--c-accent-gradient)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '16px', fontWeight: 700, color: 'white',
        }}>
          C
        </div>
        <h1>CanvasML Studio</h1>
      </div>

      <nav className="sidebar-nav">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title}>
            <div className="nav-section-title">{section.title}</div>
            {section.items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active' : ''}`
                }
                end={item.path === '/'}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div style={{
        padding: 'var(--sp-4)',
        borderTop: '1px solid var(--c-border)',
        fontSize: 'var(--fs-xs)',
        color: 'var(--c-text-muted)',
      }}>
        CanvasML Studio v0.1.0
      </div>
    </aside>
  );
}
