/** Knowledge Base — RAG document management with proper upload modal. */
import { useState, useEffect } from 'react';
import { Search, FileText, Upload, Sparkles, Loader2, MessageSquare, X } from 'lucide-react';
import { fetchApi } from '../lib/api';

const TYPE_CLS: Record<string, string> = { regulatory: 'badge-warning', credit: 'badge-info', policy: 'badge-success', other: 'badge-secondary' };

type Document = { doc_id: string; title: string; doc_type: string; word_count: number; status: string; ingested_at: string; };
type Citation = { id: string; doc_id: string; excerpt: string; heading?: string; page?: number; };
type AskResponse = { question: string; answer: string; confidence: number; citations: Citation[]; follow_up_questions: string[]; };

export function KnowledgeBase() {
  const [query, setQuery] = useState('');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [asking, setAsking] = useState(false);
  const [askResponse, setAskResponse] = useState<AskResponse | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);

  const loadDocuments = async () => {
    try { setLoadingDocs(true); const data = await fetchApi('/rag/documents'); setDocuments(data.documents || []); }
    catch (err: any) { console.error(err); }
    finally { setLoadingDocs(false); }
  };

  useEffect(() => { loadDocuments(); }, []);

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const title = fd.get('title') as string;
    const text = fd.get('text') as string;
    const docType = fd.get('doc_type') as string;
    if (text.length < 10) { alert('Text must be at least 10 characters'); return; }
    try {
      setUploading(true);
      await fetchApi('/rag/ingest/text', { method: 'POST', body: JSON.stringify({ title, text, chunking_strategy: 'recursive', chunk_size: 1024, metadata: { doc_type: docType } }) });
      setShowUpload(false); await loadDocuments();
    } catch (err: any) { alert(`Upload failed: ${err.message}`); }
    finally { setUploading(false); }
  };

  const handleAsk = async () => {
    if (!query) return;
    try {
      setAsking(true); setAskResponse(null);
      const data = await fetchApi('/rag/ask', { method: 'POST', body: JSON.stringify({ question: query, top_k: 5 }) });
      setAskResponse(data);
    } catch (err: any) { alert(`Ask failed: ${err.message}`); }
    finally { setAsking(false); }
  };

  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div><h2>Knowledge Base</h2><p>RAG-powered document management, search, and Q&amp;A</p></div>
        <button className="btn btn-secondary" onClick={() => setShowUpload(true)}><Upload size={14} /> Upload Document</button>
      </div>

      {/* AI Search */}
      <div className="glass-card stagger-item" style={{ padding: 'var(--sp-5)', marginBottom: 'var(--sp-4)' }}>
        <div style={{ display: 'flex', gap: 'var(--sp-3)', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') handleAsk(); }} placeholder="Ask about policies, regulations, compliance..." className="input" style={{ paddingLeft: 40 }} disabled={asking} />
          </div>
          <button className="btn btn-primary" onClick={handleAsk} disabled={asking || !query}>
            {asking ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Sparkles size={14} />} Ask AI
          </button>
        </div>

        {askResponse && (
          <div style={{ marginTop: 'var(--sp-5)', paddingTop: 'var(--sp-4)', borderTop: '1px solid var(--border-light)' }}>
            <div style={{ display: 'flex', gap: 'var(--sp-3)', marginBottom: 'var(--sp-4)' }}>
              <Sparkles size={20} style={{ color: 'var(--primary)' }} />
              <div>
                <div style={{ fontWeight: 'var(--fw-medium)', marginBottom: 'var(--sp-2)' }}>Answer</div>
                <div style={{ color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{askResponse.answer}</div>
              </div>
            </div>
            {askResponse.citations.length > 0 && (
              <div style={{ marginLeft: 'var(--sp-8)', marginBottom: 'var(--sp-4)' }}>
                <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 'var(--fw-medium)', color: 'var(--text-muted)', marginBottom: 'var(--sp-2)' }}>CITATIONS</div>
                {askResponse.citations.map((c, i) => (
                  <div key={i} style={{ fontSize: 'var(--fs-xs)', background: 'var(--bg-card)', padding: 'var(--sp-3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-light)', marginBottom: 'var(--sp-2)' }}>
                    <span style={{ fontWeight: 'var(--fw-medium)', color: 'var(--primary)', marginRight: 'var(--sp-2)' }}>{c.id}</span>
                    <span style={{ color: 'var(--text-muted)' }}>{c.doc_id} {c.heading ? `- ${c.heading}` : ''}</span>
                    <div style={{ marginTop: 'var(--sp-1)', color: 'var(--text-secondary)', fontStyle: 'italic' }}>"{c.excerpt}..."</div>
                  </div>
                ))}
              </div>
            )}
            {askResponse.follow_up_questions.length > 0 && (
              <div style={{ marginLeft: 'var(--sp-8)' }}>
                <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 'var(--fw-medium)', color: 'var(--text-muted)', marginBottom: 'var(--sp-2)' }}>FOLLOW-UP QUESTIONS</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-2)' }}>
                  {askResponse.follow_up_questions.map((q, i) => (
                    <button key={i} className="btn btn-secondary" style={{ fontSize: 'var(--fs-xs)', padding: '4px 10px' }} onClick={() => { setQuery(q); setTimeout(handleAsk, 0); }}>
                      <MessageSquare size={12} /> {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Document Library */}
      <div className="glass-card stagger-item" style={{ padding: 'var(--sp-5)', animationDelay: '120ms' }}>
        <h3 className="section-title"><FileText size={16} /> Document Library</h3>
        <table className="data-table">
          <thead><tr><th>Document</th><th>Type</th><th>Word Count</th><th>Status</th></tr></thead>
          <tbody>
            {loadingDocs ? (<tr><td colSpan={4} style={{ textAlign: 'center', padding: 'var(--sp-8)' }}><Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} /></td></tr>
            ) : documents.length === 0 ? (<tr><td colSpan={4} style={{ textAlign: 'center', padding: 'var(--sp-8)', color: 'var(--text-muted)' }}>No documents found.</td></tr>
            ) : documents.map((d) => (
              <tr key={d.doc_id}>
                <td><div style={{ color: 'var(--text-primary)', fontWeight: 'var(--fw-medium)' }}>{d.title}</div><div style={{ fontSize: 'var(--fs-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>{d.doc_id}</div></td>
                <td><span className={`badge ${TYPE_CLS[d.doc_type] || 'badge-info'}`}>{d.doc_type}</span></td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{d.word_count}</td>
                <td><span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--sp-1)' }}><span className={`ambient-dot ${d.status === 'indexed' ? 'live' : ''}`} style={{ width: 6, height: 6, background: d.status === 'indexed' ? 'var(--success)' : 'var(--warning)' }} /><span style={{ fontSize: 'var(--fs-2xs)', color: d.status === 'indexed' ? 'var(--success)' : 'var(--warning)' }}>{d.status}</span></span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <div className="modal-backdrop"><div className="modal-content glass-card animate-in">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--sp-4)' }}>
            <h3 style={{ margin: 0 }}>Upload Document</h3>
            <button className="btn btn-ghost" onClick={() => setShowUpload(false)} style={{ padding: 'var(--sp-2)' }}><X size={16} /></button>
          </div>
          <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
            <div className="form-group"><label>Document Title</label><input name="title" type="text" className="input-field" placeholder="E.g., RBI Master Direction 2024" required /></div>
            <div className="form-group"><label>Document Type</label><select name="doc_type" className="input-field"><option value="regulatory">Regulatory</option><option value="credit">Credit Policy</option><option value="policy">Internal Policy</option><option value="other">Other</option></select></div>
            <div className="form-group"><label>Document Text</label><textarea name="text" className="input-field" rows={6} placeholder="Paste the document content here (min 10 characters)..." required style={{ resize: 'vertical' }} /></div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--sp-3)' }}>
              <button type="button" className="btn btn-ghost" onClick={() => setShowUpload(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={uploading}>{uploading ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Upload size={14} />} Ingest Document</button>
            </div>
          </form>
        </div></div>
      )}
    </div>
  );
}
