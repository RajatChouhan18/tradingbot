import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  Alert,
  CircularProgress,
  Chip,
  Stack,
  Divider,
} from '@mui/material';
import AccountBalanceWalletOutlinedIcon from '@mui/icons-material/AccountBalanceWalletOutlined';
import { api } from '../../api';

export default function CashTopupModal({ open, onClose, user, onSuccess }) {
  const [amount, setAmount] = useState(100000);
  const [reason, setReason] = useState('Admin Allocation');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!user) return null;

  const currentBal = user.cash_balance || 0;
  const newBal = currentBal + Number(amount || 0);

  const handleQuickAdd = (delta) => {
    setAmount((prev) => Math.max(0, Number(prev || 0) + delta));
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (newBal < 0) {
      setError('Adjustment would result in negative cash balance.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await api.topupUserBalance(user.id, {
        amount: Number(amount),
        reason: reason.trim() || 'Admin Manual Top-Up',
      });
      if (onSuccess) onSuccess();
      if (onClose) onClose();
    } catch (err) {
      setError(err.message || 'Failed to update balance.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        elevation: 8,
        sx: { borderRadius: 3, p: 1 },
      }}
    >
      <DialogTitle sx={{ pb: 1, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <AccountBalanceWalletOutlinedIcon color="primary" />
        <Box>
          <Typography variant="h6" fontWeight={700}>
            Top-Up Virtual Cash Balance
          </Typography>
          <Typography variant="body2" color="text.secondary">
            User: {user.email} ({user.role?.name || user.role})
          </Typography>
        </Box>
      </DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent sx={{ pt: 1.5 }}>
          {error && <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>{error}</Alert>}

          <Box sx={{ p: 2, mb: 2.5, bgcolor: 'action.hover', borderRadius: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">Current Balance:</Typography>
              <Typography variant="body1" fontWeight={700}>
                ₹{currentBal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">Adjustment Delta:</Typography>
              <Typography variant="body1" fontWeight={700} color={amount >= 0 ? 'success.main' : 'error.main'}>
                {amount >= 0 ? '+' : ''}₹{Number(amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </Typography>
            </Box>
            <Divider sx={{ my: 1 }} />
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="subtitle2" fontWeight={600}>Projected New Balance:</Typography>
              <Typography variant="subtitle1" fontWeight={800} color="primary.main">
                ₹{newBal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </Typography>
            </Box>
          </Box>

          <TextField
            label="Adjustment Amount (₹)"
            type="number"
            variant="outlined"
            fullWidth
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            required
            sx={{ mb: 1.5 }}
          />

          <Stack direction="row" spacing={1} sx={{ mb: 2.5, flexWrap: 'wrap', gap: 0.5 }}>
            <Chip label="+₹50,000" size="small" onClick={() => handleQuickAdd(50000)} sx={{ cursor: 'pointer' }} />
            <Chip label="+₹100,000" size="small" onClick={() => handleQuickAdd(100000)} sx={{ cursor: 'pointer' }} />
            <Chip label="+₹500,000" size="small" onClick={() => handleQuickAdd(500000)} sx={{ cursor: 'pointer' }} />
            <Chip label="+₹1,000,000" size="small" color="primary" onClick={() => handleQuickAdd(1000000)} sx={{ cursor: 'pointer' }} />
          </Stack>

          <TextField
            label="Audit Reason"
            variant="outlined"
            fullWidth
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            helperText="Recorded in the immutable PostgreSQL balance audit logs"
          />
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={onClose} disabled={loading} sx={{ textTransform: 'none' }}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={loading}
            sx={{ textTransform: 'none', px: 3, borderRadius: 2 }}
          >
            {loading ? <CircularProgress size={22} color="inherit" /> : 'Confirm Top-Up'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
