import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, 
  User, 
  LogOut, 
  ChevronDown, 
  Settings, 
  CheckCircle2, 
  RefreshCw, 
  Bell, 
  Zap,
  Moon,
  Building2,
  Palette,
  Sun,
  Info
} from 'lucide-react';
import { Tooltip, IconButton } from '@mui/material';
import { useTheme } from '../ThemeContext';
import { useAuth } from '../context/AuthContext';

export default function Header({ 
  onRunAllCycles, 
  isRunningAll, 
  activeModuleTitle,
  streamConnected = false,
  concurrencyStats = null,
}) {
  const [profileOpen, setProfileOpen] = useState(false);
  const dropdownRef = useRef(null);
  const { theme, toggleTheme, currentTheme, isEnterprise } = useTheme();
  const { user, logout } = useAuth();

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setProfileOpen(false);
    await logout();
  };

  return (
    <header style={{
      height: '68px',
      borderBottom: '1px solid var(--header-border, rgba(255, 255, 255, 0.08))',
      background: 'var(--header-bg, rgba(7, 10, 19, 0.85))',
      backdropFilter: 'blur(16px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 28px',
      position: 'sticky',
      top: 0,
      zIndex: 15,
      transition: 'background 0.2s ease, border-color 0.2s ease',
    }}>
      {/* Active Module Title with Info Tooltip */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <h1 style={{ 
          fontSize: '1.25rem', 
          fontWeight: '800', 
          color: isEnterprise ? '#0F172A' : '#ffffff', 
          letterSpacing: '-0.02em', 
          margin: 0 
        }}>
          {activeModuleTitle}
        </h1>
        {activeModuleTitle === 'Event WatchDog' && (
          <Tooltip title="Automated signal rule evaluators dispatching alerts to Telegram, WhatsApp, and Webhooks without trade execution." arrow>
            <IconButton size="small" sx={{ color: isEnterprise ? '#64748B' : 'rgba(255,255,255,0.6)', p: 0.5 }}>
              <Info size={18} />
            </IconButton>
          </Tooltip>
        )}
      </div>

      {/* Right Controls: Telemetry, Theme Switcher, Quick Cycle Runner & User Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        
        {/* Real-time SSE Telemetry & Concurrency Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          borderRadius: '8px',
          background: isEnterprise ? '#F1F5F9' : 'rgba(15, 23, 42, 0.65)',
          border: isEnterprise ? '1px solid #E2E8F0' : '1px solid rgba(255, 255, 255, 0.15)',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono, monospace)',
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: streamConnected ? (isEnterprise ? '#16A34A' : '#10b981') : '#d97706',
            boxShadow: streamConnected ? (isEnterprise ? '0 0 8px #16A34A' : '0 0 8px #10b981') : '0 0 6px #d97706',
            display: 'inline-block',
          }}></span>
          <span style={{ color: streamConnected ? (isEnterprise ? '#16A34A' : '#10b981') : '#d97706', fontWeight: '700' }}>
            {streamConnected ? 'LIVE STREAM' : 'CONNECTING...'}
          </span>
          {concurrencyStats && (
            <>
              <span style={{ color: isEnterprise ? '#CBD5E1' : 'rgba(255, 255, 255, 0.25)' }}>|</span>
              <span style={{ color: isEnterprise ? '#64748B' : '#E2E8F0', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Zap style={{ width: '12px', height: '12px', color: isEnterprise ? '#2563EB' : '#a855f7' }} />
                <span>Threads: <strong style={{ color: isEnterprise ? '#0F172A' : '#ffffff' }}>{concurrencyStats.total_max_workers || 8}</strong></span>
              </span>
            </>
          )}
        </div>

        {/* Quick Theme Switcher Icon Button */}
        <Tooltip title={`Current Theme: ${currentTheme?.name || (isEnterprise ? 'Institutional Light' : 'Institutional Dark')} (Click to switch)`}>
          <IconButton
            onClick={toggleTheme}
            size="small"
            sx={{
              width: 36,
              height: 36,
              borderRadius: 2,
              bgcolor: isEnterprise ? '#F1F5F9' : 'rgba(15, 23, 42, 0.65)',
              border: isEnterprise ? '1px solid #E2E8F0' : '1px solid rgba(255, 255, 255, 0.18)',
              color: isEnterprise ? '#0F172A' : '#ffffff',
              transition: 'all 0.15s ease',
              '&:hover': {
                bgcolor: isEnterprise ? '#E2E8F0' : 'rgba(30, 41, 59, 0.9)',
              },
            }}
          >
            {isEnterprise ? (
              <Sun style={{ width: 16, height: 16, color: '#D97706' }} />
            ) : (
              <Moon style={{ width: 16, height: 16, color: '#60a5fa' }} />
            )}
          </IconButton>
        </Tooltip>

        {/* Run All Active Algos (Purple Execution Button) */}
        <button
          onClick={onRunAllCycles}
          disabled={isRunningAll}
          className="btn btn-execute"
          style={{ 
            opacity: isRunningAll ? 0.7 : 1,
          }}
        >
          {isRunningAll ? (
            <>
              <RefreshCw style={{ width: '16px', height: '16px', animation: 'spin 1s linear infinite' }} />
              <span>Scanning All...</span>
            </>
          ) : (
            <>
              <Play style={{ width: '16px', height: '16px', fill: '#ffffff' }} />
              <span>Scan Active Algos</span>
            </>
          )}
        </button>

        {/* User Profile View & Logout Dropdown (Top Right) */}
        <div style={{ position: 'relative' }} ref={dropdownRef}>
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '5px 12px 5px 6px',
              borderRadius: '999px',
              background: isEnterprise ? '#F1F5F9' : (profileOpen ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.12)'),
              border: isEnterprise ? '1.5px solid #E2E8F0' : '1.5px solid rgba(255, 255, 255, 0.35)',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {/* User Cash Balance Pill */}
            {user && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                marginRight: '6px',
                background: isEnterprise ? 'rgba(22, 163, 74, 0.1)' : 'rgba(34, 197, 94, 0.15)',
                border: isEnterprise ? '1px solid rgba(22, 163, 74, 0.3)' : '1px solid rgba(34, 197, 94, 0.3)',
                borderRadius: '8px',
              }}>
                <span style={{ fontSize: '0.68rem', color: isEnterprise ? '#16A34A' : '#4ade80', fontWeight: '700' }}>
                  ₹{Number(user.cash_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
            )}

            {/* Avatar Pill */}
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: isEnterprise 
                ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' 
                : 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              fontWeight: '700',
              fontSize: '0.8rem',
              boxShadow: isEnterprise 
                ? '0 2px 8px rgba(37, 99, 235, 0.3)' 
                : '0 2px 8px rgba(168, 85, 247, 0.35)',
            }}>
              {(user?.username || 'AT').substring(0, 2).toUpperCase()}
            </div>
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '700', color: isEnterprise ? '#0F172A' : '#ffffff', lineHeight: 1.2 }}>
                {user?.username || 'Trader'}
              </div>
              <div style={{ fontSize: '0.68rem', color: isEnterprise ? '#64748B' : '#cbd5e1' }}>
                {user?.role?.name || user?.role || 'TRADER'}
              </div>
            </div>
            <ChevronDown style={{ width: '14px', height: '14px', color: isEnterprise ? '#64748B' : '#ffffff', transform: profileOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
          </button>

          {/* Profile Dropdown Menu */}
          {profileOpen && (
            <div style={{
              position: 'absolute',
              top: '48px',
              right: '0',
              width: '235px',
              background: isEnterprise ? '#FFFFFF' : 'rgba(15, 23, 42, 0.96)',
              backdropFilter: 'blur(20px)',
              border: isEnterprise ? '1px solid #E2E8F0' : '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '14px',
              boxShadow: isEnterprise ? '0 12px 35px rgba(0, 0, 0, 0.08)' : '0 12px 35px rgba(0, 0, 0, 0.5)',
              padding: '8px',
              zIndex: 50,
            }}>
              <div style={{ 
                padding: '8px 12px', 
                borderBottom: isEnterprise ? '1px solid #E2E8F0' : '1px solid rgba(255, 255, 255, 0.08)', 
                marginBottom: '6px' 
              }}>
                <p style={{ fontSize: '0.82rem', fontWeight: '700', color: isEnterprise ? '#0F172A' : '#ffffff', margin: 0 }}>
                  {user?.username || 'AuraTrade User'}
                </p>
                <p style={{ fontSize: '0.72rem', color: isEnterprise ? '#64748B' : '#94a3b8', margin: '2px 0 0 0' }}>
                  {user?.email || 'authenticated'}
                </p>
              </div>

              {/* Theme Settings Selector */}
              <button
                onClick={() => {
                  setProfileOpen(false);
                  setIsThemeModalOpen(true);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  fontWeight: '600',
                  color: isEnterprise ? '#0F172A' : '#cbd5e1',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = isEnterprise ? '#F8FAFC' : 'rgba(255, 255, 255, 0.06)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <Palette style={{ width: '15px', height: '15px', color: isEnterprise ? '#2563EB' : '#a855f7' }} />
                <span>Theme Settings</span>
                <span style={{ 
                  marginLeft: 'auto', 
                  fontSize: '0.68rem', 
                  padding: '1px 6px', 
                  borderRadius: '10px', 
                  background: isEnterprise ? 'rgba(37, 99, 235, 0.1)' : 'rgba(168, 85, 247, 0.2)',
                  color: isEnterprise ? '#2563EB' : '#c084fc',
                  fontWeight: '700'
                }}>
                  {isEnterprise ? 'LIGHT' : 'DARK'}
                </span>
              </button>

              <button
                onClick={() => { setProfileOpen(false); alert("User Profile settings modal."); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  color: isEnterprise ? '#0F172A' : '#cbd5e1',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = isEnterprise ? '#F8FAFC' : 'rgba(255, 255, 255, 0.06)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <User style={{ width: '14px', height: '14px', color: '#38bdf8' }} />
                <span>Profile Settings</span>
              </button>

              <button
                onClick={() => { setProfileOpen(false); alert("Strategy notification endpoints."); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  color: isEnterprise ? '#0F172A' : '#cbd5e1',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = isEnterprise ? '#F8FAFC' : 'rgba(255, 255, 255, 0.06)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <Settings style={{ width: '14px', height: '14px', color: '#94a3b8' }} />
                <span>Strategy Endpoints</span>
              </button>

              <div style={{ height: '1px', background: isEnterprise ? '#E2E8F0' : 'rgba(255, 255, 255, 0.08)', margin: '6px 0' }}></div>

              {/* Log Out Option */}
              <button
                onClick={handleLogout}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  fontWeight: '600',
                  color: '#DC2626',
                  background: isEnterprise ? '#FEF2F2' : 'rgba(239, 68, 68, 0.1)',
                  border: isEnterprise ? '1px solid #FECACA' : '1px solid rgba(239, 68, 68, 0.2)',
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = isEnterprise ? '#FEE2E2' : 'rgba(239, 68, 68, 0.2)'}
                onMouseLeave={(e) => e.currentTarget.style.background = isEnterprise ? '#FEF2F2' : 'rgba(239, 68, 68, 0.1)'}
              >
                <LogOut style={{ width: '14px', height: '14px', color: '#DC2626' }} />
                <span>Log Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
