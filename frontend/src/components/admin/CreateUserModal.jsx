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
  MenuItem,
} from '@mui/material';
import PersonAddOutlinedIcon from '@mui/icons-material/PersonAddOutlined';
import { api } from '../../api';

export default function CreateUserModal({ open, onClose, roles = [], onSuccess }) {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [roleId, setRoleId] = useState(roles.length > 0 ? roles[0].id : '');
  const [initialBalance, setInitialBalance] = useState(1000000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!email || !username || !password || !roleId) {
      setError('Please fill in all required fields.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await api.createUser({
        email: email.trim(),
        username: username.trim(),
        password,
        role_id: roleId,
        initial_balance: Number(initialBalance || 0),
      });
      if (onSuccess) onSuccess();
      if (onClose) onClose();
    } catch (err) {
      setError(err.message || 'Failed to create user account.');
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
        <PersonAddOutlinedIcon color="primary" />
        <Box>
          <Typography variant="h6" fontWeight={700}>
            Create New User Account
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Assign credentials, system role, and virtual capital
          </Typography>
        </Box>
      </DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent sx={{ pt: 1.5, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {error && <Alert severity="error" sx={{ mb: 1, borderRadius: 2 }}>{error}</Alert>}

          <TextField
            label="Email Address"
            type="email"
            variant="outlined"
            fullWidth
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <TextField
            label="Username"
            variant="outlined"
            fullWidth
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />

          <TextField
            label="Password"
            type="password"
            variant="outlined"
            fullWidth
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <TextField
            select
            label="Assign Role"
            value={roleId}
            onChange={(e) => setRoleId(e.target.value)}
            fullWidth
            required
          >
            {roles.map((r) => (
              <MenuItem key={r.id} value={r.id}>
                {r.name} {r.is_system_role ? '(System)' : '(Custom)'}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            label="Initial Virtual Balance (₹)"
            type="number"
            variant="outlined"
            fullWidth
            value={initialBalance}
            onChange={(e) => setInitialBalance(Number(e.target.value))}
            helperText="Default allocation: ₹1,000,000 INR"
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
            {loading ? <CircularProgress size={22} color="inherit" /> : 'Create User'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
