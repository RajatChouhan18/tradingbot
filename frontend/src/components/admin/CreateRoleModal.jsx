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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Paper,
} from '@mui/material';
import AdminPanelSettingsOutlinedIcon from '@mui/icons-material/AdminPanelSettingsOutlined';
import { api } from '../../api';

const MODULE_LABELS = {
  MARKETVIEW: 'MarketView (Live Data & Charts)',
  EVENT_TRIGGERS: 'Event WatchDog',
  ALGOTRADE: 'AlgoTrade (Composite Strategies)',

  PAPER_TRADING: 'Paper Trading Execution',
  CATALOG: 'Market Catalog Directory',
  TEST_WORKBENCH: 'In-App Test Workbench',
  THEME_STUDIO: 'Theme Studio Customizer',
  USER_MANAGEMENT: 'User & Role Management',
};

export default function CreateRoleModal({ open, onClose, availableModules = [], onSuccess }) {
  const [roleName, setRoleName] = useState('');
  const [description, setDescription] = useState('');
  const [permissions, setPermissions] = useState(() => {
    const init = {};
    Object.keys(MODULE_LABELS).forEach((k) => {
      init[k] = { can_view: false, can_edit: false, can_delete: false };
    });
    return init;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleToggle = (moduleKey, action) => {
    setPermissions((prev) => {
      const current = prev[moduleKey] || { can_view: false, can_edit: false, can_delete: false };
      const updated = { ...current, [action]: !current[action] };
      // If granting edit or delete, automatically grant view
      if ((action === 'can_edit' || action === 'can_delete') && updated[action]) {
        updated.can_view = true;
      }
      // If revoking view, automatically revoke edit and delete
      if (action === 'can_view' && !updated.can_view) {
        updated.can_edit = false;
        updated.can_delete = false;
      }
      return { ...prev, [moduleKey]: updated };
    });
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!roleName.trim()) {
      setError('Role name is required.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await api.createRole({
        name: roleName.trim().toUpperCase(),
        description: description.trim(),
        permissions,
      });
      if (onSuccess) onSuccess();
      if (onClose) onClose();
    } catch (err) {
      setError(err.message || 'Failed to create role.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        elevation: 8,
        sx: { borderRadius: 3, p: 1 },
      }}
    >
      <DialogTitle sx={{ pb: 1, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <AdminPanelSettingsOutlinedIcon color="primary" />
        <Box>
          <Typography variant="h6" fontWeight={700}>
            Create Custom System Role
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure dynamic module visibility and permissions
          </Typography>
        </Box>
      </DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent sx={{ pt: 1.5 }}>
          {error && <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>{error}</Alert>}

          <Box sx={{ display: 'flex', gap: 2, mb: 2.5 }}>
            <TextField
              label="Role Name (e.g. RISK_OFFICER)"
              variant="outlined"
              fullWidth
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
              required
              helperText="Uppercase alphanumeric identifier"
            />
            <TextField
              label="Role Description"
              variant="outlined"
              fullWidth
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              helperText="Institutional scope and responsibility"
            />
          </Box>

          <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
            Module Permission Matrix:
          </Typography>

          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, maxHeight: 340 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Module</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 700 }}>View</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 700 }}>Edit / Execute</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 700 }}>Delete / Purge</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(MODULE_LABELS).map(([modKey, label]) => {
                  const perm = permissions[modKey] || { can_view: false, can_edit: false, can_delete: false };
                  return (
                    <TableRow key={modKey} hover>
                      <TableCell sx={{ fontWeight: 500 }}>{label}</TableCell>
                      <TableCell align="center">
                        <Checkbox
                          checked={perm.can_view}
                          onChange={() => handleToggle(modKey, 'can_view')}
                          size="small"
                          color="primary"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Checkbox
                          checked={perm.can_edit}
                          onChange={() => handleToggle(modKey, 'can_edit')}
                          size="small"
                          color="primary"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Checkbox
                          checked={perm.can_delete}
                          onChange={() => handleToggle(modKey, 'can_delete')}
                          size="small"
                          color="error"
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
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
            {loading ? <CircularProgress size={22} color="inherit" /> : 'Create Role'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
