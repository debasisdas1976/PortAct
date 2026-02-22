import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  Select,
  MenuItem,
  Divider,
  ListItemIcon,
  ListItemText,
  SelectChangeEvent,
} from '@mui/material';
import {
  FolderSpecial as FolderIcon,
  Settings as ManageIcon,
} from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { fetchPortfolios, setSelectedPortfolioId } from '../store/slices/portfolioSlice';

const PortfolioSelector: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { portfolios, selectedPortfolioId } = useSelector(
    (state: RootState) => state.portfolio
  );

  useEffect(() => {
    dispatch(fetchPortfolios());
  }, [dispatch]);

  const handleChange = (event: SelectChangeEvent<string>) => {
    const val = event.target.value;
    if (val === '__manage__') {
      navigate('/portfolios');
      return;
    }
    const id = val === '' ? null : parseInt(val, 10);
    dispatch(setSelectedPortfolioId(id));
  };

  return (
    <Select
      value={selectedPortfolioId !== null ? String(selectedPortfolioId) : ''}
      onChange={handleChange}
      displayEmpty
      variant="outlined"
      size="small"
      sx={{
        color: 'white',
        minWidth: 180,
        mr: 2,
        '.MuiOutlinedInput-notchedOutline': {
          borderColor: 'rgba(255,255,255,0.3)',
        },
        '&:hover .MuiOutlinedInput-notchedOutline': {
          borderColor: 'rgba(255,255,255,0.6)',
        },
        '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
          borderColor: 'rgba(255,255,255,0.8)',
        },
        '.MuiSvgIcon-root': {
          color: 'white',
        },
        fontSize: '0.875rem',
      }}
      renderValue={(selected) => {
        if (!selected) return 'All Portfolios';
        const p = portfolios.find((p: any) => String(p.id) === selected);
        return p ? p.name : 'All Portfolios';
      }}
    >
      <MenuItem value="">
        <ListItemIcon sx={{ minWidth: 32 }}>
          <FolderIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText primary="All Portfolios" />
      </MenuItem>
      {portfolios.map((p: any) => (
        <MenuItem key={p.id} value={String(p.id)}>
          <ListItemIcon sx={{ minWidth: 32 }}>
            <FolderIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary={p.name} />
        </MenuItem>
      ))}
      <Divider />
      <MenuItem value="__manage__">
        <ListItemIcon sx={{ minWidth: 32 }}>
          <ManageIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText primary="Manage Portfolios" />
      </MenuItem>
    </Select>
  );
};

export default PortfolioSelector;

// Made with Bob
