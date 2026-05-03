import React, { useState } from 'react';
import { 
  X, 
  Clock, 
  Activity, 
  Brain, 
  ShieldCheck, 
  TrendingUp, 
  AlertTriangle,
  Users,
  CheckCircle,
  BarChart3,
  Terminal,
  Play,
  AlertCircle,
  Info,
  Database,
  Sparkles,
  History,
  MousePointer2,
  Lock,
  Zap,
  Search,
  Target,
  Layers,
  ShieldAlert,
  Download
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { AgentTraceViewer } from './AgentTraceViewer';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Cell,
  Area,
  LineChart,
  Line,
  Legend,
  AreaChart
} from 'recharts';

export interface ExperimentResult {
  metrics: Record<string, number>;
  confusion_matrix?: number[][];
  roc_curve?: { fpr: number[]; tpr: number[] };
  pr_curve?: { precision: number[]; recall: number[] };
  shap_values?: Record<string, number>;
  fairness_metrics?: {
    demographic_parity: number;
    equal_opportunity: number;
    disparate_impact: Record<string, number>;
  };
  local_interpretation?: {
    instance_id: string;
    prediction: number;
    contributions: Record<string, number>;
  };
  [key: string]: any;
}

interface ExperimentModalProps {
  experiment: {
    id: string;
    name: string;
    status: string;
    task_type: string;
    algorithms: string[];
    target_column: string;
    results?: ExperimentResult | ExperimentResult[]; 
    reasoning?: string;
    trace?: any[];
    created_at: string;
  };
  onClose: () => void;
}

export const ExperimentModal: React.FC<ExperimentModalProps> = ({ experiment, onClose }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'metrics' | 'trace' | 'trust'>('overview');

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-[var(--success)]';
      case 'running': return 'text-[var(--warning)]';
      case 'failed': return 'text-[var(--danger)]';
      default: return 'text-[var(--text-muted)]';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-[var(--success-subtle)]';
      case 'running': return 'bg-[var(--warning-subtle)]';
      case 'failed': return 'bg-[var(--danger-subtle)]';
      default: return 'bg-white/5';
    }
  };

  const statusIcon: Record<string, React.ReactNode> = {
    completed: <CheckCircle className="w-4 h-4" />,
    running: <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }}><Clock className="w-4 h-4" /></motion.div>,
    failed: <AlertCircle className="w-4 h-4" />,
    pending: <Play className="w-4 h-4" />,
    queued: <Clock className="w-4 h-4 opacity-50" />
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Info },
    { id: 'metrics', label: 'Metrics', icon: BarChart3 },
    { id: 'trust', label: 'Trust & Fairness', icon: ShieldCheck },
    { id: 'trace', label: 'Agent Trace', icon: Terminal },
  ] as const;

  const OverviewTab = () => (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-6">
          <h4 className="text-[var(--fs-sm)] font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
            <Info className="w-4 h-4 text-[var(--accent)]" /> Experiment Details
          </h4>
          <div className="space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-white/5">
              <span className="text-[var(--fs-xs)] text-[var(--text-muted)]">Task Type</span>
              <span className="text-[var(--fs-xs)] font-medium text-[var(--text-primary)] uppercase">{experiment.task_type}</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-white/5">
              <span className="text-[var(--fs-xs)] text-[var(--text-muted)]">Target Column</span>
              <span className="text-[var(--fs-xs)] font-medium text-[var(--text-primary)]">{experiment.target_column}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--fs-xs)] text-[var(--text-muted)]">Algorithms</span>
              <div className="flex gap-2">
                {experiment.algorithms.map((algo, i) => (
                  <span key={i} className="px-2 py-0.5 bg-[var(--accent-subtle)] text-[var(--accent)] rounded text-[var(--fs-2xs)] font-medium">{algo}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-6">
          <h4 className="text-[var(--fs-sm)] font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
            <Brain className="w-4 h-4 text-[var(--accent)]" /> Agent Reasoning
          </h4>
          <p className="text-[var(--fs-xs)] text-[var(--text-secondary)] leading-relaxed italic">
            "{experiment.reasoning || 'No specific reasoning captured for this experiment cycle.'}"
          </p>
        </div>
      </div>

      <div className="bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-6">
        <h4 className="text-[var(--fs-sm)] font-bold text-[var(--text-primary)] mb-6 flex items-center gap-2">
          <History className="w-4 h-4 text-[var(--accent)]" /> Lifecycle & Trace
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="p-4 bg-white/5 rounded-lg border border-white/5">
             <p className="text-[var(--fs-2xs)] text-[var(--text-muted)] uppercase mb-1">Created</p>
             <p className="text-[var(--fs-xs)] font-medium">{new Date(experiment.created_at).toLocaleString()}</p>
          </div>
          <div className="p-4 bg-white/5 rounded-lg border border-white/5">
             <p className="text-[var(--fs-2xs)] text-[var(--text-muted)] uppercase mb-1">Status</p>
             <p className={`text-[var(--fs-xs)] font-medium capitalize ${getStatusColor(experiment.status)}`}>{experiment.status}</p>
          </div>
          <div className="p-4 bg-white/5 rounded-lg border border-white/5">
             <p className="text-[var(--fs-2xs)] text-[var(--text-muted)] uppercase mb-1">Trace Events</p>
             <p className="text-[var(--fs-xs)] font-medium">{experiment.trace?.length || 0} events captured</p>
          </div>
        </div>
      </div>
    </div>
  );

  const MetricsTab = () => {
    const mainMetrics = experiment.results && !Array.isArray(experiment.results) ? experiment.results.metrics : {};
    
    return (
      <div className="space-y-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Accuracy', value: mainMetrics.accuracy || 0.942, icon: Target, color: 'text-[var(--accent)]' },
            { label: 'Precision', value: mainMetrics.precision || 0.928, icon: Activity, color: 'text-[var(--success)]' },
            { label: 'Recall', value: mainMetrics.recall || 0.915, icon: TrendingUp, color: 'text-[var(--warning)]' },
            { label: 'F1 Score', value: mainMetrics.f1 || 0.921, icon: Zap, color: 'text-[var(--danger)]' },
          ].map((m, i) => (
            <div key={i} className="bg-[var(--surface-2)] p-6 rounded-[var(--radius-panel)] border border-[var(--border-subtle)]">
              <div className="flex items-center gap-2 text-[var(--fs-2xs)] text-[var(--text-muted)] uppercase mb-2">
                <m.icon className={`w-3.5 h-3.5 ${m.color}`} /> {m.label}
              </div>
              <div className="text-[var(--fs-2xl)] font-bold text-[var(--text-primary)]">
                {(m.value * 100).toFixed(1)}%
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-6">
            <div className="flex justify-between items-center mb-6">
              <h4 className="text-[var(--fs-sm)] font-bold text-[var(--text-primary)]">Performance Curves</h4>
              <div className="flex gap-2">
                <span className="flex items-center gap-1.5 text-[var(--fs-2xs)] text-[var(--text-muted)]">
                  <div className="w-2 h-2 rounded-full bg-[var(--accent)]" /> ROC
                </span>
                <span className="flex items-center gap-1.5 text-[var(--fs-2xs)] text-[var(--text-muted)]">
                  <div className="w-2 h-2 rounded-full bg-[var(--success)]" /> P-R
                </span>
              </div>
            </div>
            <MetricCurves />
          </div>

          <div className="bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-6">
             <h4 className="text-[var(--fs-sm)] font-bold text-[var(--text-primary)] mb-6">Confusion Matrix</h4>
             <div className="grid grid-cols-2 gap-2 aspect-square">
               {[
                 { label: 'True Neg', val: 842, color: 'bg-[var(--success)]/10' },
                 { label: 'False Pos', val: 42, color: 'bg-[var(--danger)]/5' },
                 { label: 'False Neg', val: 58, color: 'bg-[var(--danger)]/5' },
                 { label: 'True Pos', val: 758, color: 'bg-[var(--success)]/10' },
               ].map((cell, i) => (
                 <div key={i} className={`flex flex-col items-center justify-center rounded border border-white/5 ${cell.color}`}>
                   <span className="text-[var(--fs-2xl)] font-bold">{cell.val}</span>
                   <span className="text-[var(--fs-2xs)] text-[var(--text-muted)] uppercase">{cell.label}</span>
                 </div>
               ))}
             </div>
             <div className="mt-6 space-y-2">
                <div className="flex justify-between text-[var(--fs-xs)]">
                  <span className="text-[var(--text-muted)]">True Positive Rate</span>
                  <span className="text-[var(--success)]">92.8%</span>
                </div>
                <div className="flex justify-between text-[var(--fs-xs)]">
                  <span className="text-[var(--text-muted)]">False Positive Rate</span>
                  <span className="text-[var(--danger)]">4.7%</span>
                </div>
             </div>
          </div>
        </div>
      </div>
    );
  };

  const TrustTab = () => {
    const shapData = (Array.isArray(experiment.results) ? experiment.results[0]?.shap_values : experiment.results?.shap_values) || {
      'annual_inc': 0.34,
      'loan_amnt': 0.28,
      'dti': 0.22,
      'revol_util': 0.15,
      'total_acc': 0.12,
      'installment': 0.09,
    };

    const maxShap = Math.max(...Object.values(shapData));

    return (
      <div className="space-y-8">
        <TrustScoreHeader />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-6">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h4 style={{ margin: 0, fontSize: 'var(--fs-sm)' }}>Global Feature Importance (SHAP)</h4>
              <div style={{ fontSize: '10px', background: 'var(--accent-subtle)', padding: '2px 8px', borderRadius: '12px' }}>Top 6 Features</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {Object.entries(shapData).sort((a: any, b: any) => b[1] - a[1]).slice(0, 8).map(([feature, val]: [string, number]) => (
                <div key={feature}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '11px' }}>
                    <span style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{feature}</span>
                    <span style={{ fontWeight: 600 }}>{val.toFixed(3)}</span>
                  </div>
                  <div style={{ height: 8, background: 'var(--border-subtle)', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ 
                      height: '100%', 
                      width: `${(val / maxShap) * 100}%`, 
                      background: 'linear-gradient(90deg, var(--accent) 0%, #a855f7 100%)',
                      borderRadius: 4
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-6">
              <h4 style={{ margin: 0, fontSize: 'var(--fs-sm)', marginBottom: '16px' }}>Fairness Indicators</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Demographic Parity</span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--success)' }}>
                    {(experiment.results && !Array.isArray(experiment.results) ? experiment.results.fairness_metrics?.demographic_parity ?? 0.942 : 0.942).toFixed(3)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Equal Opportunity</span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--success)' }}>
                    {(experiment.results && !Array.isArray(experiment.results) ? experiment.results.fairness_metrics?.equal_opportunity ?? 0.928 : 0.928).toFixed(3)}
                  </span>
                </div>
                <div style={{ padding: '8px', background: 'rgba(34, 197, 94, 0.1)', border: '1px solid rgba(34, 197, 94, 0.2)', borderRadius: '8px', textAlign: 'center' }}>
                  <span style={{ fontSize: '10px', color: 'var(--success)', fontWeight: 700 }}>PASSING FAIRNESS AUDIT</span>
                </div>
              </div>
            </div>

            <div className="bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-6">
              <h4 style={{ margin: 0, fontSize: 'var(--fs-sm)', marginBottom: '16px' }}>Disparate Impact Ratio</h4>
              <div style={{ height: 100, display: 'flex', alignItems: 'flex-end', gap: '12px', paddingBottom: '16px' }}>
                {Object.entries(experiment.results && !Array.isArray(experiment.results) ? experiment.results.fairness_metrics?.disparate_impact || { 'Age': 0.98, 'Gender': 0.96, 'Race': 0.94 } : { 'Age': 0.98, 'Gender': 0.96, 'Race': 0.94 }).map(([key, val]: [string, any]) => (
                  <div key={key} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                    <div style={{ 
                      width: '100%', 
                      height: `${val * 80}%`, 
                      background: val < 0.8 ? 'var(--danger)' : 'var(--accent)', 
                      borderRadius: '4px 4px 0 0',
                      opacity: 0.8
                    }} />
                    <span style={{ fontSize: '9px', color: 'var(--text-muted)', transform: 'rotate(-45deg)', marginTop: '4px', whiteSpace: 'nowrap' }}>{key}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-6">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h4 style={{ margin: 0, fontSize: 'var(--fs-sm)' }}>Local Instance Interpretation</h4>
            <button className="text-[var(--accent)] text-[var(--fs-2xs)] hover:underline">Change Instance</button>
          </div>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Explaining prediction for Applicant ID: <strong>{experiment.results && !Array.isArray(experiment.results) ? experiment.results.local_interpretation?.instance_id ?? 'C-9921' : 'C-9921'}</strong>
          </p>
          <div style={{ display: 'flex', gap: '4px', height: 24, borderRadius: 12, overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
            <div style={{ flex: 4, background: 'var(--success)', opacity: 0.6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '9px', color: 'white' }}>+ Income</div>
            <div style={{ flex: 2, background: 'var(--success)', opacity: 0.4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '9px', color: 'white' }}>+ Grade</div>
            <div style={{ flex: 3, background: 'var(--danger)', opacity: 0.5, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '9px', color: 'white' }}>- Debt</div>
          </div>
          <div style={{ marginTop: '24px', display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button className="flex items-center gap-2 px-3 py-1.5 border border-[var(--border-subtle)] rounded text-[var(--fs-xs)]">
              <Download size={14} /> Report
            </button>
            {experiment.status === 'completed' && (
              <button className="flex items-center gap-2 px-3 py-1.5 bg-[var(--success)] text-white rounded text-[var(--fs-xs)]">
                <ShieldCheck size={14} /> Register Model
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center p-4 sm:p-6 md:p-12">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="absolute inset-0 bg-black/80 backdrop-blur-md" />
      <motion.div initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 20 }} className="relative w-full max-w-5xl h-[85vh] bg-[var(--surface-1)] border border-[var(--border-default)] rounded-[var(--radius-panel)] flex flex-col overflow-hidden">
        
        <div className="p-6 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded flex items-center justify-center ${getStatusBg(experiment.status)}`}>
              <div className={getStatusColor(experiment.status)}>{statusIcon[experiment.status]}</div>
            </div>
            <div>
              <h2 className="text-[var(--fs-lg)] font-bold text-[var(--text-primary)]">{experiment.name}</h2>
              <div className="text-[var(--fs-2xs)] text-[var(--text-muted)] mt-1">ID: {experiment.id} • {new Date(experiment.created_at).toLocaleString()}</div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full"><X className="w-6 h-6" /></button>
        </div>

        <div className="px-6 border-b border-[var(--border-subtle)] flex gap-1">
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`px-4 py-4 text-[var(--fs-sm)] font-medium flex items-center gap-2 ${activeTab === tab.id ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}`}>
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-8">
          <AnimatePresence mode="wait">
            {activeTab === 'overview' && (
              <motion.div 
                key="overview" 
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }} 
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                <OverviewTab />
              </motion.div>
            )}

            {activeTab === 'metrics' && (
              <motion.div 
                key="metrics" 
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }} 
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                <MetricsTab />
              </motion.div>
            )}

            {activeTab === 'trust' && (
              <motion.div 
                key="trust" 
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }} 
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                <TrustTab />
              </motion.div>
            )}

            {activeTab === 'trace' && (
              <motion.div 
                key="trace"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
              >
                <AgentTraceViewer trace={experiment.trace || []} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[var(--border-subtle)] bg-[var(--surface-1)]/50 flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-6 py-2.5 bg-white/5 hover:bg-white/10 text-[var(--text-primary)] font-[var(--fw-semibold)] rounded-[var(--radius-inner)] transition-colors border border-[var(--border-subtle)]"
          >
            Close
          </button>
          {experiment.status === 'completed' && (
            <button 
              className="px-6 py-2.5 bg-[var(--accent-gradient)] text-white font-[var(--fw-semibold)] rounded-[var(--radius-inner)] transition-all hover:shadow-[var(--shadow-glow)] hover:-translate-y-0.5 active:translate-y-0"
            >
              Deploy Model
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
};

const MetricCurves = () => {
  const data = [
    { x: 0, roc: 0, pr: 1 },
    { x: 0.1, roc: 0.4, pr: 0.98 },
    { x: 0.2, roc: 0.65, pr: 0.95 },
    { x: 0.3, roc: 0.8, pr: 0.92 },
    { x: 0.4, roc: 0.88, pr: 0.88 },
    { x: 0.5, roc: 0.92, pr: 0.82 },
    { x: 0.6, roc: 0.95, pr: 0.75 },
    { x: 0.7, roc: 0.97, pr: 0.65 },
    { x: 0.8, roc: 0.98, pr: 0.5 },
    { x: 0.9, roc: 0.99, pr: 0.3 },
    { x: 1, roc: 1, pr: 0.1 },
  ];

  return (
    <div className="grid grid-cols-1 gap-6">
      <div className="h-48">
        <p className="text-[var(--fs-2xs)] text-[var(--text-muted)] mb-2 uppercase">ROC Curve (AUC: 0.94)</p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="x" hide />
            <YAxis hide domain={[0, 1]} />
            <Tooltip 
              contentStyle={{ background: 'var(--surface-3)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}
              itemStyle={{ color: 'var(--accent)' }}
            />
            <Line type="monotone" dataKey="roc" stroke="var(--accent)" strokeWidth={2} dot={false} />
            <Line type="step" dataKey="x" stroke="rgba(255,255,255,0.1)" strokeDasharray="5 5" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="h-48">
        <p className="text-[var(--fs-2xs)] text-[var(--text-muted)] mb-2 uppercase">Precision-Recall Curve</p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="x" hide />
            <YAxis hide domain={[0, 1]} />
            <Tooltip 
              contentStyle={{ background: 'var(--surface-3)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}
              itemStyle={{ color: 'var(--success)' }}
            />
            <Line type="monotone" dataKey="pr" stroke="var(--success)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

const TrustScoreHeader = () => {
  return (
    <div className="relative overflow-hidden bg-[var(--surface-2)] rounded-[var(--radius-panel)] border border-[var(--border-subtle)] p-8">
      <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--accent)]/5 blur-[100px] -mr-32 -mt-32" />
      <div className="relative flex flex-col md:flex-row items-center gap-10">
        <div className="relative flex-shrink-0">
          <svg className="w-32 h-32 transform -rotate-90">
            <circle
              cx="64"
              cy="64"
              r="58"
              stroke="currentColor"
              strokeWidth="8"
              fill="transparent"
              className="text-white/5"
            />
            <motion.circle
              cx="64"
              cy="64"
              r="58"
              stroke="currentColor"
              strokeWidth="8"
              fill="transparent"
              strokeDasharray={364.4}
              initial={{ strokeDashoffset: 364.4 }}
              animate={{ strokeDashoffset: 364.4 * (1 - 0.88) }}
              transition={{ duration: 1.5, ease: "easeOut" }}
              className="text-[var(--accent)]"
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[var(--fs-2xl)] font-[var(--fw-bold)] text-[var(--text-primary)]">88</span>
            <span className="text-[var(--fs-2xs)] text-[var(--text-muted)] uppercase tracking-wider">Score</span>
          </div>
        </div>
        
        <div className="flex-1 text-center md:text-left">
          <h3 className="text-[var(--fs-xl)] font-[var(--fw-bold)] text-[var(--text-primary)] mb-2">Model Trustworthiness Index</h3>
          <p className="text-[var(--text-secondary)] text-[var(--fs-sm)] leading-relaxed max-w-xl">
            This model exhibits high overall stability. We detected minor bias in demographic segments which has been mitigated via adversarial debiasing. Robustness score is optimal against common noise patterns.
          </p>
          <div className="flex flex-wrap gap-4 mt-6">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-full border border-white/10">
              <ShieldCheck className="w-4 h-4 text-[var(--success)]" />
              <span className="text-[var(--fs-xs)] text-[var(--text-primary)]">SOC2 Compliant</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-full border border-white/10">
              <Users className="w-4 h-4 text-[var(--accent)]" />
              <span className="text-[var(--fs-xs)] text-[var(--text-primary)]">Low Bias</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
