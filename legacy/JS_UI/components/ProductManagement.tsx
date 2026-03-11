
import React, { useState } from 'react';
import { 
  Package, 
  Plus, 
  Search, 
  Edit3, 
  Trash2, 
  CheckCircle, 
  XCircle,
  Tag,
  DollarSign,
  Coffee,
  Utensils,
  LayoutGrid,
  MoreVertical
} from 'lucide-react';
import { MenuItem, Category } from '../types';

interface ProductManagementProps {
  products: MenuItem[];
  onAddProduct: (p: Omit<MenuItem, 'id'>) => void;
  onUpdateProduct: (id: string, p: Partial<MenuItem>) => void;
  onDeleteProduct: (id: string) => void;
}

export const ProductManagement: React.FC<ProductManagementProps> = ({ 
  products, 
  onAddProduct, 
  onUpdateProduct, 
  onDeleteProduct 
}) => {
  const [search, setSearch] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [newProduct, setNewProduct] = useState<Omit<MenuItem, 'id'>>({
    name: '',
    price: 0,
    category: 'FOOD',
    inStock: true
  });

  const filteredProducts = products.filter(p => 
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleSave = () => {
    if (!newProduct.name || newProduct.price <= 0) return;
    onAddProduct(newProduct);
    setIsAdding(false);
    setNewProduct({ name: '', price: 0, category: 'FOOD', inStock: true });
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black flex items-center gap-3">
            <Package className="text-blue-400" size={32} />
            Menu Ecosystem
          </h1>
          <p className="text-zinc-500 text-sm mt-1">Configure your product offerings and digital menu</p>
        </div>
        <button 
          onClick={() => setIsAdding(true)}
          className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-2xl font-bold shadow-lg shadow-blue-900/20 hover:bg-blue-500 transition-all active:scale-95"
        >
          <Plus size={20} /> ADD NEW ITEM
        </button>
      </div>

      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" size={18} />
          <input
            placeholder="Search products by name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-zinc-900/50 border border-zinc-800 rounded-2xl py-4 pl-12 pr-4 focus:ring-1 focus:ring-blue-500 outline-none"
          />
        </div>
        <div className="flex bg-zinc-900 border border-zinc-800 rounded-2xl p-1">
          <button className="p-3 bg-zinc-800 rounded-xl text-blue-400 shadow-lg"><LayoutGrid size={20} /></button>
          <button className="p-3 text-zinc-500 hover:text-white"><MoreVertical size={20} /></button>
        </div>
      </div>

      {isAdding && (
        <div className="glass-panel p-8 rounded-3xl border border-blue-500/30 bg-blue-500/5 animate-in slide-in-from-top-4">
          <h3 className="text-xl font-bold mb-6">Create New Menu Item</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-zinc-500 uppercase">Item Name</label>
              <input 
                value={newProduct.name}
                onChange={e => setNewProduct({...newProduct, name: e.target.value})}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-2 px-4 outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="e.g. Garlic Naan"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-zinc-500 uppercase">Price ($)</label>
              <input 
                type="number"
                value={newProduct.price}
                onChange={e => setNewProduct({...newProduct, price: parseFloat(e.target.value)})}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-2 px-4 outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-zinc-500 uppercase">Category</label>
              <select 
                value={newProduct.category}
                onChange={e => setNewProduct({...newProduct, category: e.target.value as Category})}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-2 px-4 outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="FOOD">FOOD</option>
                <option value="DRINK">DRINK</option>
                <option value="SNAX">SNAX</option>
                <option value="DESSERT">DESSERT</option>
              </select>
            </div>
            <div className="flex items-end gap-3">
              <button 
                onClick={handleSave}
                className="flex-1 bg-blue-600 py-2.5 rounded-xl font-bold hover:bg-blue-500 transition-all"
              >
                SAVE ITEM
              </button>
              <button 
                onClick={() => setIsAdding(false)}
                className="px-4 py-2.5 bg-zinc-800 rounded-xl hover:bg-zinc-700 transition-all"
              >
                CANCEL
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredProducts.map(product => (
          <div key={product.id} className="glass-panel p-6 rounded-3xl border border-zinc-800 group hover:border-blue-500/50 transition-all relative overflow-hidden">
            <div className={`absolute top-0 right-0 p-3 ${product.inStock ? 'text-emerald-500' : 'text-red-500'}`}>
              {product.inStock ? <CheckCircle size={14} /> : <XCircle size={14} />}
            </div>
            
            <div className="w-12 h-12 rounded-2xl bg-zinc-800/50 flex items-center justify-center text-zinc-400 group-hover:bg-blue-600/10 group-hover:text-blue-400 mb-6 transition-all">
              {product.category === 'DRINK' ? <Coffee size={24} /> : <Utensils size={24} />}
            </div>

            <h3 className="text-lg font-bold mb-1">{product.name}</h3>
            <div className="flex items-center gap-2 mb-4 text-xs font-bold text-zinc-500 uppercase tracking-widest">
              <Tag size={12} />
              {product.category}
            </div>

            <div className="flex justify-between items-end mt-8">
              <div className="text-2xl font-black text-white">
                <span className="text-blue-500 text-sm">$</span>
                {product.price.toFixed(2)}
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={() => onUpdateProduct(product.id, { inStock: !product.inStock })}
                  className="p-2 bg-zinc-900 border border-zinc-800 rounded-xl hover:bg-zinc-800 text-zinc-500 transition-all"
                >
                  <Edit3 size={16} />
                </button>
                <button 
                  onClick={() => onDeleteProduct(product.id)}
                  className="p-2 bg-zinc-900 border border-zinc-800 rounded-xl hover:bg-red-900/20 text-red-900 transition-all"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
