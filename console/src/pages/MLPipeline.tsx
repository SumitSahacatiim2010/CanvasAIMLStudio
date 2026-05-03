/** ML Pipeline Studio — live model registry + experiment launcher. */

import { useState, useEffect, useCallback } from 'react';
import { FlaskConical, TrendingUp, RefreshCw, X, ChevronDown, Sparkles, Wand2, Eye } from 'lucide-react';
import { fetchApi } from '../lib/api';
import { ExperimentModal as ExperimentDetailModal } from '../components/ml/ExperimentModal';

// ── Types ────────────────────────────────────────────────────────────────────

interface ModelEntry {
  model_id: string;
  name: string;
  version: number;
  algorithm: string;
  status: 'trained' | 'validated' | 'deployed' | 'retired' | 'failed';
  metrics: { f1?: number; auc?: number; accuracy?: number; [key: string]: number | undefined };
  drift: 'none' | 'low' | 'moderate' | 'high';
  trained_at: string;
  tags: Record<string, string>;
}

interface Experiment {
  experiment_id: string;
  experiment_name: string;
  task_type: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'pending';
  algorithms: string[];
  cv_folds: number;
  results: any;
  error: string | null;
  reasoning?: string;
  trace?: any[];
  created_at: string;
  completed_at: string | null;
}

// ── Constants ────────────────────────────────────────────────────────────────

const STATUS_CLS: Record<string, string> = {
  deployed: 'badge-success', validated: 'badge-info', trained: 'badge-info',
  retired: 'badge-warning', failed: 'badge-danger',
};

const DRIFT_CLS: Record<string, string> = {
  none: 'badge-success', low: 'badge-info', moderate: 'badge-warning', high: 'badge-danger',
};

const EXP_STATUS_CLS: Record<string, string> = {
  queued: 'badge-info', running: 'badge-warning', completed: 'badge-success', failed: 'badge-danger',
};

const AVAILABLE_ALGOS = [
  'logistic_regression', 'random_forest', 'gradient_boosting', 'xgboost', 'lightgbm',
];

// ── Sub-components ───────────────────────────────────────────────────────────

function MiniBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontFeatureSettings: "'tnum'", minWidth: 42 }}>
        {value.toFixed(3)}
      </span>
      <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'var(--border-subtle)', overflow: 'hidden', minWidth: 48 }}>
        <div style={{
          height: '100%', width: `${pct}%`, borderRadius: 2,
          background: pct > 90 ? 'var(--success)' : pct > 80 ? 'var(--info)' : 'var(--warning)',
          transition: 'width var(--dur-slow) var(--ease-out)',
        }} />
      </div>
    </div>
  );
}

// ── New Experiment Modal ─────────────────────────────────────────────────────

interface ExperimentModalProps {
  onClose: () => void;
  onSubmit: (exp: Experiment) => void;
}

function ExperimentModal({ onClose, onSubmit }: ExperimentModalProps) {
  const [mode, setMode] = useState<'manual' | 'auto'>('manual');
  const [name, setName] = useState('credit_risk_experiment');
  const [taskType, setTaskType] = useState<'binary_classification' | 'multiclass_classification' | 'regression'>('binary_classification');
  const [selectedAlgos, setSelectedAlgos] = useState<string[]>(['random_forest', 'gradient_boosting']);
  const [cvFolds, setCvFolds] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleAlgo = (algo: string) => {
    setSelectedAlgos(prev =>
      prev.includes(algo) ? prev.filter(a => a !== algo) : [...prev, algo]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'manual' && selectedAlgos.length === 0) { setError('Select at least one algorithm.'); return; }
    setLoading(true); setError(null);
    try {
      let result;
      if (mode === 'auto') {
        result = await fetchApi('/ml/automl/auto', {
          method: 'POST',
          body: JSON.stringify({ dataset_path: "data/credit_risk_BFSI.csv" }),
        });
        const exp: Experiment = {
          experiment_id: result.experiment_id || `auto_${Date.now()}`,
          experiment_name: `AutoML_${name}`,
          status: result.errors?.length ? 'failed' : 'completed',
          algorithms: result.algorithm ? [result.algorithm] : [],
          task_type: taskType,
          cv_folds: cvFolds,
          created_at: new Date().toISOString(),
          completed_at: result.completed_at,
          results: result.model_id ? [{ model_id: result.model_id, algorithm: result.algorithm, metrics: result.metrics }] : [],
          error: result.errors?.length ? result.errors[0].error : null,
          reasoning: result.reasoning,
          trace: result.trace,
        };
        onSubmit(exp);
      } else {
        result = await fetchApi('/ml/experiments', {
          method: 'POST',
          body: JSON.stringify({
            experiment_name: name.trim(),
            task_type: taskType,
            algorithms: selectedAlgos,
            cv_folds: cvFolds,
          }),
        });
        onSubmit(result as Experiment);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start experiment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
            <FlaskConical size={18} strokeWidth={1.8} style={{ color: 'var(--accent)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--fs-md)', fontWeight: 'var(--fw-semibold)' }}>
              New Experiment
            </h3>
          </div>
          <button className="btn btn-ghost" onClick={onClose} style={{ padding: 'var(--sp-1)' }}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)', padding: 'var(--sp-5)' }}>
          {error && (
            <div style={{ padding: 'var(--sp-3)', background: 'var(--danger-muted)', borderRadius: 'var(--radius-md)', color: 'var(--danger)', fontSize: 'var(--fs-sm)' }}>
              {error}
            </div>
          )}

          <div className="form-group" style={{ marginBottom: 'var(--sp-2)' }}>
            <label className="form-label">Mode</label>
            <div style={{ display: 'flex', background: 'var(--bg-subtle)', padding: 'var(--sp-1)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)' }}>
              <button
                type="button"
                className={`btn btn-sm ${mode === 'manual' ? 'btn-primary' : 'btn-ghost'}`}
                style={{ flex: 1, borderRadius: 'var(--radius-md)', fontSize: 'var(--fs-2xs)' }}
                onClick={() => setMode('manual')}
              >
                Manual Comparison
              </button>
              <button
                type="button"
                className={`btn btn-sm ${mode === 'auto' ? 'btn-primary' : 'btn-ghost'}`}
                style={{
                  flex: 1, borderRadius: 'var(--radius-md)', fontSize: 'var(--fs-2xs)',
                  background: mode === 'auto' ? 'linear-gradient(135deg, var(--accent) 0%, #a855f7 100%)' : 'transparent',
                  border: 'none', color: mode === 'auto' ? 'white' : 'var(--text-muted)'
                }}
                onClick={() => setMode('auto')}
              >
                <Sparkles size={12} style={{ marginRight: 4 }} />
                Magic Auto-ML
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Experiment Name</label>
            <input
              className="form-input"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="credit_risk_v4_experiment"
              required
            />
          </div>

          {mode === 'manual' ? (
            <>
              <div className="form-group">
                <label className="form-label">Task Type</label>
                <div style={{ position: 'relative' }}>
                  <select
                    className="form-input"
                    value={taskType}
                    onChange={e => setTaskType(e.target.value as typeof taskType)}
                    style={{ appearance: 'none', paddingRight: 'var(--sp-8)' }}
                  >
                    <option value="binary_classification">Binary Classification</option>
                    <option value="multiclass_classification">Multiclass Classification</option>
                    <option value="regression">Regression</option>
                  </select>
                  <ChevronDown size={14} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Algorithms to Compare</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-2)', marginTop: 'var(--sp-2)' }}>
                  {AVAILABLE_ALGOS.map(algo => (
                    <button
                      key={algo}
                      type="button"
                      onClick={() => toggleAlgo(algo)}
                      className={`badge ${selectedAlgos.includes(algo) ? 'badge-info' : ''}`}
                      style={{
                        cursor: 'pointer',
                        padding: 'var(--sp-1) var(--sp-3)',
                        border: `1px solid ${selectedAlgos.includes(algo) ? 'var(--info)' : 'var(--border-subtle)'}`,
                        borderRadius: 'var(--radius-pill)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 'var(--fs-2xs)',
                        background: selectedAlgos.includes(algo) ? 'color-mix(in srgb, var(--info) 15%, transparent)' : 'transparent',
                        color: selectedAlgos.includes(algo) ? 'var(--info)' : 'var(--text-muted)',
                        transition: 'all var(--dur-fast) var(--ease-out)',
                      }}
                    >
                      {algo}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Cross-Validation Folds: {cvFolds}</label>
                <input
                  type="range" min={2} max={10} value={cvFolds}
                  onChange={e => setCvFolds(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent)' }}
                />
              </div>
            </>
          ) : (
            <div style={{ padding: 'var(--sp-5)', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-lg)', border: '1px dashed var(--border-subtle)', textAlign: 'center' }}>
              <Wand2 size={32} strokeWidth={1} style={{ color: 'var(--accent)', marginBottom: 'var(--sp-3)', opacity: 0.6 }} />
              <h4 style={{ margin: 0, fontSize: 'var(--fs-sm)', color: 'var(--text-primary)' }}>Agentic Intelligence Active</h4>
              <p style={{ fontSize: 'var(--fs-2xs)', color: 'var(--text-muted)', marginTop: 'var(--sp-2)', lineHeight: 1.5 }}>
                The <strong>AutoML Agent</strong> will profile your dataset, detect the task type, 
                and select the optimal algorithm and hyperparameters autonomously.
              </p>
              <div style={{ marginTop: 'var(--sp-4)', padding: 'var(--sp-2)', background: 'rgba(168, 85, 247, 0.1)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(168, 85, 247, 0.2)' }}>
                <span style={{ fontSize: '10px', color: '#a855f7', fontWeight: 'var(--fw-bold)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Optimization Goal: Maximize F1-Score
                </span>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 'var(--sp-3)', justifyContent: 'flex-end', paddingTop: 'var(--sp-2)' }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={mode === 'auto' ? { background: 'linear-gradient(135deg, var(--accent) 0%, #a855f7 100%)', border: 'none' } : {}}
            >
              {loading ? (
                <><RefreshCw size={14} className="spin" /> {mode === 'auto' ? 'Agent Thinking…' : 'Launching…'}</>
              ) : (
                <>
                  {mode === 'auto' ? <Sparkles size={14} /> : <FlaskConical size={14} />}
                  {mode === 'auto' ? 'Launch Magic AutoML' : 'Launch Experiment'}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export function MLPipeline() {
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedExperiment, setSelectedExperiment] = useState<Experiment | null>(null);

  const loadData = useCallback(async (showRefreshIndicator = false) => {
    if (showRefreshIndicator) setRefreshing(true);
    try {
      const [modelsRes, expsRes] = await Promise.all([
        fetchApi('/ml/models'),
        fetchApi('/ml/experiments'),
      ]);
      setModels((modelsRes as { models: ModelEntry[] }).models);
      setExperiments((expsRes as { experiments: Experiment[] }).experiments);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load ML data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    const running = experiments.some(e => e.status === 'queued' || e.status === 'running');
    if (!running) return;
    const t = setInterval(() => loadData(), 5000);
    return () => clearInterval(t);
  }, [experiments, loadData]);

  const handleExperimentCreated = (exp: Experiment) => {
    setShowModal(false);
    setExperiments(prev => [exp, ...prev]);
    setTimeout(() => loadData(), 2000);
  };

  const deployed = models.filter(m => m.status === 'deployed').length;
  const driftAlerts = models.filter(m => m.drift !== 'none').length;
  const bestF1 = models.length > 0 ? Math.max(...models.map(m => m.metrics.f1 ?? 0)) : 0;

  if (loading) {
    return (
      <div className="animate-in" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 320 }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="spin" style={{ marginBottom: 'var(--sp-3)' }} />
          <p>Loading ML pipeline…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in">
      {showModal && (
        <ExperimentModal onClose={() => setShowModal(false)} onSubmit={handleExperimentCreated} />
      )}
      
      {selectedExperiment && (
        <ExperimentDetailModal 
          experiment={{
            id: selectedExperiment.experiment_id,
            name: selectedExperiment.experiment_name,
            status: selectedExperiment.status,
            task_type: selectedExperiment.task_type || 'binary_classification',
            algorithms: selectedExperiment.algorithms,
            target_column: 'target',
            results: selectedExperiment.results?.metrics || (Array.isArray(selectedExperiment.results) ? selectedExperiment.results[0]?.metrics : {}),
            reasoning: selectedExperiment.reasoning,
            trace: selectedExperiment.trace,
            created_at: selectedExperiment.created_at
          }} 
          onClose={() => setSelectedExperiment(null)} 
        />
      )}

      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>ML Pipeline Studio</h2>
          <p>Train, compare, deploy, and monitor ML models</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
          <button
            className="btn btn-ghost"
            onClick={() => loadData(true)}
            disabled={refreshing}
            title="Refresh"
          >
            <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
          </button>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            <FlaskConical size={16} strokeWidth={1.8} />
            New Experiment
          </button>
        </div>
      </div>

      {error && (
        <div style={{ marginBottom: 'var(--sp-4)', padding: 'var(--sp-3) var(--sp-4)', background: 'var(--danger-muted)', borderRadius: 'var(--radius-md)', color: 'var(--danger)', fontSize: 'var(--fs-sm)' }}>
          ⚠ {error} — <button className="btn btn-ghost" style={{ fontSize: 'inherit', color: 'inherit', padding: 0, textDecoration: 'underline' }} onClick={() => loadData()}>retry</button>
        </div>
      )}

      <div className="bento-grid" style={{ marginBottom: 'var(--sp-6)' }}>
        {[
          { label: 'Registered Models', value: models.length },
          { label: 'Deployed', value: deployed },
          { label: 'Best F1 Score', value: bestF1 > 0 ? bestF1.toFixed(3) : '—', highlight: true },
          { label: 'Drift Alerts', value: driftAlerts },
        ].map((m, i) => (
          <div
            key={m.label}
            className="glass-card metric-card stagger-item"
            style={{ gridColumn: 'span 3', animationDelay: `${i * 60}ms` }}
          >
            <div className="metric-label">{m.label}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--sp-2)' }}>
              <div className="metric-value">{m.value}</div>
              {m.highlight && bestF1 > 0 && <TrendingUp size={14} style={{ color: 'var(--success)', opacity: 0.6 }} />}
            </div>
          </div>
        ))}
      </div>

      <div className="glass-card stagger-item" style={{ padding: 'var(--sp-5)', animationDelay: '280ms', marginBottom: 'var(--sp-5)' }}>
        <h3 className="section-title">Model Registry</h3>
        {models.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 'var(--sp-8) 0' }}>
            <FlaskConical size={32} strokeWidth={1.2} style={{ opacity: 0.3, marginBottom: 'var(--sp-3)' }} />
            <p style={{ fontSize: 'var(--fs-sm)' }}>No models registered yet.</p>
            <p style={{ fontSize: 'var(--fs-2xs)', marginTop: 'var(--sp-1)' }}>Launch an experiment to train and register your first model.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr><th>Model</th><th>Algorithm</th><th>Status</th><th style={{ minWidth: 140 }}>F1 Score</th><th style={{ minWidth: 140 }}>ROC AUC</th><th>Drift</th><th>Trained</th></tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.model_id}>
                  <td style={{ color: 'var(--text-primary)', fontWeight: 'var(--fw-medium)', fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-2xs)' }}>{m.name}</td>
                  <td>{m.algorithm}</td>
                  <td><span className={`badge ${STATUS_CLS[m.status]}`}>{m.status}</span></td>
                  <td>{m.metrics.f1 != null ? <MiniBar value={m.metrics.f1} /> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
                  <td>{m.metrics.auc != null ? <MiniBar value={m.metrics.auc} /> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
                  <td>
                    <span className={`badge ${DRIFT_CLS[m.drift ?? 'none']}`}>
                      {m.drift === 'moderate' && <span className="ambient-dot warning" style={{ width: 5, height: 5, display: 'inline-block' }} />}
                      {m.drift ?? 'none'}
                    </span>
                  </td>
                  <td style={{ fontSize: 'var(--fs-2xs)', color: 'var(--text-muted)' }}>{m.trained_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {experiments.length > 0 && (
        <div className="glass-card stagger-item" style={{ padding: 'var(--sp-5)', animationDelay: '360ms' }}>
          <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
              <FlaskConical size={16} strokeWidth={1.8} /> Experiments
            </div>
          </h3>
          <table className="data-table">
            <thead>
              <tr><th>ID</th><th style={{ minWidth: 280 }}>Experiment</th><th>Algorithms</th><th>Status</th><th>Started</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {experiments.map(exp => (
                <tr key={exp.experiment_id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-3xs)', color: 'var(--text-muted)' }}>{exp.experiment_id.slice(0, 8)}…</td>
                  <td>
                    <div style={{ fontWeight: 'var(--fw-medium)', color: 'var(--text-primary)' }}>{exp.experiment_name}</div>
                    {exp.reasoning && (
                      <div style={{ marginTop: 'var(--sp-2)', padding: 'var(--sp-2)', background: 'rgba(168, 85, 247, 0.05)', border: '1px solid rgba(168, 85, 247, 0.1)', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)' }}><Sparkles size={8} style={{ color: '#a855f7' }} /><span style={{ fontSize: '9px', color: '#a855f7', fontWeight: 'var(--fw-bold)', textTransform: 'uppercase' }}>Agent Reason</span></div>
                        <p style={{ margin: 0, fontSize: '10px', color: 'var(--text-muted)', fontStyle: 'italic', lineHeight: 1.3 }}>{exp.reasoning}</p>
                      </div>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 'var(--sp-1)', flexWrap: 'wrap' }}>
                      {exp.algorithms.map(a => <span key={a} className="badge badge-info" style={{ fontSize: '9px', padding: '2px 6px' }}>{a}</span>)}
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${EXP_STATUS_CLS[exp.status]}`}>
                      {(exp.status === 'queued' || exp.status === 'running') && (
                        <RefreshCw size={10} className="spin" style={{ marginRight: 4 }} />
                      )}
                      {exp.status}
                    </span>
                  </td>
                  <td style={{ fontSize: 'var(--fs-2xs)', color: 'var(--text-muted)' }}>
                    {exp.created_at ? new Date(exp.created_at).toLocaleTimeString() : '—'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <button 
                      className="btn btn-ghost btn-sm"
                      onClick={() => setSelectedExperiment(exp)}
                      title="View Details"
                    >
                      <Eye size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
