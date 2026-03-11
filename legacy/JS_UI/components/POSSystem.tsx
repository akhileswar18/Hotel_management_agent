
import React, { useState, useMemo } from 'react';
import { 
  ShoppingCart, 
  Plus, 
  Minus, 
  Trash2, 
  CheckCircle, 
  Search, 
  Coffee, 
  Utensils, 
  LayoutList,
  ChevronRight,
  Receipt,
  User,
  CreditCard
} from 'lucide-react';
import { MenuItem, OrderItem, Category } from '../types';

interface POSSystemProps {
  menuItems: MenuItem[];
  onPlaceOrder: (items: OrderItem[], tableNumber: string) => void;
}

export const POSSystem: React.FC<POSSystemProps> = ({ menuItems, onPlaceOrder }) => {
  const [cart, setCart] = useState<OrderItem[]>([]);
  const [tableNumber, setTableNumber] = useState('1');
  const [selectedCategory, setSelectedCategory] = useState<Category | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredMenuItems = useMemo(() => {
    return menuItems.filter(item => {
      const matchesCategory = selectedCategory === 'ALL' || item.category === selectedCategory;
      const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [menuItems, selectedCategory, searchQuery]);

  const addToCart = (item: MenuItem) => {
    setCart(prev => {
      const existing = prev.find(i => i.menuItemId === item.id);
      if (existing) {
        return prev.map(i => i.menuItemId === item.id ? { ...i, quantity: i.quantity + 1 } : i);
      }
      return [...prev, { menuItemId: item.id, name: item.name, quantity: 1, price: item.price }];
    });
  };

  const updateQuantity = (id: string, delta: number) => {
    setCart(prev => prev.map(i => {
      if (i.menuItemId === id) {
        const newQty = Math.max(1, i.quantity + delta);
        return { ...i, quantity: newQty };
      }
      return i;
    }));
  };

  const removeItem = (id: string) => {
    setCart(prev => prev.filter(i => i.menuItemId !== id));
  };

  const subtotal = cart.reduce((acc, it) => acc + (it.price * it.quantity), 0);
  const tax = subtotal * 0.08;
  const total = subtotal + tax;

  const handleCheckout = () => {
    if (cart.length === 0) return;
    onPlaceOrder(cart, tableNumber === '0' ? 'TAKEAWAY' : tableNumber);
    setCart([]);
    setTableNumber('1');
  };

  const categories: (Category | 'ALL')[] = ['ALL', 'FOOD', 'DRINK', 'SNAX', 'DESSERT'];

  return (
    <div className="flex h-[calc(100vh-160px)] gap-6 overflow-hidden">
      {/* Sidebar: Menu Navigation & Item Selection */}
      <div className="w-80 flex flex-col glass-panel rounded-3xl border border-zinc-800 overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={16} />
            <input
              placeholder="Search dishes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-2 pl-10 pr-4 text-sm focus:ring-1 focus:ring-emerald-500 outline-none"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar">
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-lg text-[10px] font-bold transition-all border ${
                  selectedCategory === cat 
                    ? 'bg-emerald-600 border-emerald-500 text-white' 
                    : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2 no-scrollbar">
          {filteredMenuItems.map(item => (
            <button
              key={item.id}
              onClick={() => addToCart(item)}
              className="w-full flex items-center justify-between p-3 rounded-2xl bg-zinc-900/50 border border-zinc-800 hover:border-emerald-500/30 hover:bg-emerald-500/5 transition-all group"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center text-zinc-500 group-hover:text-emerald-500">
                  {item.category === 'DRINK' ? <Coffee size={16} /> : <Utensils size={16} />}
                </div>
                <div className="text-left">
                  <div className="text-xs font-bold text-zinc-200 truncate w-32">{item.name}</div>
                  <div className="text-[10px] text-zinc-500">${item.price.toFixed(2)}</div>
                </div>
              </div>
              <ChevronRight size={14} className="text-zinc-600 group-hover:text-emerald-500 transition-colors" />
            </button>
          ))}
        </div>
      </div>

      {/* Main Area: Cart & Order Details */}
      <div className="flex-1 flex flex-col gap-6">
        <div className="flex-1 glass-panel rounded-3xl border border-zinc-800 overflow-hidden flex flex-col shadow-2xl">
          <div className="p-6 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/20">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500/10 rounded-xl">
                <ShoppingCart className="text-emerald-500" size={24} />
              </div>
              <div>
                <h2 className="font-black text-xl">Active Order</h2>
                <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Billing Details</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-zinc-800/50 p-2 rounded-xl border border-zinc-700/50">
                <User size={16} className="text-zinc-500" />
                <span className="text-xs font-bold mr-2">Table:</span>
                <select 
                  value={tableNumber}
                  onChange={(e) => setTableNumber(e.target.value)}
                  className="bg-transparent text-emerald-500 font-bold outline-none"
                >
                  {[...Array(20)].map((_, i) => (
                    <option key={i+1} value={i+1}>{i+1}</option>
                  ))}
                  <option value="0">TAKEAWAY</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-8 space-y-6 no-scrollbar">
            {cart.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-zinc-700">
                <div className="w-24 h-24 rounded-full bg-zinc-900/50 border border-zinc-800 flex items-center justify-center mb-6">
                  <Receipt size={40} className="opacity-20" />
                </div>
                <h3 className="text-lg font-bold text-zinc-600">No items selected</h3>
                <p className="text-sm">Pick items from the menu to start billing</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {cart.map(item => (
                  <div key={item.menuItemId} className="flex items-center bg-zinc-900/30 border border-zinc-800 p-4 rounded-2xl group transition-all hover:border-zinc-700">
                    <div className="flex-1">
                      <div className="font-bold text-lg">{item.name}</div>
                      <div className="text-emerald-500 text-sm font-medium">${item.price.toFixed(2)} / unit</div>
                    </div>
                    
                    <div className="flex items-center gap-6">
                      <div className="flex items-center gap-4 bg-zinc-800 rounded-xl p-1 px-3 border border-zinc-700">
                        <button onClick={() => updateQuantity(item.menuItemId, -1)} className="p-1 hover:text-emerald-500 transition-colors">
                          <Minus size={18} />
                        </button>
                        <span className="text-lg font-black w-6 text-center">{item.quantity}</span>
                        <button onClick={() => updateQuantity(item.menuItemId, 1)} className="p-1 hover:text-emerald-500 transition-colors">
                          <Plus size={18} />
                        </button>
                      </div>
                      
                      <div className="text-right w-24">
                        <div className="text-lg font-black">${(item.price * item.quantity).toFixed(2)}</div>
                      </div>
                      
                      <button 
                        onClick={() => removeItem(item.menuItemId)}
                        className="p-2 text-zinc-600 hover:text-red-500 transition-all opacity-0 group-hover:opacity-100"
                      >
                        <Trash2 size={20} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="p-8 bg-[#0d0d0d] border-t border-zinc-800">
            <div className="flex gap-8 items-end">
              <div className="flex-1 grid grid-cols-2 gap-4">
                <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl">
                  <div className="text-xs text-zinc-500 font-bold mb-1">SUBTOTAL</div>
                  <div className="text-xl font-bold">${subtotal.toFixed(2)}</div>
                </div>
                <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl">
                  <div className="text-xs text-zinc-500 font-bold mb-1">TAX (8%)</div>
                  <div className="text-xl font-bold text-orange-400">${tax.toFixed(2)}</div>
                </div>
              </div>
              
              <div className="flex-1 flex flex-col items-end">
                <div className="text-xs text-zinc-500 font-bold mb-1 uppercase tracking-widest">Total Amount Due</div>
                <div className="text-5xl font-black text-emerald-500 mb-6">${total.toFixed(2)}</div>
                
                <div className="flex gap-4 w-full">
                  <button className="flex-1 py-4 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all">
                    <LayoutList size={20} />
                    DRAFT
                  </button>
                  <button
                    onClick={handleCheckout}
                    disabled={cart.length === 0}
                    className="flex-[2] py-4 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-2xl font-black tracking-widest shadow-lg shadow-emerald-900/30 flex items-center justify-center gap-2 transition-all active:scale-95"
                  >
                    <CreditCard size={20} />
                    PROCESS CHECKOUT
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
