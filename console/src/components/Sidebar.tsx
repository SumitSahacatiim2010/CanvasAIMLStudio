import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  BrainCircuit,
  Zap,
  BookOpen,
  Activity,
} from 'lucide-react';

const NAV_SECTIONS = [
  {
    title: 'Overview',
    items: [
      { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Data Platform',
    items: [
      { path: '/data', label: 'Data Sources', icon: Database },
    ],
  },
  {
    title: 'ML Platform',
    items: [
      { path: '/ml', label: 'ML Pipeline', icon: BrainCircuit },
    ],
  },
  {
    title: 'Agentic',
    items: [
      { path: '/decisioning', label: 'Credit Decisioning', icon: Zap },
    ],
  },
  {
    title: 'Knowledge',
    items: [
      { path: '/knowledge', label: 'Knowledge Base', icon: BookOpen },
    ],
  },
  {
    title: 'Ops',
    items: [
      { path: '/monitoring', label: 'Monitoring & Drift', icon: Activity },
    ],
  },
];

export function Sidebar() {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark">C</div>
        <h1>CanvasML Studio</h1>
      </div>

      <nav className="sidebar-nav">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title}>
            <div className="nav-section-title">{section.title}</div>
            {section.items.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `nav-link ${isActive ? 'active' : ''}`
                  }
                  end={item.path === '/'}
                >
                  <Icon size={18} strokeWidth={1.8} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="ambient-dot live" />
        <span>CanvasML Studio v0.1.0</span>
      </div>
    </aside>
  );
}
