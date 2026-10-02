import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Avatar,
  Card,
  CardContent,
  Checkbox,
  Divider,
} from '@mui/material';
import PersonAddOutlinedIcon from '@mui/icons-material/PersonAddOutlined';
import AccountBalanceWalletOutlinedIcon from '@mui/icons-material/AccountBalanceWalletOutlined';
import AdminPanelSettingsOutlinedIcon from '@mui/icons-material/AdminPanelSettingsOutlined';
import SecurityOutlinedIcon from '@mui/icons-material/SecurityOutlined';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlined';
import RefreshIcon from '@mui/icons-material/Refresh';
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined';

import { api } from '../../api';
import CashTopupModal from './CashTopupModal';
import CreateRoleModal from './CreateRoleModal';
import CreateUserModal from './CreateUserModal';

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

export default function UserManagementScreen() {
  const [activeTab, setActiveTab] = useState(0);
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modals state
  const [topupTargetUser, setTopupTargetUser] = useState(null);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [showCreateUser, setShowCreateUser] = useState(false);

  // Edited permissions buffer for roles matrix
  const [editedPermissions, setEditedPermissions] = useState({});
  const [isSavingRoles, setIsSavingRoles] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [uRes, rRes] = await Promise.all([api.listUsers(), api.listRoles()]);
      if (uRes && uRes.users) setUsers(uRes.users);
      if (rRes && rRes.roles) {
        setRoles(rRes.roles);
        // Initialize edited permissions
        const initPerms = {};
        rRes.roles.forEach((r) => {
          initPerms[r.id] = JSON.parse(JSON.stringify(r.permissions || {}));
        });
        setEditedPermissions(initPerms);
      }
    } catch (err) {
      setError(err.message || 'Failed to load user and role data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handlePermToggle = (roleId, modKey, action) => {
    setEditedPermissions((prev) => {
      const rolePerms = prev[roleId] ? { ...prev[roleId] } : {};
      const modPerm = rolePerms[modKey] ? { ...rolePerms[modKey] } : { can_view: false, can_edit: false, can_delete: false };
      
      const updatedMod = { ...modPerm, [action]: !modPerm[action] };
      if ((action === 'can_edit' || action === 'can_delete') && updatedMod[action]) {
        updatedMod.can_view = true;
      }
      if (action === 'can_view' && !updatedMod.can_view) {
        updatedMod.can_edit = false;
        updatedMod.can_delete = false;
      }

      return {
        ...prev,
        [roleId]: {
          ...rolePerms,
          [modKey]: updatedMod,
        },
      };
    });
  };

  const handleSaveRolePermissions = async (roleId) => {
    setIsSavingRoles(true);
    setError('');
    setSuccessMsg('');
    try {
      const permsToSave = editedPermissions[roleId];
      await api.updateRole(roleId, { permissions: permsToSave });
      setSuccessMsg(`Permissions for role updated successfully!`);
      await fetchData();
    } catch (err) {
      setError(err.message || 'Failed to save role permissions.');
    } finally {
      setIsSavingRoles(false);
    }
  };

  const handleDeleteRole = async (role) => {
    if (!window.confirm(`Are you sure you want to delete role '${role.name}'?`)) return;
    try {
      await api.deleteRole(role.id);
      setSuccessMsg(`Role '${role.name}' deleted.`);
      fetchData();
    } catch (err) {
      setError(err.message || 'Failed to delete role.');
    }
  };

  const getRoleColor = (roleName) => {
    switch (roleName) {
      case 'ADMIN': return 'primary';
      case 'TRADER': return 'info';
      case 'AUDITOR': return 'warning';
      default: return 'secondary';
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1400, mx: 'auto' }}>
      {/* Action Bar */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', mb: 2.5 }}>
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchData}
            disabled={loading}
            sx={{ textTransform: 'none', borderRadius: 2 }}
          >
            Refresh
          </Button>
          {activeTab === 0 ? (
            <Button
              variant="contained"
              startIcon={<PersonAddOutlinedIcon />}
              onClick={() => setShowCreateUser(true)}
              sx={{ textTransform: 'none', borderRadius: 2, px: 2.5 }}
            >
              Add User
            </Button>
          ) : (
            <Button
              variant="contained"
              startIcon={<AdminPanelSettingsOutlinedIcon />}
              onClick={() => setShowCreateRole(true)}
              sx={{ textTransform: 'none', borderRadius: 2, px: 2.5 }}
            >
              Create Role
            </Button>
          )}
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2.5, borderRadius: 2 }}>{error}</Alert>}
      {successMsg && <Alert severity="success" sx={{ mb: 2.5, borderRadius: 2 }}>{successMsg}</Alert>}

      {/* Tabs */}
      <Paper sx={{ borderRadius: 3, mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(e, val) => setActiveTab(val)}
          indicatorColor="primary"
          textColor="primary"
          sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
        >
          <Tab label="Users & Virtual Balances" sx={{ textTransform: 'none', fontWeight: 600, py: 2 }} />
          <Tab label="Dynamic Role Matrix" sx={{ textTransform: 'none', fontWeight: 600, py: 2 }} />
        </Tabs>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 6 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ p: 2 }}>
            {/* TAB 0: USERS & BALANCES */}
            {activeTab === 0 && (
              <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                <Table>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell sx={{ fontWeight: 700 }}>User</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Role</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Virtual Cash Balance</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Created</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {users.map((u) => (
                      <TableRow key={u.id} hover>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                            <Avatar sx={{ bgcolor: 'primary.main', width: 36, height: 36, fontSize: '0.9rem' }}>
                              {u.username.substring(0, 2).toUpperCase()}
                            </Avatar>
                            <Box>
                              <Typography variant="subtitle2" fontWeight={700}>
                                {u.username}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {u.email}
                              </Typography>
                            </Box>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={u.role?.name || 'NONE'}
                            color={getRoleColor(u.role?.name)}
                            size="small"
                            variant="filled"
                            sx={{ fontWeight: 600 }}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight={800} color="primary.main">
                            ₹{Number(u.cash_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {u.currency || 'INR'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={u.is_active ? 'Active' : 'Inactive'}
                            color={u.is_active ? 'success' : 'default'}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(u.created_at).toLocaleDateString()}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="Top-Up Cash Balance">
                            <IconButton
                              color="primary"
                              size="small"
                              onClick={() => setTopupTargetUser(u)}
                            >
                              <AccountBalanceWalletOutlinedIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {/* TAB 1: DYNAMIC ROLE MATRIX */}
            {activeTab === 1 && (
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Control exactly which modules each role can view, edit, or delete. System roles protect foundational workflows.
                </Typography>

                {roles.map((r) => {
                  const rolePerms = editedPermissions[r.id] || {};
                  return (
                    <Card key={r.id} variant="outlined" sx={{ mb: 3, borderRadius: 2.5 }}>
                      <CardContent sx={{ pb: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                            <Chip
                              label={r.name}
                              color={getRoleColor(r.name)}
                              sx={{ fontWeight: 800, fontSize: '0.85rem' }}
                            />
                            <Typography variant="body2" color="text.secondary">
                              {r.description || 'No description provided'}
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                              variant="outlined"
                              size="small"
                              startIcon={<SaveOutlinedIcon />}
                              onClick={() => handleSaveRolePermissions(r.id)}
                              disabled={isSavingRoles}
                              sx={{ textTransform: 'none', borderRadius: 1.5 }}
                            >
                              Save Permissions
                            </Button>
                            {!r.is_system_role && (
                              <IconButton
                                color="error"
                                size="small"
                                onClick={() => handleDeleteRole(r)}
                              >
                                <DeleteOutlineIcon fontSize="small" />
                              </IconButton>
                            )}
                          </Box>
                        </Box>

                        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 1.5 }}>
                          <Table size="small">
                            <TableHead>
                              <TableRow sx={{ bgcolor: 'action.hover' }}>
                                <TableCell sx={{ fontWeight: 600 }}>Module</TableCell>
                                <TableCell align="center" sx={{ fontWeight: 600 }}>Can View</TableCell>
                                <TableCell align="center" sx={{ fontWeight: 600 }}>Can Edit / Execute</TableCell>
                                <TableCell align="center" sx={{ fontWeight: 600 }}>Can Delete / Purge</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {Object.entries(MODULE_LABELS).map(([modKey, label]) => {
                                const perm = rolePerms[modKey] || { can_view: false, can_edit: false, can_delete: false };
                                const isDisabled = r.name === 'ADMIN'; // ADMIN is master override
                                return (
                                  <TableRow key={modKey} hover>
                                    <TableCell sx={{ fontSize: '0.85rem' }}>{label}</TableCell>
                                    <TableCell align="center">
                                      <Checkbox
                                        checked={perm.can_view}
                                        onChange={() => handlePermToggle(r.id, modKey, 'can_view')}
                                        disabled={isDisabled}
                                        size="small"
                                      />
                                    </TableCell>
                                    <TableCell align="center">
                                      <Checkbox
                                        checked={perm.can_edit}
                                        onChange={() => handlePermToggle(r.id, modKey, 'can_edit')}
                                        disabled={isDisabled}
                                        size="small"
                                      />
                                    </TableCell>
                                    <TableCell align="center">
                                      <Checkbox
                                        checked={perm.can_delete}
                                        onChange={() => handlePermToggle(r.id, modKey, 'can_delete')}
                                        disabled={isDisabled}
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
                      </CardContent>
                    </Card>
                  );
                })}
              </Box>
            )}
          </Box>
        )}
      </Paper>

      {/* Modals */}
      <CashTopupModal
        open={!!topupTargetUser}
        user={topupTargetUser}
        onClose={() => setTopupTargetUser(null)}
        onSuccess={fetchData}
      />

      <CreateRoleModal
        open={showCreateRole}
        onClose={() => setShowCreateRole(false)}
        onSuccess={fetchData}
      />

      <CreateUserModal
        open={showCreateUser}
        roles={roles}
        onClose={() => setShowCreateUser(false)}
        onSuccess={fetchData}
      />
    </Box>
  );
}
