import React, { useState, useEffect, useRef } from 'react';
import { 
  LayoutDashboard, 
  Zap, 
  Radio, 
  LineChart, 
  ShieldCheck, 
  ScrollText, 
  Layers, 
  Activity, 
  Building2, 
  Sliders,
  Menu,
} from 'lucide-react';
import { 
  Box, 
  Typography, 
  Tooltip, 
  IconButton, 
  List, 
  ListItem, 
  ListItemButton, 
  ListItemIcon, 
  ListItemText,
  Badge,
  Chip
} from '@mui/material';
import { useTheme } from '../ThemeContext';
import { useAuth } from '../context/AuthContext';

export default function Sidebar({ 
  currentModule, 
  onSelectModule, 
  systemStatus, 
  algosCount, 
  signalsCount, 
  openPositionsCount = 0 
}) {
  const { isEnterprise } = useTheme();
  const { hasPermission } = useAuth();

  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      return localStorage.getItem('auratrade_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const [sidebarWidth, setSidebarWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('auratrade_sidebar_width');
      return saved ? parseInt(saved, 10) : 155;
    } catch {
      return 155;
    }
  });

  const [isResizing, setIsResizing] = useState(false);

  // Drag resize handler
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      const newWidth = Math.max(130, Math.min(340, e.clientX));
      setSidebarWidth(newWidth);
      try {
        localStorage.setItem('auratrade_sidebar_width', String(newWidth));
      } catch {}
    };

    const handleMouseUp = () => {
      if (isResizing) {
        setIsResizing(false);
      }
    };

    if (isResizing) {
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    } else {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('auratrade_sidebar_collapsed', String(next));
      } catch {}
      return next;
    });
  };

  const allMenuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, badge: null, moduleKey: null },
    { id: 'market', label: 'MarketView', icon: LineChart, badge: null, moduleKey: 'MARKETVIEW' },
    { id: 'terminal_config', label: 'Terminal Config', icon: Sliders, badge: null, moduleKey: 'MARKETVIEW' },
    { id: 'events', label: 'Event WatchDog', icon: Radio, badge: null, moduleKey: 'EVENT_TRIGGERS' },
    { id: 'algotrade', label: 'AlgoTrade', icon: Zap, badge: algosCount || null, moduleKey: 'ALGOTRADE' },
    { id: 'paper', label: 'Paper Trading', icon: Activity, badge: openPositionsCount || null, moduleKey: 'PAPER_TRADING' },
    { id: 'catalog', label: 'Market Catalog', icon: Layers, badge: null, moduleKey: 'CATALOG' },
    { id: 'auditing', label: 'Auditing', icon: ShieldCheck, badge: null, moduleKey: null },
    { id: 'logging', label: 'Logging', icon: ScrollText, badge: null, moduleKey: null },
    { id: 'users', label: 'User & Roles', icon: Building2, badge: null, moduleKey: 'USER_MANAGEMENT' },
  ];

  const menuItems = allMenuItems.filter((item) => {
    if (!item.moduleKey) return true;
    return hasPermission(item.moduleKey, 'view');
  });

  const session = systemStatus?.session || {};
  const vix = systemStatus?.vix || {};
  const isMarketOpen = session?.is_trading;

  const currentWidth = isCollapsed ? 58 : sidebarWidth;

  return (
    <Box
      component="aside"
      sx={{
        width: currentWidth,
        minWidth: currentWidth,
        maxWidth: isCollapsed ? 58 : 340,
        height: '100vh',
        bgcolor: isEnterprise ? '#FFFFFF' : '#121212',
        borderRight: `1px solid ${isEnterprise ? '#E2E8F0' : '#2C2C2E'}`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        p: 1.2,
        position: 'sticky',
        top: 0,
        zIndex: 20,
        userSelect: 'none',
        transition: isResizing ? 'none' : 'width 0.2s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      <Box>
        {/* Brand Header with Centered AuraTrade Title & Side Hamburger Icon */}
        {!isCollapsed ? (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              px: 0.2,
              py: 0.8,
              mb: 1.2,
              borderBottom: `1px solid ${isEnterprise ? '#E2E8F0' : '#2C2C2E'}`,
            }}
          >
            <Tooltip title="Collapse sidebar" placement="bottom">
              <IconButton
                size="small"
                onClick={toggleCollapse}
                sx={{
                  p: 0.4,
                  color: isEnterprise ? '#64748B' : '#98989D',
                  borderRadius: 1.2,
                  '&:hover': { color: isEnterprise ? '#0F172A' : '#ffffff', bgcolor: isEnterprise ? '#F1F5F9' : 'rgba(255,255,255,0.08)' }
                }}
              >
                <Menu size={15} />
              </IconButton>
            </Tooltip>

            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, pr: 1.5 }}>
              <Typography
                variant="subtitle1"
                sx={{
                  fontWeight: 800,
                  fontSize: '1.25rem',
                  color: isEnterprise ? '#0F172A' : '#ffffff',
                  letterSpacing: '-0.02em',
                  textAlign: 'center',
                }}
              >
                AuraTrade
              </Typography>
            </Box>
          </Box>
        ) : (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              py: 0.8,
              mb: 1.2,
              gap: 0.5,
              borderBottom: `1px solid ${isEnterprise ? '#E2E8F0' : '#2C2C2E'}`,
            }}
          >
            <Tooltip title="Expand sidebar" placement="right">
              <IconButton
                size="small"
                onClick={toggleCollapse}
                sx={{
                  p: 0.4,
                  color: isEnterprise ? '#64748B' : '#98989D',
                  borderRadius: 1.2,
                  '&:hover': { color: isEnterprise ? '#0F172A' : '#ffffff', bgcolor: isEnterprise ? '#F1F5F9' : 'rgba(255,255,255,0.08)' }
                }}
              >
                <Menu size={15} />
              </IconButton>
            </Tooltip>
          </Box>
        )}

        {/* MUI-Enhanced Navigation List (Compact sized options) */}
        <List sx={{ p: 0, display: 'flex', flexDirection: 'column', gap: 0.2 }}>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentModule === item.id;

            const activeBg = isEnterprise ? '#EFF6FF' : '#2563EB';
            const activeColor = isEnterprise ? '#2563EB' : '#ffffff';
            const inactiveColor = isEnterprise ? '#64748B' : '#98989D';
            const activeIconColor = isEnterprise ? '#2563EB' : '#ffffff';
            const inactiveIconColor = isEnterprise ? '#64748B' : '#98989D';

            return (
              <ListItem key={item.id} disablePadding sx={{ display: 'block' }}>
                <Tooltip 
                  title={isCollapsed ? item.label : ''} 
                  placement="right" 
                  arrow
                  disableHoverListener={!isCollapsed}
                >
                  <ListItemButton
                    onClick={() => onSelectModule(item.id)}
                    sx={{
                      minHeight: 26,
                      justifyContent: isCollapsed ? 'center' : 'initial',
                      px: isCollapsed ? 0.7 : 0.8,
                      py: 0.35,
                      borderRadius: 1.2,
                      bgcolor: isActive ? activeBg : 'transparent',
                      color: isActive ? activeColor : inactiveColor,
                      transition: 'all 0.12s ease',
                      '&:hover': {
                        bgcolor: isActive 
                          ? activeBg 
                          : isEnterprise 
                            ? '#F8FAFC' 
                            : 'rgba(255, 255, 255, 0.05)',
                        color: isActive ? activeColor : isEnterprise ? '#0F172A' : '#ffffff',
                      },
                    }}
                  >
                    <ListItemIcon
                      sx={{
                        minWidth: 0,
                        mr: isCollapsed ? 0 : 0.7,
                        justifyContent: 'center',
                        color: isActive ? activeIconColor : inactiveIconColor,
                      }}
                    >
                      <Badge
                        variant="dot"
                        invisible={!isCollapsed || !item.badge}
                        sx={{
                          '& .MuiBadge-badge': {
                            bgcolor: '#2563EB',
                            right: -2,
                            top: -2,
                          }
                        }}
                      >
                        <Icon size={12.5} />
                      </Badge>
                    </ListItemIcon>

                    {!isCollapsed && (
                      <ListItemText
                        primary={item.label}
                        primaryTypographyProps={{
                          fontSize: '0.62rem',
                          fontWeight: isActive ? 700 : 500,
                          noWrap: true,
                        }}
                        sx={{ m: 0 }}
                      />
                    )}

                    {!isCollapsed && item.badge && (
                      <Chip
                        label={item.badge}
                        size="small"
                        sx={{
                          height: 15,
                          fontSize: '0.52rem',
                          fontWeight: 700,
                          fontFamily: 'monospace',
                          bgcolor: isEnterprise 
                            ? (isActive ? 'rgba(37, 99, 235, 0.15)' : '#F1F5F9') 
                            : (isActive ? 'rgba(255, 255, 255, 0.25)' : '#1E1E1E'),
                          color: isEnterprise 
                            ? (isActive ? '#2563EB' : '#64748B') 
                            : (isActive ? '#ffffff' : '#98989D'),
                          border: isEnterprise
                            ? (isActive ? 'none' : '1px solid #E2E8F0')
                            : (isActive ? 'none' : '1px solid #2C2C2E'),
                          '& .MuiChip-label': { px: 0.4 },
                        }}
                      />
                    )}
                  </ListItemButton>
                </Tooltip>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* Live Market Status Widget (MUI Card) */}
      {!isCollapsed ? (
        <Box
          sx={{
            p: 1.2,
            borderRadius: 2,
            bgcolor: isEnterprise ? '#F8FAFC' : '#1E1E1E',
            border: `1px solid ${isEnterprise ? '#E2E8F0' : '#2C2C2E'}`,
            display: 'flex',
            flexDirection: 'column',
            gap: 0.6,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8 }}>
              <Box
                sx={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  bgcolor: isMarketOpen ? (isEnterprise ? '#16A34A' : '#32D74B') : (isEnterprise ? '#DC2626' : '#FF453A'),
                  boxShadow: isMarketOpen 
                    ? (isEnterprise ? '0 0 6px #16A34A' : '0 0 6px #32D74B') 
                    : (isEnterprise ? '0 0 6px #DC2626' : '0 0 6px #FF453A'),
                }}
              />
              <Typography
                sx={{
                  fontSize: '0.72rem',
                  fontWeight: 800,
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                  color: isMarketOpen ? (isEnterprise ? '#16A34A' : '#32D74B') : (isEnterprise ? '#DC2626' : '#FF453A'),
                }}
              >
                {session.market_state || 'MARKET'}
              </Typography>
            </Box>
            <Typography sx={{ fontSize: '0.72rem', color: isEnterprise ? '#64748B' : '#98989D', fontFamily: 'monospace', fontWeight: 600 }}>
              {session.current_time || 'IST'}
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography sx={{ fontSize: '0.74rem', color: isEnterprise ? '#64748B' : '#98989D', fontWeight: 600 }}>India VIX:</Typography>
            <Typography
              sx={{
                fontSize: '0.82rem',
                fontWeight: 800,
                fontFamily: "'JetBrains Mono', monospace",
                color: vix.regime === 'NORMAL' 
                  ? (isEnterprise ? '#16A34A' : '#32D74B') 
                  : vix.regime === 'LOW' 
                    ? (isEnterprise ? '#64748B' : '#98989D') 
                    : (isEnterprise ? '#DC2626' : '#FF453A'),
              }}
            >
              {vix.value ? vix.value.toFixed(2) : '14.20'}
            </Typography>
          </Box>
        </Box>
      ) : (
        <Tooltip 
          title={`${session.market_state || 'MARKET'} • VIX: ${vix.value ? vix.value.toFixed(2) : '14.20'} • ${session.current_time || 'IST'}`} 
          placement="right" 
          arrow
        >
          <Box
            sx={{
              p: 1,
              borderRadius: 2,
              bgcolor: isEnterprise ? '#F8FAFC' : '#1E1E1E',
              border: `1px solid ${isEnterprise ? '#E2E8F0' : '#2C2C2E'}`,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 0.5,
              cursor: 'pointer',
            }}
          >
            <Box
              sx={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                bgcolor: isMarketOpen ? (isEnterprise ? '#16A34A' : '#32D74B') : (isEnterprise ? '#DC2626' : '#FF453A'),
                boxShadow: isMarketOpen 
                  ? (isEnterprise ? '0 0 6px #16A34A' : '0 0 6px #32D74B') 
                  : (isEnterprise ? '0 0 6px #DC2626' : '0 0 6px #FF453A'),
              }}
            />
            <Typography sx={{ fontSize: '0.68rem', color: isEnterprise ? '#64748B' : '#98989D', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}>
              {session.current_time ? session.current_time.slice(0, 5) : 'IST'}
            </Typography>
          </Box>
        </Tooltip>
      )}

      {/* Drag Resize Handle on Right Border */}
      {!isCollapsed && (
        <Box
          onMouseDown={(e) => {
            e.preventDefault();
            setIsResizing(true);
          }}
          sx={{
            position: 'absolute',
            top: 0,
            right: -3,
            width: 6,
            height: '100%',
            cursor: 'col-resize',
            zIndex: 30,
            transition: 'background-color 0.15s ease',
            '&:hover, &:active': {
              bgcolor: '#2563EB',
            },
          }}
        />
      )}
    </Box>
  );
}
