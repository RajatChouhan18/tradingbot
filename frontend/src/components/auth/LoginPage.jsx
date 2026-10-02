import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton,
  Container,
} from '@mui/material';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import ShieldOutlinedIcon from '@mui/icons-material/ShieldOutlined';
import TrendingUpOutlinedIcon from '@mui/icons-material/TrendingUpOutlined';
import { useAuth } from '../../context/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!identifier.trim() || !password) {
      setError('Please enter your email or username and password.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await login(identifier.trim(), password);
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100vw',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
        backgroundImage: (theme) =>
          theme.palette.mode === 'dark'
            ? 'radial-gradient(circle at 50% 20%, rgba(37, 99, 235, 0.08) 0%, transparent 60%)'
            : 'radial-gradient(circle at 50% 20%, rgba(27, 58, 107, 0.06) 0%, transparent 60%)',
        p: 2,
      }}
    >
      <Container maxWidth="xs">
        <Paper
          elevation={6}
          sx={{
            p: { xs: 3, sm: 4.5 },
            borderRadius: 3.5,
            border: 1,
            borderColor: 'divider',
            bgcolor: 'background.paper',
            textAlign: 'center',
            boxShadow: (theme) =>
              theme.palette.mode === 'dark'
                ? '0 20px 45px rgba(0, 0, 0, 0.65)'
                : '0 16px 40px rgba(27, 58, 107, 0.12)',
          }}
        >
          {/* Logo & Branding */}
          <Box sx={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', p: 1.5, mb: 1.5, borderRadius: '50%', bgcolor: 'action.hover' }}>
            <ShieldOutlinedIcon color="primary" sx={{ fontSize: 40 }} />
          </Box>

          <Typography variant="h4" component="h1" fontWeight={800} color="primary.main" letterSpacing="0.02em">
            AuraTrade
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.8, mb: 3.5 }}>
            Institutional Trading & Risk Management Terminal
          </Typography>

          {/* Error Message */}
          {error && (
            <Alert severity="error" sx={{ mb: 2.5, borderRadius: 2, textAlign: 'left' }}>
              {error}
            </Alert>
          )}

          {/* Login Form */}
          <Box component="form" onSubmit={handleSubmit} noValidate>
            <TextField
              label="Email or Username"
              variant="outlined"
              fullWidth
              autoComplete="username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              autoFocus
              sx={{ mb: 2.2 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <EmailOutlinedIcon fontSize="small" color="action" />
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              label="Password"
              variant="outlined"
              type={showPassword ? 'text' : 'password'}
              fullWidth
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              sx={{ mb: 3 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <LockOutlinedIcon fontSize="small" color="action" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                      size="small"
                    >
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Button
              type="submit"
              variant="contained"
              fullWidth
              size="large"
              disabled={loading}
              sx={{
                py: 1.4,
                borderRadius: 2.5,
                textTransform: 'none',
                fontWeight: 700,
                fontSize: '1rem',
                boxShadow: (theme) => `0 4px 14px ${theme.palette.primary.main}40`,
              }}
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Sign In to Terminal'}
            </Button>
          </Box>

          {/* Footer note */}
          <Box sx={{ mt: 3.5, pt: 2.5, borderTop: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
            <TrendingUpOutlinedIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary">
              AuraTrade v2.0 • Market-Agnostic Engine
            </Typography>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}
