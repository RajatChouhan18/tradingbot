import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('auratrade_token') || null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const res = await api.getMe();
      if (res && res.user) {
        setUser(res.user);
        return res.user;
      }
    } catch (err) {
      console.warn('Session verification failed:', err.message);
      localStorage.removeItem('auratrade_token');
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
    return null;
  }, []);

  useEffect(() => {
    if (token) {
      refreshUser();
    } else {
      setIsLoading(false);
    }
  }, [token, refreshUser]);

  const login = async (identifier, password) => {
    const res = await api.login(identifier, password);
    if (res && res.success && res.token) {
      localStorage.setItem('auratrade_token', res.token);
      setToken(res.token);
      setUser(res.user);
      return res.user;
    }
    throw new Error('Login failed: Token not returned.');
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (e) {
      console.error('Logout error:', e);
    } finally {
      localStorage.removeItem('auratrade_token');
      setToken(null);
      setUser(null);
    }
  };

  const hasPermission = (moduleKey, action = 'view') => {
    if (!user) return false;
    if (user.role === 'ADMIN') return true;
    if (!user.permissions || !user.permissions[moduleKey]) return false;
    const perm = user.permissions[moduleKey];
    if (action === 'view') return !!perm.can_view;
    if (action === 'edit') return !!perm.can_edit;
    if (action === 'delete') return !!perm.can_delete;
    return false;
  };

  const value = {
    user,
    token,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    refreshUser,
    hasPermission,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
