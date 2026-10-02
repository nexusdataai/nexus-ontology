
export interface Profile {
  id: string;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  name: string;
  description: string | null;
  price: number;
  category: string;
  image_url: string | null;
  stock_quantity: number;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  user_id: string;
  status: string;
  total_amount: number;
  created_at: string;
  updated_at: string;
}

export interface OrderItem {
  id: string;
  order_id: string;
  product_id: string;
  quantity: number;
  price: number;
  created_at: string;
}

export interface Customer {
  id: string;
  user_id: string | null;
  name: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  country: string | null;
  created_at: string;
  updated_at: string;
}

export interface Analytics {
  id: string;
  date: string;
  sales_amount: number;
  orders_count: number;
  customers_count: number;
  category: string | null;
  created_at: string;
}

// Add database type definition to be used with Supabase client
export type Database = {
  public: {
    Tables: {
      profiles: {
        Row: Profile;
        Insert: Omit<Profile, 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Profile, 'created_at' | 'updated_at'>>;
      };
      products: {
        Row: Product;
        Insert: Omit<Product, 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Product, 'created_at' | 'updated_at'>>;
      };
      orders: {
        Row: Order;
        Insert: Omit<Order, 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Order, 'created_at' | 'updated_at'>>;
      };
      order_items: {
        Row: OrderItem;
        Insert: Omit<OrderItem, 'created_at'>;
        Update: Partial<Omit<OrderItem, 'created_at'>>;
      };
      customers: {
        Row: Customer;
        Insert: Omit<Customer, 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Customer, 'created_at' | 'updated_at'>>;
      };
      analytics: {
        Row: Analytics;
        Insert: Omit<Analytics, 'created_at'>;
        Update: Partial<Omit<Analytics, 'created_at'>>;
      };
    };
    Views: {};
    Functions: {};
    Enums: {};
    CompositeTypes: {};
  };
};
