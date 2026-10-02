import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { ThemeProvider as MuiThemeProvider, createTheme } from '@mui/material/styles';

const ThemeContext = createContext();

export const THEMES = [
  {
    id: 'obsidian',
    name: 'Institutional Dark Pro',
    subtitle: 'AuraTrade Terminal ("frontend-design-framework.md")',
    badge: 'Bloomberg / TV Standard',
    tagline: 'High-contrast dark terminal (#121212 / #1E1E1E) with #2563EB deep blue data accents.',
    colors: {
      primary: '#2563EB',
      bg: '#121212',
      card: '#1E1E1E',
      border: '#2C2C2E',
      text: '#FFFFFF',
      textSecondary: '#98989D',
      bullish: '#32D74B',
      bearish: '#FF453A',
      accent: '#2563EB',
    },
  },
  {
    id: 'enterprise',
    name: 'Enterprise Portal',
    subtitle: 'NOSSA Corporate Navy',
    badge: 'NOSSA Seguros Design',
    tagline: 'Corporate banking & billing portal aesthetic with navy headers and slate canvas.',
    colors: {
      primary: '#1B3A6B',
      bg: '#EBEEF2',
      card: '#FFFFFF',
      border: '#D5D8DC',
      text: '#1A1A2E',
      textSecondary: '#5D6D7E',
      bullish: '#82B440',
      bearish: '#C0392B',
      accent: '#82B440',
    },
  },
];

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    try {
      const saved = localStorage.getItem('txbot_theme');
      if (saved && (saved === 'obsidian' || saved === 'enterprise')) {
        return saved;
      }
    } catch (e) {
      // ignore
    }
    return 'obsidian';
  });

  const [isThemeModalOpen, setIsThemeModalOpen] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('txbot_theme', theme);
    } catch (e) {}
  }, [theme]);

  const setTheme = (newTheme) => {
    if (newTheme === 'obsidian' || newTheme === 'enterprise') {
      setThemeState(newTheme);
    }
  };

  const toggleTheme = () => {
    setThemeState((prev) => {
      const currentIndex = THEMES.findIndex((t) => t.id === prev);
      const nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % THEMES.length;
      return THEMES[nextIndex].id;
    });
  };
  const cycleTheme = toggleTheme;

  // Generate synchronized Material UI Theme
  const muiTheme = useMemo(() => {
    const isDark = theme === 'obsidian';
    return createTheme({
      palette: {
        mode: isDark ? 'dark' : 'light',
        primary: {
          main: isDark ? '#2563EB' : '#1B3A6B',
          contrastText: '#FFFFFF',
        },
        secondary: {
          main: isDark ? '#32D74B' : '#82B440',
        },
        error: {
          main: isDark ? '#FF453A' : '#C0392B',
        },
        success: {
          main: isDark ? '#32D74B' : '#82B440',
        },
        background: {
          default: isDark ? '#121212' : '#EBEEF2',
          paper: isDark ? '#1E1E1E' : '#FFFFFF',
        },
        text: {
          primary: isDark ? '#FFFFFF' : '#1A1A2E',
          secondary: isDark ? '#98989D' : '#5D6D7E',
        },
        divider: isDark ? '#2C2C2E' : '#D5D8DC',
      },
      shape: {
        borderRadius: 12,
      },
      typography: {
        fontFamily: "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif",
      },
      components: {
        MuiCard: {
          styleOverrides: {
            root: {
              borderRadius: 16,
              backgroundImage: 'none',
              border: isDark ? '1px solid #2C2C2E' : '1px solid #D5D8DC',
            },
          },
        },
        MuiPaper: {
          styleOverrides: {
            root: {
              backgroundImage: 'none',
            },
          },
        },
        MuiButton: {
          styleOverrides: {
            root: {
              borderRadius: 8,
              textTransform: 'none',
              fontWeight: 600,
            },
          },
        },
      },
    });
  }, [theme]);

  return (
    <ThemeContext.Provider
      value={{
        theme,
        setTheme,
        toggleTheme,
        cycleTheme,
        currentTheme: THEMES.find((t) => t.id === theme) || THEMES[0],
        themes: THEMES,
        isEnterprise: theme === 'enterprise',
        isObsidian: theme === 'obsidian',
        isThemeModalOpen,
        setIsThemeModalOpen,
      }}
    >
      <MuiThemeProvider theme={muiTheme}>
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
