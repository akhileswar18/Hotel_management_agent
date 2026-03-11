
import React from 'react';
import { Package, AlertTriangle, TrendingDown } from 'lucide-react';
import { InventoryItem } from '../types';

interface InventoryStatusProps {
  inventory: InventoryItem[];
}

export const InventoryStatus: React.FC<InventoryStatusProps> = ({ inventory }) => {
  return (
    <div className="glass-panel p-4 rounded-2xl h-full border border-zinc-800">
      <h2 className="text-lg font-bold flex items-center gap-2 mb-4">
        <Package className="text-blue-400" size={20} />
        Inventory Brain
      </h2>

      <div className="space-y-4">
        {inventory.map(item => {
          const isLow = item.quantity <= item.minThreshold;
          const percentage = Math.min(100, (item.quantity / (item.minThreshold * 2)) * 100);

          return (
            <div key={item.id} className="group">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-zinc-300 font-medium flex items-center gap-1">
                  {item.name}
                  {isLow && <AlertTriangle size={12} className="text-amber-500 animate-pulse" />}
                </span>
                <span className={`${isLow ? 'text-amber-500' : 'text-zinc-500'}`}>
                  {item.quantity} {item.unit}
                </span>
              </div>
              <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-500 ${
                    isLow ? 'bg-amber-500' : 'bg-emerald-500'
                  }`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
              {isLow && (
                <div className="mt-1 text-[10px] text-amber-500 flex items-center gap-1">
                  <TrendingDown size={10} />
                  Restock recommended soon
                </div>
              )}
            </div>
          );
        })}
      </div>

      <button className="w-full mt-6 py-2 border border-zinc-700 hover:bg-zinc-800 text-zinc-400 text-xs rounded-lg transition-all">
        View Full Ledger
      </button>
    </div>
  );
};
