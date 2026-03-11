
import React, { useState, useMemo } from 'react';
import { ChefHat, Clock, Boxes, Package, Plus, CheckCircle2, AlertTriangle, ListChecks } from 'lucide-react';
import { Order, OrderStatus, InventoryItem, MenuItem } from '../types';

interface KitchenDisplayProps {
  orders: Order[];
  inventory: InventoryItem[];
  menuItems: MenuItem[];
  onUpdateStatus: (id: string, status: OrderStatus) => void;
  onAddInventory?: (id: string, amount: number) => void;
  expanded?: boolean;
}

export const KitchenDisplay: React.FC<KitchenDisplayProps> = ({ 
  orders, 
  inventory, 
  menuItems, 
  onUpdateStatus, 
  onAddInventory,
  expanded = false 
}) => {
  const [activeTab, setActiveTab] = useState<'orders' | 'supply'>('orders');
  const [addAmount, setAddAmount] = useState<Record<string, number>>({});

  const activeOrders = orders.filter(o => o.status !== OrderStatus.SERVED && o.status !== OrderStatus.CANCELLED);

  const itemsPossibleToMake = useMemo(() => {
    return menuItems.filter(item => {
      if (!item.ingredients || item.ingredients.length === 0) return true;
      return item.ingredients.every(ing => {
        const invItem = inventory.find(i => i.id === ing.inventoryItemId);
        return invItem && invItem.quantity >= ing.amount;
      });
    });
  }, [menuItems, inventory]);

  const handleAdd = (id: string) => {
    const amt = addAmount[id] || 0;
    if (amt > 0 && onAddInventory) {
      onAddInventory(id, amt);
      setAddAmount(prev => ({ ...prev, [id]: 0 }));
    }
  };

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex bg-zinc-900/50 p-1 rounded-xl border border-zinc-800">
        <button 
          onClick={() => setActiveTab('orders')}
          className={`flex-1 py-2 px-4 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 ${activeTab === 'orders' ? 'bg-orange-500 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'}`}
        >
          <ChefHat size={14} /> Orders
        </button>
        <button 
          onClick={() => setActiveTab('supply')}
          className={`flex-1 py-2 px-4 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 ${activeTab === 'supply' ? 'bg-blue-600 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'}`}
        >
          <Boxes size={14} /> Supply Ledger
        </button>
      </div>

      {activeTab === 'orders' ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4">
            {activeOrders.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 border-2 border-dashed border-zinc-800 rounded-xl text-zinc-500">
                <ChefHat size={40} className="mb-2 opacity-20" />
                <p className="text-sm">No pending orders</p>
              </div>
            ) : (
              activeOrders.map(order => (
                <div key={order.id} className="glass-panel p-4 rounded-xl relative border border-zinc-800">
                  <div className={`absolute left-0 top-0 bottom-0 w-1 ${order.status === OrderStatus.PENDING ? 'bg-zinc-700' : 'bg-orange-500'}`} />
                  <div className="flex justify-between mb-2">
                    <span className="font-bold text-sm">Table {order.tableNumber}</span>
                    <span className="text-[10px] text-zinc-500">{new Date(order.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <ul className="text-xs space-y-1 mb-4">
                    {order.items.map((it, i) => (
                      <li key={i} className="flex justify-between">
                        <span className="text-zinc-300">{it.quantity}x {it.name}</span>
                      </li>
                    ))}
                  </ul>
                  <button 
                    onClick={() => onUpdateStatus(order.id, order.status === OrderStatus.PENDING ? OrderStatus.PREPARING : OrderStatus.READY)}
                    className={`w-full py-2 text-[10px] font-black uppercase rounded-lg transition-all ${order.status === OrderStatus.PENDING ? 'bg-zinc-800 hover:bg-zinc-700' : 'bg-emerald-600 hover:bg-emerald-500'}`}
                  >
                    {order.status === OrderStatus.PENDING ? 'Start Preparing' : 'Ready to Serve'}
                  </button>
                </div>
              ))
            )}
          </div>

          <div className="glass-panel p-4 rounded-2xl border border-zinc-800">
            <h3 className="text-xs font-black uppercase tracking-widest text-emerald-500 mb-4 flex items-center gap-2">
              <ListChecks size={14} /> Ready to Prepare
            </h3>
            <div className="space-y-2">
              {itemsPossibleToMake.map(item => (
                <div key={item.id} className="flex justify-between items-center text-[11px] p-2 bg-zinc-900/50 rounded-lg border border-zinc-800/50">
                  <span className="text-zinc-300 font-medium">{item.name}</span>
                  <span className="text-emerald-500 font-black">STOCKED</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {inventory.map(item => (
            <div key={item.id} className="glass-panel p-4 rounded-xl border border-zinc-800">
              <div className="flex justify-between items-center mb-3">
                <div>
                  <div className="text-sm font-bold flex items-center gap-2">
                    {item.name}
                    {item.quantity <= item.minThreshold && <AlertTriangle size={12} className="text-amber-500" />}
                  </div>
                  <div className="text-[10px] text-zinc-500">Current: {item.quantity.toFixed(1)} {item.unit}</div>
                </div>
                <div className="flex items-center gap-2">
                   <input 
                     type="number"
                     placeholder="Amt"
                     className="w-16 bg-zinc-900 border border-zinc-800 rounded px-2 py-1 text-xs outline-none"
                     value={addAmount[item.id] || ''}
                     onChange={e => setAddAmount(prev => ({ ...prev, [item.id]: parseFloat(e.target.value) || 0 }))}
                   />
                   <button 
                    onClick={() => handleAdd(item.id)}
                    className="p-1.5 bg-blue-600 hover:bg-blue-500 rounded text-white transition-colors"
                   >
                    <Plus size={14} />
                   </button>
                </div>
              </div>
              <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${item.quantity <= item.minThreshold ? 'bg-amber-500' : 'bg-blue-500'}`}
                  style={{ width: `${Math.min(100, (item.quantity / (item.minThreshold * 2)) * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
