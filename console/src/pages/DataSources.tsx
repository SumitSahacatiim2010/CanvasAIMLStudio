/** Data Sources — connector management with proper modal. */
import { useState, useEffect } from 'react';
import { Database, Cloud, FileText, Plug, Plus, RefreshCw, Loader2, X } from 'lucide-react';
import { fetchApi } from '../lib/api';

const STATUS_BADGE: Record<string, string> = { active: 'badge-success', inactive: 'badge-warning', error: 'badge-danger' };
const TYPE_ICONS: Record<string, typeof Database> = { postgres: Database, s3: Cloud, csv: FileText, api: Plug };

type Source = { id: string; name: string; type: string; status: string; description: string; created_at: string; datasets?: number; lastSync?: string; };

export function DataSources() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [adding, setAdding] = useState(false);

  const loadSources = async () => {
    try { setLoading(true); const data = await fetchApi('/catalog/sources'); setSources(data); setError(null); }
    catch (err: any) { setError(err.message || 'Failed to load sources'); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadSources(); }, []);

  const handleAddSource = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      setAdding(true);
      await fetchApi('/catalog/sources', { method: 'POST', body: JSON.stringify({ name: fd.get('name'), type: fd.get('type'), config: {}, description: fd.get('description') || 'Added via UI' }) });
      setShowModal(false); await loadSources();
    } catch (err: any) { alert(`Error: ${err.message}`); }
    finally { setAdding(false); }
  };

  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div><h2>Data Sources</h2><p>Manage connectors, discover schemas, and browse the data catalog</p></div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={16} /> Add Source</button>
      </div>

      <div className="bento-grid" style={{ marginBottom: 'var(--sp-6)' }}>
        {[{ label: 'Total Sources', value: sources.length }, { label: 'Active', value: sources.filter(s => s.status === 'active').length }, { label: 'Datasets', value: sources.reduce((a, s) => a + (s.datasets || 0), 0) }].map((m, i) => (
          <div key={m.label} className="glass-card metric-card bento-span-2 stagger-item" style={{ animationDelay: `${i * 60}ms` }}>
            <div className="metric-label">{m.label}</div><div className="metric-value">{m.value}</div>
          </div>
        ))}
      </div>

      <div className="glass-card stagger-item" style={{ padding: 'var(--sp-5)', animationDelay: '200ms' }}>
        <table className="data-table">
          <thead><tr><th>Source</th><th>Type</th><th>Status</th><th>Datasets</th><th>Last Sync</th><th>Actions</th></tr></thead>
          <tbody>
            {loading ? (<tr><td colSpan={6} style={{ textAlign: 'center', padding: 'var(--sp-8)' }}><Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} /></td></tr>
            ) : error ? (<tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--danger)' }}>{error}</td></tr>
            ) : sources.length === 0 ? (<tr><td colSpan={6} style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>No sources found. Add one to get started.</td></tr>
            ) : sources.map((s) => {
              const Icon = TYPE_ICONS[s.type] || Database;
              return (<tr key={s.id}>
                <td><div style={{ color: 'var(--text-primary)', fontWeight: 'var(--fw-medium)' }}>{s.name}</div><div style={{ fontSize: 'var(--fs-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>{s.id}</div></td>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}><Icon size={14} style={{ opacity: 0.6 }} /><span>{s.type}</span></div></td>
                <td><span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--sp-1)' }}><span className={`ambient-dot ${s.status === 'active' ? 'live' : 'warning'}`} style={{ width: 6, height: 6 }} /><span className={`badge ${STATUS_BADGE[s.status]}`}>{s.status}</span></span></td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{s.datasets || 0}</td>
                <td style={{ fontSize: 'var(--fs-2xs)', color: 'var(--text-muted)' }}>{s.lastSync || 'N/A'}</td>
                <td><button className="btn btn-secondary" style={{ fontSize: 'var(--fs-2xs)', padding: '4px 10px' }} onClick={async () => { try { await fetchApi(`/catalog/sources/${s.id}/discover`, { method: 'POST' }); alert('Discovery started!'); } catch (err: any) { alert(`Failed: ${err.message}`); } }}><RefreshCw size={12} /> Discover</button></td>
              </tr>);
            })}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-backdrop"><div className="modal-content glass-card animate-in">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--sp-4)' }}>
            <h3 style={{ margin: 0 }}>Add Data Source</h3>
            <button className="btn btn-ghost" onClick={() => setShowModal(false)} style={{ padding: 'var(--sp-2)' }}><X size={16} /></button>
          </div>
          <form onSubmit={handleAddSource} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
            <div className="form-group"><label>Source Name</label><input name="name" type="text" className="input-field" placeholder="E.g., Production Analytics DB" required /></div>
            <div className="form-group"><label>Connector Type</label><select name="type" className="input-field" required><option value="postgres">PostgreSQL</option><option value="s3">S3 / Object Store</option><option value="csv">CSV File</option><option value="api">REST API</option></select></div>
            <div className="form-group"><label>Description</label><input name="description" type="text" className="input-field" placeholder="Brief description" /></div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--sp-3)', marginTop: 'var(--sp-2)' }}>
              <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={adding}>{adding ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Plus size={14} />} Add Source</button>
            </div>
          </form>
        </div></div>
      )}
    </div>
  );
}
