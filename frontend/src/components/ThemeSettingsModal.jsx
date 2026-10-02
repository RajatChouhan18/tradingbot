import React from 'react';
import { useTheme } from '../ThemeContext';
import { Check, X, Moon, Sun, Layers, Sparkles, Building2, Terminal } from 'lucide-react';

export default function ThemeSettingsModal() {
  const { theme, setTheme, themes, isThemeModalOpen, setIsThemeModalOpen } = useTheme();

  if (!isThemeModalOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '16px',
        animation: 'fadeIn 0.15s ease',
      }}
      onClick={() => setIsThemeModalOpen(false)}
    >
      <div
        className="glass-panel"
        style={{
          width: '740px',
          maxWidth: '96vw',
          maxHeight: '90vh',
          overflowY: 'auto',
          borderRadius: '16px',
          padding: '28px',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.45)',
          border: '1px solid var(--border-color)',
          background: 'var(--bg-card)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  background: 'var(--accent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                }}
              >
                <Sparkles style={{ width: '20px', height: '20px' }} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: '800', margin: 0 }}>
                  Platform Appearance & Themes
                </h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
                  Select an interface aesthetic tailored for your trading workflow.
                </p>
              </div>
            </div>
          </div>
          <button
            onClick={() => setIsThemeModalOpen(false)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <X style={{ width: '20px', height: '20px' }} />
          </button>
        </div>

        {/* Theme Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))', gap: '18px', marginBottom: '24px' }}>
          {themes.map((t) => {
            const isSelected = theme === t.id;
            return (
              <div
                key={t.id}
                onClick={() => setTheme(t.id)}
                style={{
                  padding: '20px',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  border: isSelected
                    ? '2px solid var(--accent)'
                    : '1px solid var(--border-color)',
                  background: isSelected
                    ? 'var(--bg-card-hover)'
                    : 'var(--bg-input)',
                  boxShadow: isSelected ? '0 8px 24px rgba(0, 0, 0, 0.15)' : 'none',
                  transition: 'all 0.2s ease',
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  {/* Top Header inside card */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {t.id === 'obsidian' ? (
                        <Moon style={{ width: '18px', height: '18px', color: '#60a5fa' }} />
                      ) : (
                        <Sun style={{ width: '18px', height: '18px', color: '#D97706' }} />
                      )}
                      <span style={{ fontWeight: '800', fontSize: '1rem', color: 'var(--text-main)' }}>
                        {t.name}
                      </span>
                    </div>
                    <span
                      style={{
                        fontSize: '0.6875rem',
                        fontWeight: '700',
                        padding: '2px 8px',
                        borderRadius: '20px',
                        background: isSelected ? 'var(--bullish-dim)' : 'rgba(100, 116, 139, 0.15)',
                        color: isSelected ? 'var(--bullish)' : 'var(--text-muted)',
                        border: isSelected ? '1px solid var(--bullish-border)' : '1px solid transparent',
                      }}
                    >
                      {isSelected ? 'ACTIVE' : t.badge}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '14px', lineHeight: 1.45 }}>
                    {t.tagline}
                  </p>

                  {/* Palette Swatches */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: '600' }}>Palette:</span>
                    <span title="Background" style={{ width: '16px', height: '16px', borderRadius: '50%', background: t.colors.bg, border: '1px solid #718096', display: 'inline-block' }}></span>
                    <span title="Surface Card" style={{ width: '16px', height: '16px', borderRadius: '50%', background: t.colors.card, border: '1px solid #718096', display: 'inline-block' }}></span>
                    <span title="Primary Accent" style={{ width: '16px', height: '16px', borderRadius: '50%', background: t.colors.primary, display: 'inline-block' }}></span>
                    <span title="Bullish" style={{ width: '16px', height: '16px', borderRadius: '50%', background: t.colors.bullish, display: 'inline-block' }}></span>
                    <span title="Bearish" style={{ width: '16px', height: '16px', borderRadius: '50%', background: t.colors.bearish, display: 'inline-block' }}></span>
                  </div>

                  {/* Mini Preview Box */}
                  <div
                    style={{
                      borderRadius: '8px',
                      padding: '12px',
                      background: t.colors.bg,
                      border: '1px solid rgba(120, 120, 120, 0.25)',
                      marginBottom: '16px',
                    }}
                  >
                    <div
                      style={{
                        background: t.colors.card,
                        padding: '10px 12px',
                        borderRadius: '6px',
                        border: '1px solid rgba(120, 120, 120, 0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '0.72rem', fontWeight: '700', color: t.colors.text }}>
                          RELIANCE 5m
                        </div>
                        <div style={{ fontSize: '0.62rem', color: t.colors.bullish, fontWeight: '600' }}>
                          +2.45% (Bullish Engulfing)
                        </div>
                      </div>
                      <div
                        style={{
                          fontSize: '0.62rem',
                          fontWeight: '700',
                          padding: '3px 8px',
                          borderRadius: '20px',
                          background: t.colors.bullish,
                          color: '#ffffff',
                        }}
                      >
                        CALL
                      </div>
                    </div>
                  </div>
                </div>

                {/* Selection Button */}
                <button
                  onClick={() => setTheme(t.id)}
                  style={{
                    width: '100%',
                    padding: '8px 14px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: '700',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    background: isSelected ? 'var(--accent)' : 'transparent',
                    color: isSelected ? '#ffffff' : 'var(--text-muted)',
                    border: isSelected ? 'none' : '1px solid var(--border-color)',
                  }}
                >
                  {isSelected ? (
                    <>
                      <Check style={{ width: '14px', height: '14px' }} />
                      <span>Current Theme</span>
                    </>
                  ) : (
                    <span>Activate Theme</span>
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {/* Footer note & Close */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', margin: 0 }}>
            Theme preference is automatically saved to your browser session.
          </p>
          <button
            onClick={() => setIsThemeModalOpen(false)}
            className="btn btn-execute"
            style={{ padding: '8px 22px' }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
