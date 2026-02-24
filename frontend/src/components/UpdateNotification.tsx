import React, { useState, useEffect, useCallback } from 'react';
import {
  Alert,
  AlertTitle,
  Collapse,
  IconButton,
  Typography,
  Box,
  Link,
} from '@mui/material';
import {
  SystemUpdateAlt as UpdateIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { systemAPI } from '../services/api';

const DISMISSED_KEY = 'portact_update_dismissed_version';

interface UpdateInfo {
  current_version: string;
  latest_version: string;
  update_available: boolean;
  release_url: string | null;
  release_notes: string | null;
  published_at: string | null;
  error: string | null;
}

const UpdateNotification: React.FC = () => {
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [visible, setVisible] = useState(false);

  const checkForUpdate = useCallback(async () => {
    try {
      const data: UpdateInfo = await systemAPI.checkUpdate();

      if (data.update_available && data.latest_version) {
        const dismissedVersion = localStorage.getItem(DISMISSED_KEY);
        if (dismissedVersion === data.latest_version) {
          return;
        }
        setUpdateInfo(data);
        setVisible(true);
      }
    } catch {
      // Silently ignore update check failures
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(checkForUpdate, 5000);
    return () => clearTimeout(timer);
  }, [checkForUpdate]);

  const handleDismiss = () => {
    setVisible(false);
    if (updateInfo?.latest_version) {
      localStorage.setItem(DISMISSED_KEY, updateInfo.latest_version);
    }
  };

  if (!updateInfo || !visible) return null;

  const isDocker = window.location.port === '8080' ||
    !(process.env.REACT_APP_API_URL || '').includes('localhost:8000');

  const updateCommand = isDocker
    ? './scripts/run_docker.sh'
    : './update.sh';

  const updateInstructions = isDocker
    ? 'Stop the container and re-run the Docker launcher script:'
    : 'Run the update script from your PortAct directory:';

  return (
    <Collapse in={visible}>
      <Alert
        severity="info"
        icon={<UpdateIcon />}
        action={
          <IconButton
            aria-label="dismiss"
            color="inherit"
            size="small"
            onClick={handleDismiss}
          >
            <CloseIcon fontSize="inherit" />
          </IconButton>
        }
        sx={{ mb: 2, borderRadius: 1 }}
      >
        <AlertTitle>
          Update Available: v{updateInfo.latest_version}
        </AlertTitle>
        <Typography variant="body2" sx={{ mb: 1 }}>
          You are running v{updateInfo.current_version}.{' '}
          A newer version (v{updateInfo.latest_version}) is available.
        </Typography>
        <Typography variant="body2" sx={{ mb: 0.5 }}>
          {updateInstructions}
        </Typography>
        <Box
          component="code"
          sx={{
            display: 'block',
            bgcolor: 'grey.100',
            p: 1,
            borderRadius: 0.5,
            fontSize: '0.85rem',
            fontFamily: 'monospace',
            mb: 1,
          }}
        >
          {updateCommand}
        </Box>
        {updateInfo.release_url && (
          <Link
            href={updateInfo.release_url}
            target="_blank"
            rel="noopener noreferrer"
            variant="body2"
          >
            View release notes on GitHub
          </Link>
        )}
      </Alert>
    </Collapse>
  );
};

export default UpdateNotification;
