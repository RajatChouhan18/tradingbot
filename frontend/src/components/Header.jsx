import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, 
  User, 
  LogOut, 
  ChevronDown, 
  Settings, 
  CheckCircle2, 
  RefreshCw,
  Bell
} from 'lucide-react';

export default function Header({ onRunAllCycles, isRunningAll, activeModuleTitle }) {
  const [profileOpen, setProfileOpen] = useState(false);
  const [userLogged, setUserLogged] = useState(true);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    setProfileOpen(false);
    setUserLogged(false);
    alert("You have logged out of TxBot AlgoTrade Platform. (Demo session reset)");
    setUserLogged(true);
  };

  return (
    <header style={{
      height: '68px',
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      background: 'rgba(7, 10, 19, 0.85)',
      backdropFilter: 'blur(16px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 28px',
      position: 'sticky',
      top: 0,
      zIndex: 15,
    }}>
      {/* Title & Active Module */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <h1 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#ffffff', letterSpacing: '-0.02em' }}>
          {activeModuleTitle}
        </h1>
        <span style={{ height: '16px', width: '1px', background: 'rgba(255, 255, 255, 0.15)' }}></span>
        <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '500' }}>
          Universal Market Pipeline
        </span>
      </div>

      {/* Right Controls: Quick Cycle Runner & User Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Run All Active Algos (Purple Execution Button) */}
        <button
          onClick={onRunAllCycles}
          disabled={isRunningAll}
          className="btn btn-execute"
          style={{ opacity: isRunningAll ? 0.7 : 1 }}
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
              padding: '6px 12px 6px 6px',
              borderRadius: '999px',
              background: profileOpen ? 'rgba(30, 41, 59, 0.9)' : 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {/* Avatar Pill */}
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              fontWeight: '700',
              fontSize: '0.8rem',
              boxShadow: '0 2px 8px rgba(168, 85, 247, 0.35)',
            }}>
              IT
            </div>
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#f8fafc', lineHeight: 1.2 }}>
                Ishaq Trading
              </div>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
                Pro Trader / Admin
              </div>
            </div>
            <ChevronDown style={{ width: '14px', height: '14px', color: '#94a3b8', transform: profileOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
          </button>

          {/* Profile Dropdown Menu */}
          {profileOpen && (
            <div style={{
              position: 'absolute',
              top: '46px',
              right: '0',
              width: '220px',
              background: 'rgba(15, 23, 42, 0.95)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '14px',
              boxShadow: '0 12px 35px rgba(0, 0, 0, 0.5)',
              padding: '8px',
              zIndex: 50,
            }}>
              <div style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', marginBottom: '6px' }}>
                <p style={{ fontSize: '0.8rem', fontWeight: '700', color: '#ffffff' }}>Ishaq Trading</p>
                <p style={{ fontSize: '0.72rem', color: '#94a3b8' }}>admin@tradingbot.internal</p>
              </div>

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
                  color: '#cbd5e1',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <User style={{ width: '14px', height: '14px', color: '#38bdf8' }} />
                <span>Profile Settings</span>
              </button>

              <button
                onClick={() => { setProfileOpen(false); alert("Notification Preferences."); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  color: '#cbd5e1',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <Settings style={{ width: '14px', height: '14px', color: '#94a3b8' }} />
                <span>Strategy Endpoints</span>
              </button>

              <div style={{ height: '1px', background: 'rgba(255, 255, 255, 0.08)', margin: '6px 0' }}></div>

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
                  color: '#f87171',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
              >
                <LogOut style={{ width: '14px', height: '14px', color: '#f87171' }} />
                <span>Log Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
