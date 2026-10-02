import { createContext, useContext, useEffect, useState, useCallback } from 'react';

type Theme = 'dark' | 'light';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const DARK_VARS: Record<string, string> = {
  '--background': '225 45% 6%',
  '--foreground': '210 40% 96%',
  '--card': '222 40% 10%',
  '--card-foreground': '210 40% 96%',
  '--popover': '222 40% 10%',
  '--popover-foreground': '210 40% 96%',
  '--primary': '262 83% 58%',
  '--primary-foreground': '0 0% 100%',
  '--secondary': '220 30% 14%',
  '--secondary-foreground': '210 40% 96%',
  '--muted': '220 30% 14%',
  '--muted-foreground': '215 20% 60%',
  '--accent': '220 30% 14%',
  '--accent-foreground': '210 40% 96%',
  '--destructive': '0 63% 31%',
  '--destructive-foreground': '210 40% 98%',
  '--border': '220 25% 16%',
  '--input': '220 25% 16%',
  '--ring': '262 83% 58%',
};

const LIGHT_VARS: Record<string, string> = {
  '--background': '0 0% 98%',
  '--foreground': '222 47% 11%',
  '--card': '0 0% 100%',
  '--card-foreground': '222 47% 11%',
  '--popover': '0 0% 100%',
  '--popover-foreground': '222 47% 11%',
  '--primary': '262 83% 58%',
  '--primary-foreground': '0 0% 100%',
  '--secondary': '214 32% 91%',
  '--secondary-foreground': '222 47% 11%',
  '--muted': '210 40% 96%',
  '--muted-foreground': '215 16% 47%',
  '--accent': '214 32% 91%',
  '--accent-foreground': '222 47% 11%',
  '--destructive': '0 84% 60%',
  '--destructive-foreground': '0 0% 100%',
  '--border': '214 32% 91%',
  '--input': '214 32% 91%',
  '--ring': '262 83% 58%',
};

function applyTheme(t: Theme) {
  const root = document.documentElement;
  root.classList.remove('light', 'dark');
  root.classList.add(t);
  root.style.colorScheme = t;

  const vars = t === 'dark' ? DARK_VARS : LIGHT_VARS;
  for (const [key, value] of Object.entries(vars)) {
    root.style.setProperty(key, value);
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('app-theme') as Theme;
    if (saved === 'light' || saved === 'dark') return saved;
    return 'dark';
  });

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem('app-theme', theme);
  }, [theme]);

  useEffect(() => {
    applyTheme(theme);
  }, []);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    applyTheme(t);
    localStorage.setItem('app-theme', t);
  }, []);

  const toggleTheme = useCallback(() => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
  }, [theme, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
