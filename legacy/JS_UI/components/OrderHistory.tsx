
import React, { useState } from 'react';
import { 
  History, 
  Search, 
  Filter, 
  Download, 
  ExternalLink, 
  CheckCircle2, 
  Clock, 
  XCircle,
  TrendingUp,
  Calendar
} from 'lucide-react';
import { Order, OrderStatus } from '../types';

interface OrderHistoryProps {
  orders: Order[];
}

export const OrderHistory: React.FC<OrderHistoryProps> = ({ orders }) => {
  const [filter, setFilter] = useState<OrderStatus | 'ALL'>('ALL');
  const [search, setSearch] = useState('');

  const filteredOrders = orders.filter(o => {
    const matchesFilter = filter === 'ALL' || o.status === filter;
    const matchesSearch = o.id.toLowerCase().includes(search.toLowerCase()) || 
                         o.tableNumber.toString().toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getStatusStyle = (status: OrderStatus) => {
    switch (status) {
      case OrderStatus.SERVED: return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
      case OrderStatus.READY: return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case OrderStatus.PREPARING: return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case OrderStatus.PENDING: return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20';
      case OrderStatus.CANCELLED: return 'bg-red-500/10 text-red-500 border-red-500/20';
      default: return 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black flex items-center gap-3">
            <History className="text-emerald-500" size={32} />
            Order Ledger
          </h1>
          <p className="text-zinc-500 text-sm mt-1">Audit-ready historical logs for all branch operations</p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-xl text-xs font-bold hover:bg-zinc-800 transition-all">
            <Download size={14} /> EXPORT CSV
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold hover:bg-emerald-500 transition-all">
            <TrendingUp size={14} /> DAILY REPORT
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <div className="glass-panel p-6 rounded-3xl border border-zinc-800">
            <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-4 flex items-center gap-2">
              <Filter size={14} /> Quick Filter
            </h3>
            <div className="space-y-2">
              {(['ALL', ...Object.values(OrderStatus)] as const).map(s => (
                <button
                  key={s}
                  onClick={() => setFilter(s as any)}
                  className={`w-full text-left px-4 py-3 rounded-2xl text-sm font-medium transition-all border ${
                    filter === s 
                      ? 'bg-emerald-600/10 border-emerald-500/30 text-emerald-400' 
                      : 'border-transparent text-zinc-500 hover:bg-zinc-800'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          
          <div className="glass-panel p-6 rounded-3xl border border-zinc-800 bg-zinc-900/20">
            <div className="text-xs text-zinc-500 font-bold uppercase mb-4">Quick Stats</div>
            <div className="space-y-4">
              <div>
                <div className="text-2xl font-black">{orders.length}</div>
                <div className="text-[10px] text-zinc-500 font-bold">TOTAL TRANSACTIONS</div>
              </div>
              <div className="pt-4 border-t border-zinc-800">
                <div className="text-2xl font-black text-emerald-500">
                  ${orders.reduce((a, b) => a + b.total, 0).toFixed(2)}
                </div>
                <div className="text-[10px] text-zinc-500 font-bold">GROSS REVENUE</div>
              </div>
            </div>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-9 space-y-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" size={18} />
            <input
              placeholder="Search by Order ID or Table Number..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl py-4 pl-12 pr-4 focus:ring-1 focus:ring-emerald-500 outline-none shadow-xl"
            />
          </div>

          <div className="glass-panel rounded-3xl border border-zinc-800 overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-zinc-900/50 border-b border-zinc-800 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
                <tr>
                  <th className="px-6 py-4">ID</th>
                  <th className="px-6 py-4">Table</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Items</th>
                  <th className="px-6 py-4">Time</th>
                  <th className="px-6 py-4 text-right">Total</th>
                  <th className="px-6 py-4 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {filteredOrders.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-20 text-center text-zinc-600 italic">No orders found matching the criteria</td>
                  </tr>
                ) : (
                  filteredOrders.map(order => (
                    <tr key={order.id} className="hover:bg-zinc-800/30 transition-colors group">
                      <td className="px-6 py-4 font-mono text-xs text-zinc-400 group-hover:text-emerald-500 transition-colors">#{order.id}</td>
                      <td className="px-6 py-4">
                        <span className="font-bold">{order.tableNumber}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-lg text-[10px] font-black border uppercase ${getStatusStyle(order.status)}`}>
                          {order.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-xs text-zinc-400 truncate w-32">
                          {order.items.map(i => `${i.quantity}x ${i.name}`).join(', ')}
                        </div>
                      </td>
                      <td className="px-6 py-4 flex items-center gap-2 text-xs text-zinc-500">
                        <Calendar size={12} />
                        {new Date(order.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-6 py-4 text-right font-black text-white">
                        ${order.total.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <button className="p-2 text-zinc-500 hover:text-white transition-colors">
                          <ExternalLink size={16} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
