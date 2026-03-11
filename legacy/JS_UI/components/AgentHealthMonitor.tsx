
import React, { useMemo } from 'react';
import { Heart, Activity, Cpu, Wifi, ShieldAlert } from 'lucide-react';
import { AgentHealthStatus } from '../types';

interface AgentHealthMonitorProps {
  expanded?: boolean;
}

export const AgentHealthMonitor: React.FC<AgentHealthMonitorProps> = ({ expanded = false }) => {
  const healthData: AgentHealthStatus[] = useMemo(() => [
    { name: 'Multimodal Core', status: 'ONLINE', latency: 42, lastActive: Date.now() },
    { name: 'Voice Processor', status: 'ONLINE', latency: 128, lastActive: Date.now() - 5000 },
    { name: 'Kitchen Orchestrator', status: 'ONLINE', latency: 310, lastActive: Date.now() - 12000 },
    { name: 'Supply Optimizer', status: 'BUSY', latency: 2400, lastActive: Date.now() - 1000 },
  ], []);

  return (
    <div className={`glass-panel p-6 rounded-3xl border border-zinc-800 ${expanded ? 'shadow-2xl' : 'h-fit'}`}>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-black flex items-center gap-2">
          <Heart size={20} className="text-red-500 animate-pulse" />
          Neural Health
        </h2>
        {!expanded && (
          <div className="px-2 py-0.5 bg-emerald-500/10 rounded-full border border-emerald-500/20 text-[10px] text-emerald-500 font-black">
            STABLE
          </div>
        )}
      </div>

      <div className={`space-y-4 ${expanded ? 'grid grid-cols-1 md:grid-cols-2 gap-6' : ''}`}>
        {healthData.map(agent => (
          <div key={agent.name} className="p-4 bg-zinc-900/40 rounded-2xl border border-zinc-800/50">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-bold text-zinc-400 flex items-center gap-2">
                <Cpu size={12} />
                {agent.name}
              </span>
              <span className={`text-[10px] font-black px-2 py-0.5 rounded ${
                agent.status === 'ONLINE' ? 'bg-emerald-500/10 text-emerald-500' : 
                agent.status === 'BUSY' ? 'bg-amber-500/10 text-amber-500' : 'bg-red-500/10 text-red-500'
              }`}>
                {agent.status}
              </span>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex-1 space-y-1">
                <div className="flex justify-between text-[10px] text-zinc-500">
                  <span>Latency</span>
                  <span className={agent.latency > 1000 ? 'text-amber-500' : 'text-zinc-300'}>{agent.latency}ms</span>
                </div>
                <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                   <div 
                     className={`h-full transition-all duration-700 ${agent.latency > 1000 ? 'bg-amber-500' : 'bg-emerald-500'}`} 
                     style={{ width: `${Math.max(10, Math.min(100, 100 - (agent.latency / 30)))}%` }}
                   />
                </div>
              </div>
              <Activity size={24} className={agent.status === 'ONLINE' ? 'text-emerald-500/40' : 'text-amber-500/40'} />
            </div>
          </div>
        ))}
      </div>

      {expanded && (
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-zinc-900/50 rounded-3xl border border-zinc-800 flex flex-col items-center justify-center text-center">
            <Wifi className="text-emerald-500 mb-2" size={32} />
            <div className="text-xl font-black">99.9%</div>
            <div className="text-[10px] text-zinc-500 font-bold uppercase">Uptime Score</div>
          </div>
          <div className="p-6 bg-zinc-900/50 rounded-3xl border border-zinc-800 flex flex-col items-center justify-center text-center">
            <ShieldAlert className="text-blue-500 mb-2" size={32} />
            <div className="text-xl font-black">2.4ms</div>
            <div className="text-[10px] text-zinc-500 font-bold uppercase">Jitter Variance</div>
          </div>
          <div className="p-6 bg-zinc-900/50 rounded-3xl border border-zinc-800 flex flex-col items-center justify-center text-center">
            <Cpu className="text-purple-500 mb-2" size={32} />
            <div className="text-xl font-black">12%</div>
            <div className="text-[10px] text-zinc-500 font-bold uppercase">Neural Load</div>
          </div>
        </div>
      )}
    </div>
  );
};
