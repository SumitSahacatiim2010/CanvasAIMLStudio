import React from 'react';
import { CheckCircle, Clock, Zap, Info, Terminal, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface TraceStep {
  node: string;
  action: string;
  duration_ms: number;
  details: any;
}

interface AgentTraceViewerProps {
  trace: TraceStep[];
}

export const AgentTraceViewer: React.FC<AgentTraceViewerProps> = ({ trace }) => {
  if (!trace || trace.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-surface-dark/30 rounded-2xl border border-dashed border-white/10">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center"
        >
          <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
            <Info className="w-8 h-8 text-white/20" />
          </div>
          <p className="text-white/40 font-medium">Listening for agent signals...</p>
          <p className="text-white/20 text-xs mt-1">No execution trace data available yet.</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-white/60 uppercase tracking-[0.2em] flex items-center gap-2">
          <Terminal className="w-4 h-4 text-primary" />
          Execution Trace
        </h4>
        <div className="flex items-center gap-2 text-[10px] text-white/30 font-mono">
          <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
          LIVE STREAM
        </div>
      </div>
      
      <div className="relative">
        {/* Connection Line */}
        <div className="absolute left-[19px] top-4 bottom-4 w-px bg-gradient-to-b from-primary/50 via-secondary/30 to-transparent" />
        
        <div className="space-y-6">
          <AnimatePresence mode="popLayout">
            {trace.map((step, idx) => (
              <motion.div 
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1, type: "spring", stiffness: 100 }}
                className="relative pl-12 group"
              >
                {/* Node Icon */}
                <motion.div 
                  whileHover={{ scale: 1.1 }}
                  className="absolute left-0 top-0 w-10 h-10 rounded-full bg-surface-light border border-white/10 flex items-center justify-center z-10 group-hover:border-primary/50 transition-colors shadow-xl"
                >
                  {step.node.includes('planner') ? (
                    <Zap className="w-5 h-5 text-primary" />
                  ) : step.node.includes('validator') ? (
                    <Info className="w-5 h-5 text-warning" />
                  ) : (
                    <CheckCircle className="w-5 h-5 text-secondary" />
                  )}
                </motion.div>
                
                {/* Content */}
                <div className="bg-surface-light/40 backdrop-blur-md border border-white/5 rounded-2xl p-5 group-hover:border-white/10 transition-all shadow-lg hover:shadow-primary/5">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h5 className="text-white font-semibold text-sm capitalize flex items-center gap-2">
                        {step.node.replace('_', ' ')}
                        <ChevronRight className="w-3 h-3 text-white/20" />
                      </h5>
                      <p className="text-white/40 text-xs mt-0.5">{step.action}</p>
                    </div>
                    <div className="flex items-center gap-2 px-2.5 py-1.5 bg-black/40 rounded-lg border border-white/5">
                      <Clock className="w-3 h-3 text-primary/60" />
                      <span className="text-white/60 text-[10px] font-mono tracking-tight">
                        {step.duration_ms.toFixed(1)}ms
                      </span>
                    </div>
                  </div>
                  
                  {/* Terminal Detail View */}
                  <div className="bg-black/60 rounded-xl border border-white/5 p-4 overflow-hidden">
                    <div className="flex items-center gap-1.5 mb-2 opacity-30">
                      <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                      <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                    </div>
                    <pre className="text-[11px] text-primary/80 font-mono overflow-x-auto leading-relaxed custom-scrollbar max-h-40">
                      {JSON.stringify(step.details, null, 2)}
                    </pre>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
