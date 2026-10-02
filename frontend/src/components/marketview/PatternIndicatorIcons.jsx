import React from 'react';
import { Box } from '@mui/material';

/**
 * High-precision institutional SVG iconography for Candlestick Pattern Recognition
 * and Technical Indicators. Renders sharp, theme-adaptive vectors beside option labels.
 */

export const CandleIconSvg = ({ id, size = 18 }) => {
  const bullishColor = '#32D74B';
  const bearishColor = '#FF453A';
  const neutralColor = '#98989D';

  switch (id) {
    case 'ALL':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Multi-candle scan representation */}
          <line x1="4" y1="2" x2="4" y2="14" stroke={bearishColor} strokeWidth="1.2" />
          <rect x="2.5" y="4" width="3" height="6" fill={bearishColor} rx="0.5" />
          <line x1="10" y1="3" x2="10" y2="13" stroke={neutralColor} strokeWidth="1.2" />
          <rect x="8.5" y="6" width="3" height="4" fill={neutralColor} rx="0.5" />
          <line x1="16" y1="1" x2="16" y2="15" stroke={bullishColor} strokeWidth="1.2" />
          <rect x="14.5" y="3" width="3" height="8" fill={bullishColor} rx="0.5" />
        </svg>
      );

    case 'ENGULFING_BULLISH':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Small prior red candle */}
          <line x1="5" y1="4" x2="5" y2="12" stroke={bearishColor} strokeWidth="1" />
          <rect x="3.5" y="6" width="3" height="4" fill={bearishColor} rx="0.5" />
          {/* Large engulfing green candle */}
          <line x1="13" y1="1" x2="13" y2="15" stroke={bullishColor} strokeWidth="1.2" />
          <rect x="11" y="3" width="4" height="10" fill={bullishColor} rx="0.5" />
        </svg>
      );

    case 'ENGULFING_BEARISH':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Small prior green candle */}
          <line x1="5" y1="4" x2="5" y2="12" stroke={bullishColor} strokeWidth="1" />
          <rect x="3.5" y="6" width="3" height="4" fill={bullishColor} rx="0.5" />
          {/* Large engulfing red candle */}
          <line x1="13" y1="1" x2="13" y2="15" stroke={bearishColor} strokeWidth="1.2" />
          <rect x="11" y="3" width="4" height="10" fill={bearishColor} rx="0.5" />
        </svg>
      );

    case 'HAMMER':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Small upper green body with long lower shadow */}
          <line x1="10" y1="2" x2="10" y2="15" stroke={bullishColor} strokeWidth="1.2" />
          <rect x="7" y="2" width="6" height="4" fill={bullishColor} rx="0.5" />
        </svg>
      );

    case 'INVERTED_HAMMER':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Long upper shadow with small lower green body */}
          <line x1="10" y1="1" x2="10" y2="14" stroke={bullishColor} strokeWidth="1.2" />
          <rect x="7" y="10" width="6" height="4" fill={bullishColor} rx="0.5" />
        </svg>
      );

    case 'SHOOTING_STAR':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Long upper shadow with small lower red body */}
          <line x1="10" y1="1" x2="10" y2="14" stroke={bearishColor} strokeWidth="1.2" />
          <rect x="7" y="10" width="6" height="4" fill={bearishColor} rx="0.5" />
        </svg>
      );

    case 'HANGING_MAN':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Small upper red body with long lower shadow */}
          <line x1="10" y1="2" x2="10" y2="15" stroke={bearishColor} strokeWidth="1.2" />
          <rect x="7" y="2" width="6" height="4" fill={bearishColor} rx="0.5" />
        </svg>
      );

    case 'DOJI':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Symmetric cross */}
          <line x1="10" y1="1" x2="10" y2="15" stroke={neutralColor} strokeWidth="1.2" />
          <line x1="5" y1="8" x2="15" y2="8" stroke={neutralColor} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );

    case 'DRAGONFLY_DOJI':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* T-shape with crossbar at the very top */}
          <line x1="10" y1="2" x2="10" y2="15" stroke={bullishColor} strokeWidth="1.2" />
          <line x1="4" y1="2" x2="16" y2="2" stroke={bullishColor} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );

    case 'GRAVESTONE_DOJI':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Inverted T-shape with crossbar at the very bottom */}
          <line x1="10" y1="1" x2="10" y2="14" stroke={bearishColor} strokeWidth="1.2" />
          <line x1="4" y1="14" x2="16" y2="14" stroke={bearishColor} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );

    case 'MORNING_STAR':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* 3-candle reversal: Tall red, gapped star, tall green */}
          <line x1="4" y1="2" x2="4" y2="12" stroke={bearishColor} strokeWidth="1" />
          <rect x="2.5" y="3" width="3" height="7" fill={bearishColor} rx="0.5" />
          <line x1="10" y1="11" x2="10" y2="15" stroke={neutralColor} strokeWidth="1" />
          <rect x="8.5" y="12" width="3" height="2" fill={neutralColor} rx="0.5" />
          <line x1="16" y1="3" x2="16" y2="13" stroke={bullishColor} strokeWidth="1" />
          <rect x="14.5" y="4" width="3" height="7" fill={bullishColor} rx="0.5" />
        </svg>
      );

    case 'EVENING_STAR':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* 3-candle reversal: Tall green, gapped top star, tall red */}
          <line x1="4" y1="4" x2="4" y2="14" stroke={bullishColor} strokeWidth="1" />
          <rect x="2.5" y="6" width="3" height="7" fill={bullishColor} rx="0.5" />
          <line x1="10" y1="1" x2="10" y2="5" stroke={neutralColor} strokeWidth="1" />
          <rect x="8.5" y="2" width="3" height="2" fill={neutralColor} rx="0.5" />
          <line x1="16" y1="3" x2="16" y2="13" stroke={bearishColor} strokeWidth="1" />
          <rect x="14.5" y="5" width="3" height="7" fill={bearishColor} rx="0.5" />
        </svg>
      );

    case 'MARUBOZU_BULLISH':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Full solid green body without wicks */}
          <rect x="6" y="1" width="8" height="14" fill={bullishColor} rx="1" />
        </svg>
      );

    case 'MARUBOZU_BEARISH':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Full solid red body without wicks */}
          <rect x="6" y="1" width="8" height="14" fill={bearishColor} rx="1" />
        </svg>
      );

    case 'HARAMI_BULLISH':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Large red candle holding small inside green candle */}
          <line x1="5" y1="1" x2="5" y2="15" stroke={bearishColor} strokeWidth="1" />
          <rect x="3" y="2" width="4" height="12" fill={bearishColor} rx="0.5" />
          <line x1="13" y1="5" x2="13" y2="11" stroke={bullishColor} strokeWidth="1" />
          <rect x="11.5" y="6" width="3" height="4" fill={bullishColor} rx="0.5" />
        </svg>
      );

    case 'HARAMI_BEARISH':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Large green candle holding small inside red candle */}
          <line x1="5" y1="1" x2="5" y2="15" stroke={bullishColor} strokeWidth="1" />
          <rect x="3" y="2" width="4" height="12" fill={bullishColor} rx="0.5" />
          <line x1="13" y1="5" x2="13" y2="11" stroke={bearishColor} strokeWidth="1" />
          <rect x="11.5" y="6" width="3" height="4" fill={bearishColor} rx="0.5" />
        </svg>
      );

    case 'PIERCING_LINE':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Long red candle + green candle opening below and piercing >50% body */}
          <line x1="5" y1="1" x2="5" y2="13" stroke={bearishColor} strokeWidth="1" />
          <rect x="3" y="2" width="4" height="9" fill={bearishColor} rx="0.5" />
          <line x1="13" y1="3" x2="13" y2="15" stroke={bullishColor} strokeWidth="1" />
          <rect x="11" y="5" width="4" height="9" fill={bullishColor} rx="0.5" />
        </svg>
      );

    case 'DARK_CLOUD_COVER':
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          {/* Long green candle + red candle opening above and piercing >50% body down */}
          <line x1="5" y1="3" x2="5" y2="15" stroke={bullishColor} strokeWidth="1" />
          <rect x="3" y="5" width="4" height="9" fill={bullishColor} rx="0.5" />
          <line x1="13" y1="1" x2="13" y2="13" stroke={bearishColor} strokeWidth="1" />
          <rect x="11" y="2" width="4" height="9" fill={bearishColor} rx="0.5" />
        </svg>
      );

    default:
      return (
        <svg width={size} height={size} viewBox="0 0 20 16" fill="none" style={{ flexShrink: 0 }}>
          <line x1="10" y1="1" x2="10" y2="15" stroke={neutralColor} strokeWidth="1.2" />
          <rect x="7" y="4" width="6" height="8" fill={neutralColor} rx="0.5" />
        </svg>
      );
  }
};


export const IndicatorIconSvg = ({ id, color, size = 20 }) => {
  const strokeColor = color || '#38bdf8';

  switch (id) {
    case 'EMA_9':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Fast Exponential Curve */}
          <path d="M 2,12 Q 8,10 12,5 T 20,2" stroke={strokeColor} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );

    case 'EMA_21':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Short Trend Smoothed Curve */}
          <path d="M 2,11 Q 9,9.5 13,6 T 20,3.5" stroke={strokeColor} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );

    case 'EMA_50':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Medium Trend Curve */}
          <path d="M 2,10.5 Q 10,9 14,7 T 20,4.5" stroke={strokeColor} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );

    case 'EMA_200':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Macro Baseline Curve */}
          <path d="M 2,9.5 C 8,9 14,8 20,6.5" stroke={strokeColor} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );

    case 'SMA_20':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Simple Moving Average Dashed Line */}
          <path d="M 2,11 C 7,10 13,7.5 20,4" stroke={strokeColor} strokeWidth="2" strokeDasharray="3 1.5" strokeLinecap="round" />
        </svg>
      );

    case 'VWAP':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Stepped Weighted Price with Volume Bars */}
          <rect x="2" y="10" width="2" height="3" fill="rgba(251, 191, 36, 0.4)" />
          <rect x="6" y="8" width="2" height="5" fill="rgba(251, 191, 36, 0.4)" />
          <rect x="10" y="9" width="2" height="4" fill="rgba(251, 191, 36, 0.4)" />
          <rect x="14" y="6" width="2" height="7" fill="rgba(251, 191, 36, 0.4)" />
          <rect x="18" y="7" width="2" height="6" fill="rgba(251, 191, 36, 0.4)" />
          <path d="M 2,8.5 L 6,8.5 L 6,6 L 14,6 L 14,3.5 L 20,3.5" stroke={strokeColor} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );

    case 'BB':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Bollinger Bands Envelope: Upper, Midline, Lower */}
          <path d="M 2,3 Q 11,1.5 20,3" stroke={strokeColor} strokeWidth="1.5" strokeLinecap="round" />
          <path d="M 2,7 Q 11,7 20,7" stroke={strokeColor} strokeWidth="1" strokeDasharray="2 2" strokeLinecap="round" />
          <path d="M 2,11 Q 11,12.5 20,11" stroke={strokeColor} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );

    case 'SMA_50':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          <path d="M 2,11.5 C 7,10.5 13,8 20,4.5" stroke={strokeColor} strokeWidth="2" strokeDasharray="3 1.5" strokeLinecap="round" />
        </svg>
      );

    case 'SMA_200':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          <path d="M 2,10.5 C 8,10 14,9 20,7" stroke={strokeColor} strokeWidth="2" strokeDasharray="3 1.5" strokeLinecap="round" />
        </svg>
      );

    case 'SUPERTREND':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Dual step-line: green step then red step */}
          <path d="M 2,11 L 8,11 L 8,7 L 13,7" stroke="#32D74B" strokeWidth="2" strokeLinecap="round" />
          <path d="M 13,4 L 17,4 L 17,2 L 20,2" stroke="#FF453A" strokeWidth="2" strokeLinecap="round" />
        </svg>
      );

    case 'KELTNER':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Keltner Channels */}
          <path d="M 2,2.5 Q 11,2 20,3.5" stroke={strokeColor} strokeWidth="1.5" strokeLinecap="round" />
          <path d="M 2,7 Q 11,6.5 20,8" stroke={strokeColor} strokeWidth="1" strokeDasharray="2 2" strokeLinecap="round" />
          <path d="M 2,11.5 Q 11,11 20,12.5" stroke={strokeColor} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );

    case 'DONCHIAN':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Donchian High/Low Step Envelope */}
          <path d="M 2,2 L 10,2 L 10,3 L 20,3" stroke={strokeColor} strokeWidth="1.5" />
          <path d="M 2,12 L 8,12 L 8,11 L 20,11" stroke={strokeColor} strokeWidth="1.5" />
          <path d="M 2,7 L 20,7" stroke={strokeColor} strokeWidth="1" strokeDasharray="2 2" />
        </svg>
      );

    case 'PSAR':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Parabolic SAR Dots below and above */}
          <circle cx="3" cy="11" r="1.2" fill={strokeColor} />
          <circle cx="7" cy="9.5" r="1.2" fill={strokeColor} />
          <circle cx="11" cy="7.5" r="1.2" fill={strokeColor} />
          <circle cx="15" cy="4" r="1.2" fill="#FF453A" />
          <circle cx="19" cy="2.5" r="1.2" fill="#FF453A" />
        </svg>
      );

    case 'PIVOT_POINTS':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* R1, Pivot, S1 horizontal levels */}
          <line x1="2" y1="3" x2="20" y2="3" stroke="#FF453A" strokeWidth="1.2" strokeDasharray="2 1" />
          <line x1="2" y1="7" x2="20" y2="7" stroke="#fbbf24" strokeWidth="1.5" />
          <line x1="2" y1="11" x2="20" y2="11" stroke="#32D74B" strokeWidth="1.2" strokeDasharray="2 1" />
        </svg>
      );

    case 'ZIGZAG':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* ZigZag swing line */}
          <path d="M 2,11 L 8,3 L 14,10 L 20,2" stroke={strokeColor} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );

    case 'ICHIMOKU':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Cloud shaded area + conversion lines */}
          <path d="M 2,8 Q 8,5 14,9 T 20,4 L 20,11 Q 14,13 8,9 T 2,11 Z" fill="rgba(6, 182, 212, 0.2)" />
          <path d="M 2,7 Q 9,5 20,4" stroke="#06b6d4" strokeWidth="1.2" />
          <path d="M 2,9 Q 10,7 20,6" stroke="#f43f5e" strokeWidth="1.2" />
        </svg>
      );

    case 'RSI':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* RSI Wave with 70/30 boundary lines */}
          <line x1="2" y1="3" x2="20" y2="3" stroke="rgba(255,255,255,0.2)" strokeWidth="0.8" strokeDasharray="2 1" />
          <line x1="2" y1="11" x2="20" y2="11" stroke="rgba(255,255,255,0.2)" strokeWidth="0.8" strokeDasharray="2 1" />
          <path d="M 2,10 Q 7,2 12,8 T 20,3" stroke={strokeColor} strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      );

    case 'MACD':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* MACD Histogram & Signal Lines */}
          <rect x="3" y="4" width="2" height="3" fill="#32D74B" />
          <rect x="7" y="2" width="2" height="5" fill="#32D74B" />
          <rect x="11" y="7" width="2" height="4" fill="#FF453A" />
          <rect x="15" y="7" width="2" height="6" fill="#FF453A" />
          <path d="M 2,5 Q 8,3 14,8 T 20,10" stroke="#38bdf8" strokeWidth="1.2" />
          <path d="M 2,7 Q 9,6 15,9 T 20,11" stroke="#f43f5e" strokeWidth="1.2" />
        </svg>
      );

    case 'STOCH_RSI':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Dual %K & %D Oscillators */}
          <path d="M 2,11 Q 7,1 12,9 T 20,2" stroke="#38bdf8" strokeWidth="1.5" />
          <path d="M 2,12 Q 8,3 13,10 T 20,4" stroke="#f59e0b" strokeWidth="1.2" strokeDasharray="2 1" />
        </svg>
      );

    case 'ADX':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* ADX Trend Strength Line */}
          <line x1="2" y1="7" x2="20" y2="7" stroke="rgba(255,255,255,0.2)" strokeWidth="0.8" strokeDasharray="2 1" />
          <path d="M 2,12 Q 10,11 14,4 T 20,2" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" />
        </svg>
      );

    case 'ATR':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Volatility Expansion Curve */}
          <path d="M 2,11 C 6,10 9,4 14,5 T 20,3" stroke="#fbbf24" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      );

    case 'OBV':
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          {/* Volume Trend Stepped Curve */}
          <path d="M 2,11 L 6,11 L 8,7 L 13,7 L 15,3 L 20,3" stroke="#60a5fa" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      );

    default:
      return (
        <svg width={size} height={14} viewBox="0 0 22 14" fill="none" style={{ flexShrink: 0 }}>
          <path d="M 2,10 Q 11,5 20,4" stroke={strokeColor} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );
  }
};
