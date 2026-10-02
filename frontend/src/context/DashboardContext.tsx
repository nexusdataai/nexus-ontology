import React, { createContext, useContext, useState, useCallback } from 'react';

type DashboardView = 'default' | 'topProducts' | 'sales' | 'customers' | 'analytics';

interface DashboardContextType {
  currentView: DashboardView;
  setView: (view: DashboardView) => void;
  resetView: () => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [currentView, setCurrentView] = useState<DashboardView>('default');

  const setView = useCallback((view: DashboardView) => {
    setCurrentView(view);
  }, []);

  const resetView = useCallback(() => {
    setCurrentView('default');
  }, []);

  return (
    <DashboardContext.Provider value={{ currentView, setView, resetView }}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (context === undefined) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
} 