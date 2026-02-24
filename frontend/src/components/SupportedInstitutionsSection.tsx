import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Alert,
  Collapse,
  Divider,
} from '@mui/material';
import {
  AccountBalance,
  CreditCard,
  ShowChart,
  Flag,
  Lock as LockIcon,
  KeyboardArrowDown,
  KeyboardArrowRight,
  Info as InfoIcon,
  Lightbulb as TipIcon,
} from '@mui/icons-material';
import { institutionHelpEntries, InstitutionHelpEntry } from './InstitutionHelpData';

const categoryConfig: Record<
  string,
  { label: string; icon: React.ReactElement; color: 'primary' | 'secondary' | 'success' | 'warning' }
> = {
  bank: { label: 'Banks', icon: <AccountBalance fontSize="small" />, color: 'primary' },
  credit_card: { label: 'Credit Cards', icon: <CreditCard fontSize="small" />, color: 'secondary' },
  demat: { label: 'Demat Brokers & Aggregators', icon: <ShowChart fontSize="small" />, color: 'success' },
  government: { label: 'Government Schemes', icon: <Flag fontSize="small" />, color: 'warning' },
};

const categoryOrder: Array<keyof typeof categoryConfig> = ['bank', 'credit_card', 'demat', 'government'];

const SupportedInstitutionsSection: React.FC = () => {
  const [expanded, setExpanded] = useState(false);
  const [selected, setSelected] = useState<InstitutionHelpEntry | null>(null);

  // Group entries by category
  const grouped = institutionHelpEntries.reduce<Record<string, InstitutionHelpEntry[]>>((acc, entry) => {
    if (!acc[entry.category]) acc[entry.category] = [];
    acc[entry.category].push(entry);
    return acc;
  }, {});

  return (
    <Paper sx={{ mb: 2, overflow: 'hidden' }}>
      {/* Collapsible header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          p: 2,
          cursor: 'pointer',
          bgcolor: 'action.hover',
          '&:hover': { bgcolor: 'action.selected' },
          userSelect: 'none',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <KeyboardArrowDown sx={{ color: 'text.secondary' }} />
        ) : (
          <KeyboardArrowRight sx={{ color: 'text.secondary' }} />
        )}
        <Box sx={{ ml: 1, mr: 1, display: 'flex', alignItems: 'center', color: 'primary.main' }}>
          <InfoIcon />
        </Box>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Supported Institutions
        </Typography>
        <Chip
          label={institutionHelpEntries.length}
          size="small"
          color="primary"
          variant="outlined"
        />
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ p: 2, pt: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Click on any institution below to see step-by-step instructions on how to download your statement.
          </Typography>

          {categoryOrder.map((cat) => {
            const config = categoryConfig[cat];
            const entries = grouped[cat] || [];
            if (entries.length === 0) return null;

            return (
              <Box key={cat} sx={{ mb: 2.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Box sx={{ color: `${config.color}.main`, display: 'flex', alignItems: 'center' }}>
                    {config.icon}
                  </Box>
                  <Typography variant="subtitle2" fontWeight={600}>
                    {config.label}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {entries.map((entry) => (
                    <Chip
                      key={entry.id}
                      label={entry.name}
                      icon={entry.passwordRequired ? <LockIcon fontSize="small" /> : undefined}
                      onClick={() => setSelected(entry)}
                      variant="outlined"
                      color={config.color}
                      clickable
                      size="small"
                    />
                  ))}
                </Box>
              </Box>
            );
          })}

          <Typography variant="caption" color="text.secondary">
            <LockIcon sx={{ fontSize: 12, verticalAlign: 'middle', mr: 0.5 }} />
            indicates the statement may be password-protected.
          </Typography>
        </Box>
      </Collapse>

      {/* Detail Dialog */}
      <Dialog
        open={!!selected}
        onClose={() => setSelected(null)}
        maxWidth="sm"
        fullWidth
      >
        {selected && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {selected.name}
              </Box>
            </DialogTitle>
            <DialogContent>
              <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                <Chip
                  label={`Format: ${selected.formats}`}
                  color="primary"
                  size="small"
                  variant="outlined"
                />
                {selected.passwordRequired && (
                  <Chip
                    icon={<LockIcon fontSize="small" />}
                    label="Password Protected"
                    color="warning"
                    size="small"
                    variant="outlined"
                  />
                )}
              </Box>

              {selected.passwordRequired && selected.passwordHint && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  <strong>Password hint:</strong> {selected.passwordHint}
                </Alert>
              )}

              <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
                How to download:
              </Typography>
              <Box component="ol" sx={{ pl: 2.5, m: 0 }}>
                {selected.steps.map((step, i) => (
                  <Box
                    component="li"
                    key={i}
                    sx={{ mb: 0.75, fontSize: '0.875rem', lineHeight: 1.6 }}
                  >
                    {step}
                  </Box>
                ))}
              </Box>

              {selected.tips && selected.tips.length > 0 && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                    <TipIcon fontSize="small" color="warning" />
                    <Typography variant="subtitle2" fontWeight={600}>
                      Tips
                    </Typography>
                  </Box>
                  <Box component="ul" sx={{ pl: 2.5, m: 0 }}>
                    {selected.tips.map((tip, i) => (
                      <Box
                        component="li"
                        key={i}
                        sx={{ mb: 0.5, fontSize: '0.875rem', color: 'text.secondary', lineHeight: 1.5 }}
                      >
                        {tip}
                      </Box>
                    ))}
                  </Box>
                </>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelected(null)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Paper>
  );
};

export default SupportedInstitutionsSection;
