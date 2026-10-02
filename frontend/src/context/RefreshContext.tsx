import React, { createContext, useContext, useState, useCallback } from 'react';

interface RefreshContextType {
  refreshAll: () => void;
  isRefreshing: boolean;
  lastRefresh: Date;
  triggerRefresh: () => void;
  refreshTrigger: number;
}

const RefreshContext = createContext<RefreshContextType | undefined>(undefined);

export const useRefresh = () => {
  const context = useContext(RefreshContext);
  if (context === undefined) {
    throw new Error('useRefresh must be used within a RefreshProvider');
  }
  return context;
};

interface RefreshProviderProps {
  children: React.ReactNode;
}

export const RefreshProvider: React.FC<RefreshProviderProps> = ({ children }) => {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const refreshAll = useCallback(() => {
    setIsRefreshing(true);
    setLastRefresh(new Date());
    
    // Trigger a refresh by incrementing the trigger counter
    setRefreshTrigger(prev => prev + 1);
    
    // Simulate a brief loading state
    setTimeout(() => {
      setIsRefreshing(false);
    }, 1000);
  }, []);

  const triggerRefresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  return (
    <RefreshContext.Provider value={{ 
      refreshAll, 
      isRefreshing, 
      lastRefresh, 
      triggerRefresh,
      refreshTrigger 
    }}>
      {children}
    </RefreshContext.Provider>
  );
}; 