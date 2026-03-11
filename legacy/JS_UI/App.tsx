
import React, { useState, useCallback, useMemo } from 'react';
import { 
  LayoutDashboard, 
  UtensilsCrossed, 
  Activity, 
  Settings, 
  Bell,
  Search,
  Zap,
  CreditCard,
  History,
  Store,
  ShieldCheck,
  Heart
} from 'lucide-react';
import { CommandCenter } from './components/CommandCenter';
import { KitchenDisplay } from './components/KitchenDisplay';
import { AgentLog } from './components/AgentLog';
import { FinancialTracker } from './components/FinancialTracker';
import { POSSystem } from './components/POSSystem';
import { OrderHistory } from './components/OrderHistory';
import { ProductManagement } from './components/ProductManagement';
import { AgentSettingsPanel } from './components/AgentSettingsPanel';
import { AgentHealthMonitor } from './components/AgentHealthMonitor';
import { Order, OrderStatus, InventoryItem, AgentAction, FinancialLog, OrderItem, MenuItem, AgentSettings } from './types';
import { orchestrateInput } from './services/gemini';

const INITIAL_INVENTORY: InventoryItem[] = [
  { id: '1', name: 'Masala Dosa Batter', quantity: 24, unit: 'kg', minThreshold: 5 },
  { id: '2', name: 'Potatoes', quantity: 12, unit: 'kg', minThreshold: 10 },
  { id: '3', name: 'Coconut Chutney', quantity: 8, unit: 'L', minThreshold: 3 },
  { id: '4', name: 'Coffee Beans', quantity: 2.5, unit: 'kg', minThreshold: 1 },
  { id: '5', name: 'Milk', quantity: 15, unit: 'L', minThreshold: 5 },
];

const INITIAL_MENU: MenuItem[] = [
  { id: 'm1', name: 'Masala Dosa', price: 8.50, category: 'FOOD', inStock: true, ingredients: [{ inventoryItemId: '1', amount: 0.2 }, { inventoryItemId: '2', amount: 0.1 }] },
  { id: 'm2', name: 'Plain Dosa', price: 6.00, category: 'FOOD', inStock: true, ingredients: [{ inventoryItemId: '1', amount: 0.2 }] },
  { id: 'm3', name: 'Idli (2pcs)', price: 4.50, category: 'FOOD', inStock: true },
  { id: 'm4', name: 'Vada (2pcs)', price: 5.00, category: 'FOOD', inStock: true },
  { id: 'm5', name: 'Filter Coffee', price: 2.50, category: 'DRINK', inStock: true, ingredients: [{ inventoryItemId: '4', amount: 0.05 }, { inventoryItemId: '5', amount: 0.2 }] },
  { id: 'm6', name: 'Masala Tea', price: 2.00, category: 'DRINK', inStock: true },
  { id: 'm7', name: 'Mango Lassi', price: 3.50, category: 'DRINK', inStock: true },
  { id: 'm8', name: 'Gulab Jamun', price: 3.00, category: 'DESSERT', inStock: true },
];

const App: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>(INITIAL_INVENTORY);
  const [menuItems, setMenuItems] = useState<MenuItem[]>(INITIAL_MENU);
  const [logs, setLogs] = useState<AgentAction[]>([]);
  const [financials, setFinancials] = useState<FinancialLog[]>([]);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'kitchen' | 'pos' | 'history' | 'products' | 'health'>('dashboard');
  const [agentSettings, setAgentSettings] = useState<AgentSettings>({
    voiceName: 'Puck',
    language: 'English',
    autoInventoryDeduction: true,
    thinkingBudget: 1000,
  });

  const addLog = useCallback((agent: AgentAction['agent'], message: string, type: AgentAction['type'] = 'INFO') => {
    setLogs(prev => [{
      id: Math.random().toString(36).substr(2, 9),
      agent,
      message,
      timestamp: Date.now(),
      type
    }, ...prev.slice(0, 49)]);
  }, []);

  const applyInventoryImpact = useCallback((impacts: any[], alerts?: string[]) => {
    if (impacts && impacts.length > 0) {
      setInventory(prev => prev.map(invItem => {
        const impact = impacts.find((imp: any) => imp.inventoryItemId === invItem.id);
        if (impact) {
          addLog('INVENTORY', `Deducting ${impact.deductionAmount}${impact.unit} of ${invItem.name}`);
          return { ...invItem, quantity: Math.max(0, invItem.quantity - impact.deductionAmount) };
        }
        return invItem;
      }));
    }
    if (alerts) {
      alerts.forEach((alert: string) => addLog('INVENTORY', alert, 'WARNING'));
    }
  }, [addLog]);

  const placeOrder = useCallback(async (items: OrderItem[], tableNumber: string | 'TAKEAWAY', source: 'AGENT' | 'POS' = 'POS') => {
    const total = items.reduce((sum, it) => sum + (it.quantity * it.price), 0);
    const newOrder: Order = {
      id: `ORD-${Math.random().toString(36).substr(2, 5).toUpperCase()}`,
      tableNumber,
      items,
      status: OrderStatus.PENDING,
      timestamp: Date.now(),
      total
    };

    setOrders(prev => [newOrder, ...prev]);
    addLog(source === 'AGENT' ? 'ORCHESTRATOR' : 'BILLING', `Order ${newOrder.id} placed via ${source}. Total: $${total.toFixed(2)}`);
    
    setFinancials(prev => [{
      id: Math.random().toString(36).substr(2, 9),
      type: 'INCOME',
      amount: total,
      description: `Order ${newOrder.id}`,
      timestamp: Date.now()
    }, ...prev]);

    if (source === 'POS' && agentSettings.autoInventoryDeduction) {
      try {
        const itemSummary = items.map(i => `${i.quantity}x ${i.name}`).join(', ');
        addLog('ORCHESTRATOR', `Calculating inventory impact for order ${newOrder.id}...`);
        const result = await orchestrateInput(`Process inventory for POS order: ${itemSummary}`, inventory);
        if (result.inventoryImpact) {
          applyInventoryImpact(result.inventoryImpact, result.inventoryAlerts);
        }
      } catch (error) {
        console.error("Failed to auto-deduct inventory via agent:", error);
        addLog('INVENTORY', `Manual inventory deduction required for order ${newOrder.id} - Brain busy`, 'ERROR');
      }
    }

    return newOrder;
  }, [addLog, inventory, applyInventoryImpact, agentSettings]);

  const handleProcessedCommand = (result: any) => {
    const { intent, data, agentResponse, inventoryAlerts, inventoryImpact } = result;
    addLog('ORCHESTRATOR', agentResponse);

    if (intent === 'ORDER' && data?.items) {
      const items: OrderItem[] = data.items.map((it: any) => ({
        name: it.name,
        quantity: it.quantity,
        price: it.price_estimated || 10,
        menuItemId: 'dynamic'
      }));
      
      placeOrder(items, data.tableNumber || 'TAKEAWAY', 'AGENT');

      if (inventoryImpact) {
        applyInventoryImpact(inventoryImpact, inventoryAlerts);
      }
    }
  };

  const updateOrderStatus = (id: string, status: OrderStatus) => {
    setOrders(prev => prev.map(o => o.id === id ? { ...o, status } : o));
    addLog('KITCHEN', `Order ${id} status: ${status}`);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-zinc-100 flex overflow-hidden">
      <aside className="w-20 lg:w-64 border-r border-zinc-800 flex flex-col items-center lg:items-stretch bg-[#0d0d0d] z-20">
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-900/20">
            <Zap className="text-white fill-white" size={24} />
          </div>
          <span className="hidden lg:block font-black text-xl tracking-tight">AGENTIC<span className="text-emerald-500">HMS</span></span>
        </div>
        <nav className="flex-1 mt-6 px-4 space-y-2 overflow-y-auto no-scrollbar">
          {[
            { id: 'dashboard', icon: LayoutDashboard, label: 'Control Room' },
            { id: 'pos', icon: CreditCard, label: 'Modern POS' },
            { id: 'kitchen', icon: UtensilsCrossed, label: 'Kitchen Hub' },
            { id: 'history', icon: History, label: 'Order History' },
            { id: 'products', icon: Store, label: 'Menu Mgmt' },
            { id: 'health', icon: Heart, label: 'Agent Health' },
          ].map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id as any)}
              className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${
                activeTab === item.id 
                  ? 'bg-emerald-600/10 text-emerald-500 border border-emerald-500/20' 
                  : 'text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300'
              }`}
            >
              <item.icon size={22} />
              <span className="hidden lg:block font-medium">{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>
      <main className="flex-1 flex flex-col relative min-w-0 h-screen overflow-hidden">
        <header className="h-20 border-b border-zinc-800 flex items-center justify-between px-8 bg-[#0a0a0a]/50 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-4 bg-zinc-900/50 px-4 py-2 rounded-full border border-zinc-800 lg:w-96">
            <Search size={18} className="text-zinc-500" />
            <input placeholder="Global search..." className="bg-transparent border-none outline-none text-sm w-full" />
          </div>
          <div className="flex items-center gap-6">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
              <Activity size={14} className="text-emerald-500" />
              <span className="text-[10px] font-black text-emerald-500 tracking-widest uppercase">Live Sync</span>
            </div>
            <button className="relative p-2 text-zinc-400 hover:text-white"><Bell size={22} /></button>
            <div className="flex items-center gap-3 pl-6 border-l border-zinc-800">
              <img src="https://picsum.photos/seed/res/40/40" className="w-10 h-10 rounded-full" alt="User" />
            </div>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto p-8 no-scrollbar">
          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-12 gap-8">
              <div className="col-span-12 lg:col-span-8 space-y-8">
                <section>
                  <h1 className="text-2xl font-bold mb-2">Operation Control</h1>
                  <CommandCenter 
                    inventory={inventory} 
                    orders={orders}
                    financials={financials}
                    onUpdateOrder={updateOrderStatus}
                    onProcessed={handleProcessedCommand} 
                    voiceName={agentSettings.voiceName}
                    language={agentSettings.language}
                  />
                </section>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-8">
                    <FinancialTracker logs={financials} />
                    <AgentLog logs={logs} />
                  </div>
                  <AgentHealthMonitor />
                </div>
              </div>
              <div className="col-span-12 lg:col-span-4 space-y-8">
                <div className="glass-panel p-6 rounded-2xl border border-zinc-800">
                   <h2 className="text-xl font-black mb-4 flex items-center gap-2"><UtensilsCrossed size={20} className="text-emerald-500" /> Kitchen Quick View</h2>
                   <KitchenDisplay orders={orders} inventory={inventory} menuItems={menuItems} onUpdateStatus={updateOrderStatus} onAddInventory={(id, amt) => setInventory(prev => prev.map(i => i.id === id ? {...i, quantity: i.quantity + amt} : i))} />
                </div>
              </div>
            </div>
          )}
          {activeTab === 'pos' && (
            <POSSystem menuItems={menuItems} onPlaceOrder={(items, table) => placeOrder(items, table, 'POS')} />
          )}
          {activeTab === 'kitchen' && (
            <div className="max-w-7xl mx-auto">
               <h1 className="text-3xl font-black mb-8 flex items-center gap-3"><UtensilsCrossed size={32} className="text-orange-400" /> Kitchen Operations Hub</h1>
               <KitchenDisplay orders={orders} inventory={inventory} menuItems={menuItems} onUpdateStatus={updateOrderStatus} onAddInventory={(id, amt) => setInventory(prev => prev.map(i => i.id === id ? {...i, quantity: i.quantity + amt} : i))} expanded />
            </div>
          )}
          {activeTab === 'history' && <OrderHistory orders={orders} />}
          {activeTab === 'products' && (
            <div className="space-y-12">
              <ProductManagement 
                products={menuItems} 
                onAddProduct={p => setMenuItems(prev => [...prev, { ...p, id: `m${Date.now()}` }])}
                onUpdateProduct={(id, p) => setMenuItems(prev => prev.map(i => i.id === id ? { ...i, ...p } : i))}
                onDeleteProduct={id => setMenuItems(prev => prev.filter(i => i.id !== id))}
              />
              <AgentSettingsPanel settings={agentSettings} onUpdate={setAgentSettings} />
            </div>
          )}
          {activeTab === 'health' && (
            <div className="max-w-4xl mx-auto space-y-8">
               <h1 className="text-3xl font-black flex items-center gap-3"><Heart className="text-red-500" size={32} /> Agent Health & Observability</h1>
               <AgentHealthMonitor expanded />
               <AgentLog logs={logs} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;
