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
    name: 'Institutional Light Pro',
    subtitle: 'AuraTrade Light Dashboard ("frontend-design-framework.md")',
    badge: 'MUI Light Standard',
    tagline: 'Clean institutional cool slate-gray/blue workstation (#EEF2F6 / #F8FAFC) with #2563EB sapphire accents.',
    colors: {
      primary: '#2563EB',
      bg: '#EEF2F6',
      card: '#F8FAFC',
      border: '#CBD5E1',
      text: '#0F172A',
      textSecondary: '#475569',
      bullish: '#16A34A',
      bearish: '#DC2626',
      accent: '#2563EB',
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
          main: '#2563EB',
          contrastText: '#FFFFFF',
        },
        secondary: {
          main: isDark ? '#32D74B' : '#16A34A',
        },
        error: {
          main: isDark ? '#FF453A' : '#DC2626',
        },
        warning: {
          main: isDark ? '#FF9F0A' : '#D97706',
        },
        success: {
          main: isDark ? '#32D74B' : '#16A34A',
        },
        background: {
          default: isDark ? '#121212' : '#EEF2F6',
          paper: isDark ? '#1E1E1E' : '#F8FAFC',
        },
        text: {
          primary: isDark ? '#FFFFFF' : '#0F172A',
          secondary: isDark ? '#98989D' : '#475569',
        },
        divider: isDark ? '#2C2C2E' : '#CBD5E1',
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
              border: isDark ? '1px solid #2C2C2E' : '1px solid #CBD5E1',
              backgroundColor: isDark ? '#1E1E1E' : '#F8FAFC',
              boxShadow: isDark ? '0 4px 20px rgba(0, 0, 0, 0.35)' : '0 2px 12px rgba(15, 23, 42, 0.05)',
            },
          },
        },
        MuiPaper: {
          styleOverrides: {
            root: {
              backgroundImage: 'none',
              backgroundColor: isDark ? '#1E1E1E' : '#F8FAFC',
              border: isDark ? '1px solid #2C2C2E' : '1px solid #CBD5E1',
            },
          },
        },
        MuiTableCell: {
          styleOverrides: {
            root: {
              borderBottom: isDark ? '1px solid #2C2C2E' : '1px solid #E2E8F0',
              color: isDark ? '#FFFFFF' : '#0F172A',
            },
            head: {
              backgroundColor: isDark ? '#181818' : '#F8FAFC',
              color: isDark ? '#98989D' : '#64748B',
              fontWeight: 700,
              fontSize: '0.75rem',
              textTransform: 'uppercase',
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
        MuiSelect: {
          defaultProps: {
            MenuProps: {
              anchorOrigin: {
                vertical: 'bottom',
                horizontal: 'left',
              },
              transformOrigin: {
                vertical: 'top',
                horizontal: 'left',
              },
              autoFocus: false,
              disableAutoFocusItem: true,
              disableRestoreFocus: true,
            },
          },
        },
        MuiMenu: {
          defaultProps: {
            autoFocus: false,
            disableAutoFocusItem: true,
            disableRestoreFocus: true,
            anchorOrigin: {
              vertical: 'bottom',
              horizontal: 'left',
            },
            transformOrigin: {
              vertical: 'top',
              horizontal: 'left',
            },
          },
          styleOverrides: {
            paper: {
              backgroundColor: isDark ? '#1E1E1E' : '#FFFFFF',
              border: isDark ? '1px solid #2C2C2E' : '1px solid #E2E8F0',
              boxShadow: isDark ? '0 10px 30px rgba(0,0,0,0.5)' : '0 10px 30px rgba(0,0,0,0.08)',
            },
          },
        },
        MuiPopover: {
          defaultProps: {
            disableRestoreFocus: true,
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
