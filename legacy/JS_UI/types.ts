
export enum OrderStatus {
  PENDING = 'PENDING',
  PREPARING = 'PREPARING',
  READY = 'READY',
  SERVED = 'SERVED',
  CANCELLED = 'CANCELLED'
}

export type Category = 'FOOD' | 'DRINK' | 'SNAX' | 'DESSERT';

export interface MenuItem {
  id: string;
  name: string;
  price: number;
  category: Category;
  inStock: boolean;
  ingredients?: { inventoryItemId: string; amount: number }[];
}

export interface OrderItem {
  menuItemId: string;
  name: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  tableNumber: string | 'TAKEAWAY';
  items: OrderItem[];
  status: OrderStatus;
  timestamp: number;
  total: number;
}

export interface InventoryItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  minThreshold: number;
}

export interface AgentAction {
  id: string;
  agent: 'ORCHESTRATOR' | 'KITCHEN' | 'INVENTORY' | 'BILLING';
  message: string;
  timestamp: number;
  type: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';
}

export interface FinancialLog {
  id: string;
  type: 'INCOME' | 'EXPENSE';
  amount: number;
  description: string;
  timestamp: number;
}

export interface AgentSettings {
  voiceName: 'Puck' | 'Charon' | 'Kore' | 'Fenrir' | 'Zephyr';
  language: 'English' | 'Telugu' | 'Hindi';
  autoInventoryDeduction: boolean;
  thinkingBudget: number;
}

export interface AgentHealthStatus {
  name: string;
  status: 'ONLINE' | 'BUSY' | 'OFFLINE';
  latency: number;
  lastActive: number;
}
