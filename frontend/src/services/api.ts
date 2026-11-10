
import type { SupabaseClient } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';
import { Product, Order, Analytics, Customer, OrderItem } from '@/types/database.types';

// The shared Database type (types/database.types.ts) does not satisfy supabase-js's
// GenericSchema (interface rows, no Relationships), so insert/update on its tables
// resolve to `never`. This schema types only the writes made below.
type PlainRow<T> = { [K in keyof T]: T[K] };
type WritableTable<T> = {
  Row: PlainRow<T>;
  Insert: PlainRow<Partial<T>>;
  Update: PlainRow<Partial<T>>;
  Relationships: [];
};
type ApiWriteDatabase = {
  public: {
    Tables: {
      customers: WritableTable<Customer>;
      orders: WritableTable<Order>;
      order_items: WritableTable<OrderItem>;
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
  };
};
// Type-only view of the same client object; runtime behaviour is unchanged.
const writeClient = supabase as unknown as SupabaseClient<ApiWriteDatabase>;

// Products related functions
export const getProducts = async (): Promise<Product[]> => {
  const { data, error } = await supabase
    .from('products')
    .select('*')
    .order('name');

  if (error) {
    console.error('Error fetching products:', error);
    throw error;
  }

  return data as Product[];
};

export const getProductById = async (id: string): Promise<Product> => {
  const { data, error } = await supabase
    .from('products')
    .select('*')
    .eq('id', id)
    .single();

  if (error) {
    console.error('Error fetching product:', error);
    throw error;
  }

  return data as Product;
};

export const getProductsByCategory = async (category: string): Promise<Product[]> => {
  const { data, error } = await supabase
    .from('products')
    .select('*')
    .eq('category', category)
    .order('name');

  if (error) {
    console.error('Error fetching products by category:', error);
    throw error;
  }

  return data as Product[];
};

// Orders related functions
export const getUserOrders = async (): Promise<Order[]> => {
  const { data, error } = await supabase
    .from('orders')
    .select('*')
    .order('created_at', { ascending: false });

  if (error) {
    console.error('Error fetching orders:', error);
    throw error;
  }

  return data as Order[];
};

export const getOrderById = async (id: string): Promise<Order> => {
  const { data, error } = await supabase
    .from('orders')
    .select('*')
    .eq('id', id)
    .single();

  if (error) {
    console.error('Error fetching order:', error);
    throw error;
  }

  return data as Order;
};

export const getOrderItems = async (orderId: string) => {
  const { data, error } = await supabase
    .from('order_items')
    .select(`
      *,
      products:product_id (
        name,
        price,
        image_url
      )
    `)
    .eq('order_id', orderId);

  if (error) {
    console.error('Error fetching order items:', error);
    throw error;
  }

  return data;
};

// Analytics related functions
export const getAnalyticsByCategoryAndDateRange = async (
  startDate: string, 
  endDate: string
) => {
  const { data, error } = await supabase
    .from('analytics')
    .select('*')
    .gte('date', startDate)
    .lte('date', endDate)
    .order('date');

  if (error) {
    console.error('Error fetching analytics:', error);
    throw error;
  }

  return data as Analytics[];
};

// Customers related functions
export const getCustomers = async (): Promise<Customer[]> => {
  const { data, error } = await supabase
    .from('customers')
    .select('*')
    .order('name');

  if (error) {
    console.error('Error fetching customers:', error);
    throw error;
  }

  return data as Customer[];
};

export const getCustomerById = async (id: string): Promise<Customer> => {
  const { data, error } = await supabase
    .from('customers')
    .select('*')
    .eq('id', id)
    .single();

  if (error) {
    console.error('Error fetching customer:', error);
    throw error;
  }

  return data as Customer;
};

// Create a new customer
export const createCustomer = async (customerData: Partial<Customer>): Promise<Customer> => {
  const { data, error } = await writeClient
    .from('customers')
    .insert([customerData])
    .select()
    .single();

  if (error) {
    console.error('Error creating customer:', error);
    throw error;
  }

  return data as Customer;
};

// Update a customer
export const updateCustomer = async (id: string, customerData: Partial<Customer>): Promise<Customer> => {
  const { data, error } = await writeClient
    .from('customers')
    .update(customerData)
    .eq('id', id)
    .select()
    .single();

  if (error) {
    console.error('Error updating customer:', error);
    throw error;
  }

  return data as Customer;
};

// Create a new order
export const createOrder = async (orderData: Partial<Order>, orderItems: Partial<OrderItem>[]): Promise<Order> => {
  // Start a transaction
  const { data: order, error: orderError } = await writeClient
    .from('orders')
    .insert([orderData])
    .select()
    .single();

  if (orderError) {
    console.error('Error creating order:', orderError);
    throw orderError;
  }

  if (!order) {
    throw new Error('Failed to create order');
  }

  // Add order items with the new order ID
  const itemsWithOrderId = orderItems.map(item => ({
    ...item,
    order_id: order.id
  }));

  const { error: itemsError } = await writeClient
    .from('order_items')
    .insert(itemsWithOrderId);

  if (itemsError) {
    console.error('Error creating order items:', itemsError);
    throw itemsError;
  }

  return order as Order;
};
