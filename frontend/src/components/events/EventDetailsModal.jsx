import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  Typography,
  Chip,
  Button,
  IconButton,
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  X,
  Play,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Send,
  Zap,
  RefreshCw,
} from 'lucide-react';
import { api } from '../../api';

export default function EventDetailsModal({
  open,
  onClose,
  triggerId,
  showToast,
}) {
  const [trigger, setTrigger] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [sendLiveAlert, setSendLiveAlert] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const loadTriggerDetails = async () => {
    if (!triggerId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.getEventTrigger(triggerId);
      setTrigger(data);
      setLogs(data.recent_logs || []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load event trigger details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (open && triggerId) {
      setTestResult(null);
      loadTriggerDetails();
    }
  }, [open, triggerId]);

  const handleTestNow = async () => {
    if (!triggerId) return;
    setIsTesting(true);
    setErrorMsg(null);
    try {
      const res = await api.testEventTrigger(triggerId, sendLiveAlert);
      setTestResult(res);
      if (showToast) {
        showToast(
          res.matched
            ? `Test Match: ${res.evaluation_message}`
            : 'Test Evaluated: Condition not currently met.',
          res.matched ? 'success' : 'info'
        );
      }
      // Reload logs to reflect newly saved execution log if alert dispatched
      if (sendLiveAlert && res.matched) {
        await loadTriggerDetails();
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to execute test evaluation.');
    } finally {
      setIsTesting(false);
    }
  };

  if (!open) return null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          backgroundImage: 'none',
          boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pb: 1.5,
          pt: 2.5,
          px: 3,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 38,
              height: 38,
              borderRadius: 2,
              bgcolor: 'info.main',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Zap size={20} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.15rem' }}>
              Event WatchDog Audit & Execution Telemetry
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
              {trigger ? `${trigger.name} (${trigger.symbol} • ${trigger.market})` : 'Loading...'}
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton onClick={loadTriggerDetails} size="small" disabled={isLoading}>
            <RefreshCw size={18} />
          </IconButton>
          <IconButton onClick={onClose} size="small">
            <X size={20} />
          </IconButton>
        </Box>
      </DialogTitle>

      <Divider />

      <DialogContent sx={{ p: 3 }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress size={36} />
          </Box>
        ) : errorMsg ? (
          <Alert severity="error" sx={{ borderRadius: 2 }}>
            {errorMsg}
          </Alert>
        ) : trigger ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Top Summary Card */}
            <Paper
              variant="outlined"
              sx={{
                p: 2.5,
                borderRadius: 2.5,
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 2,
                bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'rgba(30, 41, 59, 0.4)' : '#f8fafc'),
              }}
            >
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, display: 'block' }}>
                  SYMBOL / TIMEFRAME
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 800, fontFamily: 'monospace' }}>
                  {trigger.symbol} ({trigger.timeframe})
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, display: 'block' }}>
                  TRIGGER TYPE
                </Typography>
                <Chip
                  label={trigger.trigger_type}
                  size="small"
                  color="primary"
                  variant="outlined"
                  sx={{ fontWeight: 700, mt: 0.5 }}
                />
              </Box>

              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, display: 'block' }}>
                  LIFETIME TRIGGER COUNT
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 800, fontFamily: 'monospace' }}>
                  {trigger.trigger_count} events fired
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, display: 'block' }}>
                  CHANNELS
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
                  {(trigger.channels || []).map((ch) => (
                    <Chip key={ch} label={ch} size="small" sx={{ height: 20, fontSize: '0.7rem', fontWeight: 700 }} />
                  ))}
                </Box>
              </Box>
            </Paper>

            {/* Test Run Box */}
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                borderRadius: 2.5,
                bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'rgba(15, 23, 42, 0.6)' : '#fff'),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 2,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button
                  variant="contained"
                  color="info"
                  size="small"
                  onClick={handleTestNow}
                  disabled={isTesting}
                  startIcon={isTesting ? <CircularProgress size={16} color="inherit" /> : <Play size={16} />}
                  sx={{ textTransform: 'none', fontWeight: 700 }}
                >
                  {isTesting ? 'Testing...' : 'Dry-Run Test Now'}
                </Button>

                <FormControlLabel
                  control={
                    <Switch
                      checked={sendLiveAlert}
                      onChange={(e) => setSendLiveAlert(e.target.checked)}
                      size="small"
                      color="warning"
                    />
                  }
                  label={
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>
                      Send Live Test Alert to Channels
                    </Typography>
                  }
                />
              </Box>

              {testResult && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <Chip
                    icon={testResult.matched ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                    label={testResult.matched ? 'Condition Match!' : 'No Condition Met'}
                    color={testResult.matched ? 'success' : 'default'}
                    size="small"
                    sx={{ fontWeight: 700 }}
                  />
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace' }}>
                    Latency: {testResult.latency_ms}ms
                  </Typography>
                </Box>
              )}
            </Paper>

            {/* Execution History Table */}
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Clock size={18} /> Audit Execution History ({logs.length} Recent Logs)
              </Typography>

              {logs.length === 0 ? (
                <Paper variant="outlined" sx={{ p: 4, textAlign: 'center', borderRadius: 2 }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    No execution events recorded yet for this watcher.
                  </Typography>
                </Paper>
              ) : (
                <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          Timestamp
                        </TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          Trigger Price
                        </TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          Conditions Met
                        </TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          Channels Dispatched
                        </TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          Latency
                        </TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          Status
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {logs.map((log) => (
                        <TableRow key={log.id} hover>
                          <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                            {new Date(log.created_at).toLocaleString()}
                          </TableCell>
                          <TableCell sx={{ fontFamily: 'monospace', fontWeight: 700 }}>
                            {Number(log.trigger_price).toFixed(4)}
                          </TableCell>
                          <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                            {JSON.stringify(log.conditions_met || {})}
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                              {(log.channels_notified || []).map((ch, idx) => (
                                <Chip
                                  key={idx}
                                  label={`${ch.channel}: ${ch.status}`}
                                  size="small"
                                  color={ch.status === 'SENT' ? 'success' : 'default'}
                                  sx={{ height: 20, fontSize: '0.65rem', fontWeight: 700 }}
                                />
                              ))}
                            </Box>
                          </TableCell>
                          <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                            {log.latency_ms}ms
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={log.dispatch_success ? 'DELIVERED' : 'FAILED'}
                              size="small"
                              color={log.dispatch_success ? 'success' : 'error'}
                              sx={{ fontWeight: 700, height: 20, fontSize: '0.65rem' }}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          </Box>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
