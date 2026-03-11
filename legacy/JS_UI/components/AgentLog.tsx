
import React from 'react';
import { Terminal, Cpu } from 'lucide-react';
import { AgentAction } from '../types';

interface AgentLogProps {
  logs: AgentAction[];
}

export const AgentLog: React.FC<AgentLogProps> = ({ logs }) => {
  return (
    <div className="glass-panel p-4 rounded-2xl h-full border border-zinc-800 flex flex-col">
      <h2 className="text-sm font-bold flex items-center gap-2 mb-3 text-zinc-500 uppercase tracking-widest">
        <Terminal size={14} />
        System Coordination
      </h2>
      
      <div className="flex-1 overflow-y-auto font-mono text-[11px] space-y-2 pr-2 custom-scrollbar">
        {logs.map((log) => (
          <div key={log.id} className="border-l-2 border-zinc-800 pl-3 py-1 animate-in fade-in slide-in-from-left-2">
            <div className="flex items-center gap-2 text-zinc-500 mb-0.5">
              <span className={`px-1 rounded ${
                log.agent === 'ORCHESTRATOR' ? 'bg-purple-900/40 text-purple-400' :
                log.agent === 'KITCHEN' ? 'bg-orange-900/40 text-orange-400' :
                log.agent === 'INVENTORY' ? 'bg-blue-900/40 text-blue-400' :
                'bg-emerald-900/40 text-emerald-400'
              }`}>
                {log.agent}
              </span>
              <span>{new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
            </div>
            <p className="text-zinc-300">{log.message}</p>
          </div>
        ))}
      </div>
      
      <div className="mt-3 pt-3 border-t border-zinc-800 flex items-center justify-between text-[10px] text-zinc-600">
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Agents Connected
        </div>
        <span>Local Core 2.0.4</span>
      </div>
    </div>
  );
};
