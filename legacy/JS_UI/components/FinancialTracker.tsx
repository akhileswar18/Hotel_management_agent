
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { DollarSign, ArrowUpRight } from 'lucide-react';
import { FinancialLog } from '../types';

interface FinancialTrackerProps {
  logs: FinancialLog[];
}

export const FinancialTracker: React.FC<FinancialTrackerProps> = ({ logs }) => {
  const totalRevenue = logs
    .filter(l => l.type === 'INCOME')
    .reduce((acc, curr) => acc + curr.amount, 0);

  // Group by hour for the chart
  const hourlyData = Array.from({ length: 8 }, (_, i) => {
    const hour = new Date().getHours() - (7 - i);
    const amount = logs
      .filter(l => new Date(l.timestamp).getHours() === hour && l.type === 'INCOME')
      .reduce((acc, curr) => acc + curr.amount, 0);
    return { hour: `${hour}:00`, amount };
  });

  return (
    <div className="glass-panel p-4 rounded-2xl border border-zinc-800">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-zinc-500 text-xs font-bold uppercase tracking-widest mb-1 flex items-center gap-1">
            <DollarSign size={14} />
            Revenue Stream
          </h2>
          <div className="text-3xl font-bold text-white flex items-baseline gap-1">
            <span className="text-emerald-500 text-xl">$</span>
            {totalRevenue.toFixed(2)}
          </div>
        </div>
        <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-500">
          <ArrowUpRight size={20} />
        </div>
      </div>

      <div className="h-32 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={hourlyData}>
            <Tooltip
              contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
              itemStyle={{ color: '#10b981' }}
              cursor={{ fill: 'rgba(255,255,255,0.05)' }}
            />
            <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
              {hourlyData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={index === hourlyData.length - 1 ? '#10b981' : '#3f3f46'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      
      <div className="mt-4 flex justify-between text-[10px] text-zinc-500">
        <span>8h performance</span>
        <span className="text-emerald-400">+12% vs yesterday</span>
      </div>
    </div>
  );
};
