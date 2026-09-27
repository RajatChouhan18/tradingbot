import React from 'react';
import { 
  LayoutDashboard, 
  Zap, 
  Radio, 
  LineChart, 
  ShieldCheck, 
  ScrollText, 
  Layers,
  Activity,
  Flame
} from 'lucide-react';

export default function Sidebar({ currentModule, onSelectModule, systemStatus, algosCount, signalsCount }) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, badge: null },
    { id: 'algotrade', label: 'AlgoTrade', icon: Zap, badge: algosCount || null, badgeColor: 'bg-purple-500/20 text-purple-300' },
    { id: 'signals', label: 'Signals & PnL', icon: Radio, badge: signalsCount || null, badgeColor: 'bg-emerald-500/20 text-emerald-300' },
    { id: 'market', label: 'Market Data', icon: LineChart, badge: null },
    { id: 'auditing', label: 'Auditing', icon: ShieldCheck, badge: null },
    { id: 'logging', label: 'Logging', icon: ScrollText, badge: null },
  ];

  const session = systemStatus?.session || {};
  const vix = systemStatus?.vix || {};
  const isMarketOpen = session?.is_trading;

  return (
    <aside style={{ width: '270px', minWidth: '270px', height: '100vh' }} className="glass-panel flex flex-col justify-between p-5 border-r border-slate-800/80 bg-slate-950/80 sticky top-0 z-20">
      <div>
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-3 px-2 py-4 mb-6 border-b border-slate-800/60">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-blue-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-wider text-white">TxBot</span>
              <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">v3.0</span>
            </div>
            <p className="text-xs text-slate-400 font-medium">AlgoTrade Engine</p>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="space-y-1.5">
          <div className="px-3 mb-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Trading Modules
          </div>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentModule === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectModule(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  width: '100%',
                  padding: '11px 14px',
                  borderRadius: '12px',
                  fontSize: '0.875rem',
                  fontWeight: isActive ? '700' : '500',
                  color: isActive ? '#ffffff' : '#94a3b8',
                  background: isActive ? 'linear-gradient(135deg, rgba(147, 51, 234, 0.25) 0%, rgba(99, 102, 241, 0.15) 100%)' : 'transparent',
                  border: isActive ? '1px solid rgba(168, 85, 247, 0.35)' : '1px solid transparent',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  textAlign: 'left'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon style={{ width: '18px', height: '18px', color: isActive ? '#c084fc' : '#64748b' }} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span style={{ fontSize: '11px', padding: '2px 7px', borderRadius: '999px', background: isActive ? 'rgba(192, 132, 252, 0.25)' : 'rgba(51, 65, 85, 0.6)', color: isActive ? '#f3e8ff' : '#cbd5e1', fontWeight: 600 }}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Live Market Status Widget */}
      <div style={{ padding: '14px', borderRadius: '14px', background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: isMarketOpen ? '#10b981' : '#f43f5e', display: 'inline-block', boxShadow: isMarketOpen ? '0 0 8px #10b981' : '0 0 8px #f43f5e' }}></span>
            <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: isMarketOpen ? '#34d399' : '#fb7185' }}>
              {session.market_state || 'MARKET'}
            </span>
          </div>
          <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'monospace' }}>
            {session.current_time || 'IST'}
          </span>
        </div>

        <div style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#94a3b8' }}>India VIX:</span>
          <span style={{ fontWeight: '700', color: vix.regime === 'NORMAL' ? '#38bdf8' : vix.regime === 'LOW' ? '#94a3b8' : '#f87171' }}>
            {vix.value ? vix.value.toFixed(2) : '14.20'} ({vix.regime || 'NORMAL'})
          </span>
        </div>

        {session.minutes_to_close !== null && isMarketOpen && (
          <div style={{ fontSize: '11px', color: '#94a3b8', display: 'flex', justifyContent: 'space-between' }}>
            <span>Time to Close:</span>
            <span style={{ color: '#f8fafc', fontWeight: '600' }}>{session.minutes_to_close} mins</span>
          </div>
        )}
      </div>
    </aside>
  );
}
