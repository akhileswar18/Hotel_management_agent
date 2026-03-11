
import React from 'react';
import { Settings, Volume2, Languages, Zap, BrainCircuit } from 'lucide-react';
import { AgentSettings } from '../types';

interface AgentSettingsPanelProps {
  settings: AgentSettings;
  onUpdate: (settings: AgentSettings) => void;
}

export const AgentSettingsPanel: React.FC<AgentSettingsPanelProps> = ({ settings, onUpdate }) => {
  return (
    <div className="glass-panel p-8 rounded-3xl border border-zinc-800">
      <div className="flex items-center gap-3 mb-8">
        <div className="p-3 bg-zinc-800 rounded-2xl text-purple-400"><Settings size={24} /></div>
        <div>
          <h2 className="text-2xl font-black">Agent Brain Configuration</h2>
          <p className="text-zinc-500 text-sm">Fine-tune behavioral and operational parameters of your local agents</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        <div className="space-y-4">
          <label className="text-xs font-black text-zinc-500 uppercase flex items-center gap-2">
            <Volume2 size={14} /> Agent Voice
          </label>
          <select 
            value={settings.voiceName}
            onChange={e => onUpdate({ ...settings, voiceName: e.target.value as any })}
            className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-3 px-4 text-sm font-bold focus:ring-1 focus:ring-purple-500 outline-none"
          >
            <option value="Puck">Puck (Cheerful)</option>
            <option value="Charon">Charon (Professional)</option>
            <option value="Kore">Kore (Calm)</option>
            <option value="Fenrir">Fenrir (Authoritative)</option>
            <option value="Zephyr">Zephyr (Fast)</option>
          </select>
        </div>

        <div className="space-y-4">
          <label className="text-xs font-black text-zinc-500 uppercase flex items-center gap-2">
            <Languages size={14} /> Primary Language
          </label>
          <select 
            value={settings.language}
            onChange={e => onUpdate({ ...settings, language: e.target.value as any })}
            className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-3 px-4 text-sm font-bold focus:ring-1 focus:ring-purple-500 outline-none"
          >
            <option value="English">English</option>
            <option value="Telugu">Telugu (తెలుగు)</option>
            <option value="Hindi">Hindi (हिन्दी)</option>
          </select>
        </div>

        <div className="space-y-4">
          <label className="text-xs font-black text-zinc-500 uppercase flex items-center gap-2">
            <BrainCircuit size={14} /> Thinking Budget
          </label>
          <input 
            type="range"
            min="0"
            max="24000"
            step="1000"
            value={settings.thinkingBudget}
            onChange={e => onUpdate({ ...settings, thinkingBudget: parseInt(e.target.value) })}
            className="w-full accent-purple-500"
          />
          <div className="text-[10px] text-zinc-500 flex justify-between">
            <span>Fast Responses</span>
            <span className="text-purple-400 font-black">{settings.thinkingBudget} Tokens</span>
            <span>Deep Reasoning</span>
          </div>
        </div>

        <div className="flex flex-col justify-end">
           <button 
             onClick={() => onUpdate({ ...settings, autoInventoryDeduction: !settings.autoInventoryDeduction })}
             className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-3 transition-all border ${
               settings.autoInventoryDeduction 
                 ? 'bg-emerald-600/10 border-emerald-500/30 text-emerald-400' 
                 : 'bg-zinc-900 border-zinc-800 text-zinc-500'
             }`}
           >
             <Zap size={18} />
             {settings.autoInventoryDeduction ? 'AUTO-INVENTORY ON' : 'AUTO-INVENTORY OFF'}
           </button>
        </div>
      </div>
    </div>
  );
};
