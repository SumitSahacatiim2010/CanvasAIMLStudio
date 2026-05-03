import { useLocation } from 'react-router-dom';
import { Bell, Search } from 'lucide-react';

const PAGE_TITLES: Record<string, { title: string; sub: string }> = {
  '/': { title: 'Command Center', sub: 'Real-time platform overview' },
  '/data': { title: 'Data Platform', sub: 'Connectors & catalog' },
  '/ml': { title: 'ML Pipeline Studio', sub: 'Train · Deploy · Monitor' },
  '/decisioning': { title: 'Credit Decisioning', sub: 'Agentic workflow engine' },
  '/knowledge': { title: 'Knowledge Base', sub: 'RAG-powered search & Q&A' },
  '/monitoring': { title: 'Monitoring & Drift', sub: 'Performance tracking' },
};

export function Header() {
  const location = useLocation();
  const page = PAGE_TITLES[location.pathname] || { title: 'CanvasML Studio', sub: '' };

  return (
    <header className="app-header">
      <div>
        <h2 style={{
          fontSize: 'var(--fs-md)',
          fontWeight: 'var(--fw-semibold)',
          letterSpacing: 'var(--ls-tight)',
          lineHeight: 'var(--lh-tight)',
        }}>
          {page.title}
        </h2>
        {page.sub && (
          <p style={{
            fontSize: 'var(--fs-2xs)',
            color: 'var(--text-muted)',
            marginTop: '2px',
            letterSpacing: 'var(--ls-wide)',
          }}>
            {page.sub}
          </p>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
        <button className="btn btn-ghost" aria-label="Search">
          <Search size={16} strokeWidth={1.8} />
        </button>
        <button className="btn btn-ghost" style={{ position: 'relative' }} aria-label="Notifications">
          <Bell size={16} strokeWidth={1.8} />
          <span style={{
            position: 'absolute',
            top: 2,
            right: 2,
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: 'var(--danger)',
            border: '1.5px solid var(--surface-1)',
          }} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
          <div className="ambient-dot live" />
          <span style={{
            fontSize: 'var(--fs-2xs)',
            fontWeight: 'var(--fw-semibold)',
            color: 'var(--success)',
            letterSpacing: 'var(--ls-wide)',
          }}>
            LIVE
          </span>
        </div>

        <div style={{
          width: 32,
          height: 32,
          borderRadius: 'var(--radius-pill)',
          background: 'var(--accent-gradient)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 'var(--fs-sm)',
          fontWeight: 'var(--fw-bold)',
          color: 'white',
          boxShadow: '0 0 0 2px var(--surface-1), 0 0 0 4px oklch(0.65 0.22 264 / 0.2)',
          cursor: 'pointer',
          transition: 'transform var(--dur-fast) var(--ease-spring)',
        }}
          onMouseEnter={(e) => { (e.target as HTMLElement).style.transform = 'scale(1.08)'; }}
          onMouseLeave={(e) => { (e.target as HTMLElement).style.transform = 'scale(1)'; }}
        >
          A
        </div>
      </div>
    </header>
  );
}
