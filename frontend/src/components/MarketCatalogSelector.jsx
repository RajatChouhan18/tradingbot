import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Search, Check, X, Layers, ChevronDown, Plus, Sparkles, Building2, TrendingUp, Globe2, Cpu, Flame } from 'lucide-react';
import { api } from '../api';

/**
 * High-Density Institutional Market Catalog & Symbol Multi-Select Component.
 * Supports group-based filtering (NSE, BSE, DOW_JONES, NASDAQ, SP500, FOREX, CRYPTO, MCX),
 * searching by symbol/shortName/fullName, and custom manual symbol write-ins.
 */
export default function MarketCatalogSelector({
  selectedGroup = 'NSE',
  onGroupChange,
  selectedSymbols = [],
  onChangeSymbols,
  isMulti = true,
  placeholder = 'Search stocks, indexes, or currencies...',
  allowCustom = true,
  filterAssetType = null, // 'STOCK', 'INDEX', null (all)
}) {
  const [groups, setGroups] = useState([]);
  const [symbolsInGroup, setSymbolsInGroup] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [activeAssetType, setActiveAssetType] = useState('ALL'); // 'ALL', 'STOCK', 'INDEX'
  const containerRef = useRef(null);

  // 1. Fetch all market groups on mount
  useEffect(() => {
    let isMounted = true;
    api.getCatalogGroups()
      .then((data) => {
        if (isMounted && Array.isArray(data) && data.length > 0) {
          setGroups(data);
        }
      })
      .catch((err) => console.error('Failed to load catalog groups:', err));
    return () => { isMounted = false; };
  }, []);

  // 2. Fetch symbols whenever selectedGroup changes
  useEffect(() => {
    if (!selectedGroup) return;
    let isMounted = true;
    setLoading(true);
    api.getCatalogSymbols({ group: selectedGroup, limit: 150 })
      .then((data) => {
        if (isMounted && Array.isArray(data)) {
          setSymbolsInGroup(data);
        }
      })
      .catch((err) => console.error(`Failed to load symbols for group ${selectedGroup}:`, err))
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => { isMounted = false; };
  }, [selectedGroup]);

  // Click outside listener to close dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter symbols by search query and asset type
  const filteredSymbols = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return symbolsInGroup.filter((s) => {
      if (filterAssetType && s.assetType !== filterAssetType) return false;
      if (activeAssetType !== 'ALL' && s.assetType !== activeAssetType) return false;
      if (!q) return true;
      return (
        s.symbol.toLowerCase().includes(q) ||
        (s.shortName && s.shortName.toLowerCase().includes(q)) ||
        (s.fullName && s.fullName.toLowerCase().includes(q)) ||
        (s.sector && s.sector.toLowerCase().includes(q))
      );
    });
  }, [symbolsInGroup, searchQuery, activeAssetType, filterAssetType]);

  // Asset type counts in current group
  const assetCounts = useMemo(() => {
    const counts = { ALL: symbolsInGroup.length, STOCK: 0, INDEX: 0, CURRENCY: 0, CRYPTO: 0, COMMODITY: 0 };
    symbolsInGroup.forEach((s) => {
      if (counts[s.assetType] !== undefined) counts[s.assetType]++;
    });
    return counts;
  }, [symbolsInGroup]);

  // Toggle or select a symbol
  const handleSelectSymbol = (sym) => {
    const targetSymbol = sym.symbol.toUpperCase();
    if (isMulti) {
      if (selectedSymbols.includes(targetSymbol)) {
        onChangeSymbols(selectedSymbols.filter((s) => s !== targetSymbol));
      } else {
        onChangeSymbols([...selectedSymbols, targetSymbol]);
      }
    } else {
      onChangeSymbols([targetSymbol]);
      setIsOpen(false);
    }
  };

  const handleRemoveSymbol = (symToRemove) => {
    onChangeSymbols(selectedSymbols.filter((s) => s !== symToRemove));
  };

  const handleAddCustomSymbol = () => {
    const clean = searchQuery.trim().toUpperCase();
    if (!clean) return;
    if (isMulti) {
      if (!selectedSymbols.includes(clean)) {
        onChangeSymbols([...selectedSymbols, clean]);
      }
    } else {
      onChangeSymbols([clean]);
      setIsOpen(false);
    }
    setSearchQuery('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredSymbols.length > 0) {
        handleSelectSymbol(filteredSymbols[0]);
      } else if (allowCustom && searchQuery.trim()) {
        handleAddCustomSymbol();
      }
    }
  };

  const handleSelectAllInGroup = () => {
    const allSyms = filteredSymbols.map((s) => s.symbol.toUpperCase());
    const merged = Array.from(new Set([...selectedSymbols, ...allSyms]));
    onChangeSymbols(merged);
  };

  const handleClearAll = () => {
    onChangeSymbols([]);
  };

  // Group Icon helper
  const getGroupIcon = (groupId) => {
    switch (groupId) {
      case 'NSE':
      case 'BSE':
        return <Building2 style={{ width: '13px', height: '13px', color: '#10b981' }} />;
      case 'DOW_JONES':
      case 'NASDAQ':
      case 'SP500':
        return <TrendingUp style={{ width: '13px', height: '13px', color: '#3b82f6' }} />;
      case 'FOREX':
        return <Globe2 style={{ width: '13px', height: '13px', color: '#f59e0b' }} />;
      case 'CRYPTO':
        return <Cpu style={{ width: '13px', height: '13px', color: '#c084fc' }} />;
      case 'MCX':
        return <Flame style={{ width: '13px', height: '13px', color: '#ef4444' }} />;
      default:
        return <Layers style={{ width: '13px', height: '13px' }} />;
    }
  };

  return (
    <div ref={containerRef} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* 1. Market Group Tabs / Dropdown */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflowX: 'auto', paddingBottom: '4px' }}>
          {groups.map((grp) => {
            const isSelected = grp.groupId === selectedGroup;
            return (
              <button
                type="button"
                key={grp.groupId}
                onClick={() => {
                  if (onGroupChange) onGroupChange(grp.groupId, grp.market);
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 10px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: isSelected ? '700' : '500',
                  background: isSelected ? 'var(--accent-dim)' : 'var(--bg-secondary)',
                  color: isSelected ? '#60a5fa' : 'var(--text-muted)',
                  border: isSelected ? '1px solid var(--accent-border)' : '1px solid var(--border-color)',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease',
                }}
                title={grp.description || grp.name}
              >
                {getGroupIcon(grp.groupId)}
                <span>{grp.groupId}</span>
                <span style={{ fontSize: '0.6875rem', opacity: 0.65 }}>({grp.symbolCount})</span>
              </button>
            );
          })}
        </div>

        {/* Quick Batch Actions for Multi-Select */}
        {isMulti && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              type="button"
              onClick={handleSelectAllInGroup}
              style={{
                background: 'none',
                border: 'none',
                color: '#60a5fa',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: '600',
                padding: '2px 6px',
              }}
            >
              + Add All ({filteredSymbols.length})
            </button>
            <span style={{ color: 'var(--border-color)' }}>|</span>
            <button
              type="button"
              onClick={handleClearAll}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-dim)',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: '600',
                padding: '2px 6px',
              }}
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* 2. Selected Pills Tray */}
      {selectedSymbols.length > 0 && (
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px',
          padding: '8px 10px',
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          maxHeight: '120px',
          overflowY: 'auto',
        }}>
          {selectedSymbols.map((sym) => (
            <span
              key={sym}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '3px 8px',
                borderRadius: '4px',
                background: 'rgba(37, 99, 235, 0.15)',
                border: '1px solid rgba(37, 99, 235, 0.35)',
                color: '#93c5fd',
                fontSize: '0.75rem',
                fontWeight: '700',
                fontFamily: 'JetBrains Mono, monospace',
              }}
            >
              <span>{sym}</span>
              <button
                type="button"
                onClick={() => handleRemoveSymbol(sym)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#93c5fd',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  padding: 0,
                  opacity: 0.7,
                }}
              >
                <X style={{ width: '12px', height: '12px' }} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* 3. Search & Picker Box */}
      <div style={{ position: 'relative' }}>
        <div
          onClick={() => setIsOpen(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'var(--bg-input)',
            border: isOpen ? '1px solid var(--accent)' : '1px solid var(--border-color)',
            borderRadius: '6px',
            padding: '6px 12px',
          }}
        >
          <Search style={{ width: '15px', height: '15px', color: 'var(--text-dim)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            style={{
              background: 'transparent',
              border: 'none',
              padding: 0,
              width: '100%',
              fontSize: '0.8125rem',
              color: 'var(--text-main)',
              outline: 'none',
            }}
          />
          {allowCustom && searchQuery.trim() && (
            <button
              type="button"
              onClick={handleAddCustomSymbol}
              className="btn btn-blue"
              style={{ padding: '3px 8px', fontSize: '0.7rem' }}
            >
              <Plus style={{ width: '12px', height: '12px' }} />
              Add "{searchQuery.trim().toUpperCase()}"
            </button>
          )}
          <ChevronDown
            style={{
              width: '14px',
              height: '14px',
              color: 'var(--text-dim)',
              cursor: 'pointer',
              transform: isOpen ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.15s ease',
            }}
            onClick={(e) => {
              e.stopPropagation();
              setIsOpen(!isOpen);
            }}
          />
        </div>

        {/* 4. Dropdown List */}
        {isOpen && (
          <div style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            zIndex: 50,
            background: '#0e131f',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            boxShadow: '0 12px 30px rgba(0, 0, 0, 0.65)',
            maxHeight: '280px',
            overflowY: 'auto',
            animation: 'fadeIn 0.15s ease',
          }}>
            {/* Asset Type Filter Tabs */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 12px',
              background: '#090d16',
              borderBottom: '1px solid var(--border-color)',
              fontSize: '0.72rem',
            }}>
              <span style={{ color: 'var(--text-dim)', fontWeight: '600' }}>Filter:</span>
              {['ALL', 'STOCK', 'INDEX', 'CURRENCY', 'CRYPTO', 'COMMODITY'].map((type) => {
                if (type !== 'ALL' && !assetCounts[type]) return null;
                const isAct = activeAssetType === type;
                return (
                  <button
                    type="button"
                    key={type}
                    onClick={() => setActiveAssetType(type)}
                    style={{
                      background: isAct ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                      border: 'none',
                      color: isAct ? 'var(--text-main)' : 'var(--text-muted)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: isAct ? '700' : '500',
                      cursor: 'pointer',
                    }}
                  >
                    {type} ({assetCounts[type] || 0})
                  </button>
                );
              })}
            </div>

            {loading ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                Loading catalog for {selectedGroup}...
              </div>
            ) : filteredSymbols.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                No matching symbols found in {selectedGroup}.
                {allowCustom && searchQuery.trim() && (
                  <div style={{ marginTop: '8px' }}>
                    <button
                      type="button"
                      onClick={handleAddCustomSymbol}
                      className="btn btn-blue"
                      style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                    >
                      Use custom ticker "{searchQuery.trim().toUpperCase()}"
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ padding: '4px' }}>
                {filteredSymbols.map((item) => {
                  const isChecked = selectedSymbols.includes(item.symbol.toUpperCase());
                  return (
                    <div
                      key={item.symbol}
                      onClick={() => handleSelectSymbol(item)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        background: isChecked ? 'rgba(37, 99, 235, 0.1)' : 'transparent',
                        borderLeft: isChecked ? '3px solid #3b82f6' : '3px solid transparent',
                        transition: 'background 0.1s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (!isChecked) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                      }}
                      onMouseLeave={(e) => {
                        if (!isChecked) e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{
                            fontFamily: 'JetBrains Mono, monospace',
                            fontWeight: '700',
                            fontSize: '0.8125rem',
                            color: 'var(--text-main)',
                          }}>
                            {item.symbol}
                          </span>
                          <span style={{
                            fontSize: '0.65rem',
                            fontWeight: '700',
                            padding: '1px 5px',
                            borderRadius: '3px',
                            background: item.assetType === 'INDEX' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                            color: item.assetType === 'INDEX' ? '#34d399' : '#94a3b8',
                          }}>
                            {item.assetType}
                          </span>
                          {item.sector && item.sector !== 'INDEX' && (
                            <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
                              • {item.sector}
                            </span>
                          )}
                        </div>
                        <span style={{
                          fontSize: '0.72rem',
                          color: 'var(--text-muted)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}>
                          {item.fullName}
                        </span>
                      </div>

                      {isChecked && (
                        <div style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '4px',
                          background: '#2563eb',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}>
                          <Check style={{ width: '12px', height: '12px', color: '#ffffff' }} />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
