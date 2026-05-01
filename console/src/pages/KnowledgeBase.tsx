/** Knowledge Base — RAG document management and Q&A interface. */
import { useState } from 'react';

const DOCS = [
  { id: 'DOC-001', title: 'RBI Master Direction on Lending', type: 'regulatory', chunks: 42 },
  { id: 'DOC-002', title: 'Internal Credit Policy v3.2', type: 'credit', chunks: 28 },
  { id: 'DOC-003', title: 'MAS FEAT Assessment Framework', type: 'regulatory', chunks: 35 },
  { id: 'DOC-004', title: 'DPDP Act Compliance Handbook', type: 'regulatory', chunks: 56 },
];

export function KnowledgeBase() {
  const [query, setQuery] = useState('');
  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>Knowledge Base</h2>
        <p>RAG-powered document management, search, and Q&amp;A</p>
      </div>
      <div className="glass-card" style={{ padding: 'var(--sp-5)', marginBottom: 'var(--sp-4)' }}>
        <div style={{ display: 'flex', gap: 'var(--sp-3)' }}>
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about policies, regulations..." style={{
              flex: 1, padding: 'var(--sp-3) var(--sp-4)', background: 'var(--c-bg-input)',
              border: '1px solid var(--c-border)', borderRadius: 'var(--radius-md)',
              color: 'var(--c-text-primary)', fontSize: 'var(--fs-base)', outline: 'none',
            }} />
          <button className="btn btn-primary">Ask AI</button>
        </div>
      </div>
      <div className="glass-card" style={{ padding: 'var(--sp-5)' }}>
        <h3 style={{ fontSize: 'var(--fs-base)', fontWeight: 600, marginBottom: 'var(--sp-4)' }}>Document Library</h3>
        <table className="data-table">
          <thead><tr><th>Document</th><th>Type</th><th>Chunks</th></tr></thead>
          <tbody>
            {DOCS.map((d) => (
              <tr key={d.id}>
                <td style={{ color: 'var(--c-text-primary)', fontWeight: 500 }}>{d.title}</td>
                <td><span className="badge badge-warning">{d.type}</span></td>
                <td>{d.chunks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
