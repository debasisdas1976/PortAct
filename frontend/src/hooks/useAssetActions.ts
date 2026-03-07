import { useState, useCallback } from 'react';
import type { NavigateFunction } from 'react-router-dom';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import {
  getAssetTypeConfig,
  NAVIGATE_TO_PAGE_TYPES,
  SPECIALIZED_DIALOG_TYPES,
} from '../config/assetFieldConfig';
import type { CryptoAssetForEdit } from '../components/CryptoAssetDialog';

/** Route map for navigating to dedicated asset pages */
const ASSET_TYPE_ROUTES: Record<string, string> = {
  stock: '/stocks',
  us_stock: '/us-stocks',
  equity_mutual_fund: '/equity-mf',
  hybrid_mutual_fund: '/hybrid-mf',
  debt_mutual_fund: '/debt-funds',
  commodity: '/commodities',
  sovereign_gold_bond: '/sovereign-gold-bonds',
  esop: '/esops',
  rsu: '/rsus',
  reit: '/reits',
  invit: '/invits',
  savings_account: '/savings',
  fixed_deposit: '/fixed-deposit',
  recurring_deposit: '/recurring-deposit',
  corporate_bond: '/corporate-bond',
  rbi_bond: '/rbi-bond',
  tax_saving_bond: '/tax-saving-bond',
  ppf: '/ppf',
  pf: '/pf',
  nps: '/nps',
  ssy: '/ssy',
  gratuity: '/gratuity',
  insurance_policy: '/insurance',
  crypto: '/crypto-assets',
  nsc: '/nsc',
  kvp: '/kvp',
  scss: '/scss',
  mis: '/mis',
  cash: '/cash-in-hand',
  pension: '/pension',
  land: '/land',
  farm_land: '/farm-land',
  house: '/house',
};

interface UseAssetActionsOptions {
  onRefresh: () => void;
  navigate: NavigateFunction;
}

interface UseAssetActionsReturn {
  // Generic edit dialog
  editDialogOpen: boolean;
  editingAsset: any | null;
  editingAssetType: string;
  openEditDialog: (asset: any) => void;
  closeEditDialog: () => void;

  // Crypto dialog (specialized)
  cryptoDialogOpen: boolean;
  cryptoEditingAsset: CryptoAssetForEdit | null;
  closeCryptoDialog: () => void;

  // Delete
  handleDelete: (asset: any) => Promise<void>;

  // Attributes
  tagAssetId: number | null;
  tagAssetName: string;
  openAttributes: (assetId: number, assetName: string) => void;
  closeAttributes: () => void;
}

export function useAssetActions({ onRefresh, navigate }: UseAssetActionsOptions): UseAssetActionsReturn {
  const { notify } = useNotification();

  // Generic edit dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<any | null>(null);
  const [editingAssetType, setEditingAssetType] = useState('');

  // Crypto dialog state
  const [cryptoDialogOpen, setCryptoDialogOpen] = useState(false);
  const [cryptoEditingAsset, setCryptoEditingAsset] = useState<CryptoAssetForEdit | null>(null);

  // Attribute dialog state
  const [tagAssetId, setTagAssetId] = useState<number | null>(null);
  const [tagAssetName, setTagAssetName] = useState('');

  const openEditDialog = useCallback((asset: any) => {
    const assetType = (asset.asset_type || '').toLowerCase();

    // Account-centric types: navigate to dedicated page
    if (NAVIGATE_TO_PAGE_TYPES.has(assetType)) {
      const route = ASSET_TYPE_ROUTES[assetType];
      if (route) {
        navigate(route);
        return;
      }
    }

    // Crypto: open CryptoAssetDialog
    if (SPECIALIZED_DIALOG_TYPES.has(assetType)) {
      setCryptoEditingAsset({
        id: asset.id,
        name: asset.name,
        symbol: asset.symbol,
        quantity: asset.quantity,
        purchase_price: asset.purchase_price,
        total_invested: asset.total_invested,
        current_price: asset.current_price,
        xirr: asset.xirr,
        crypto_account_id: asset.crypto_account_id,
        details: asset.details,
      });
      setCryptoDialogOpen(true);
      return;
    }

    // Generic: open GenericAssetEditDialog
    setEditingAsset(asset);
    setEditingAssetType(assetType);
    setEditDialogOpen(true);
  }, [navigate]);

  const closeEditDialog = useCallback(() => {
    setEditDialogOpen(false);
    setEditingAsset(null);
    setEditingAssetType('');
  }, []);

  const closeCryptoDialog = useCallback(() => {
    setCryptoDialogOpen(false);
    setCryptoEditingAsset(null);
  }, []);

  const handleDelete = useCallback(async (asset: any) => {
    const label = asset.symbol || asset.name || 'this asset';
    if (!window.confirm(`Delete ${label}?`)) return;
    try {
      await api.delete(`/assets/${asset.id}`);
      const config = getAssetTypeConfig(asset.asset_type);
      notify.success(`${config?.label || 'Asset'} deleted`);
      onRefresh();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete asset'));
    }
  }, [notify, onRefresh]);

  const openAttributes = useCallback((assetId: number, assetName: string) => {
    setTagAssetId(assetId);
    setTagAssetName(assetName);
  }, []);

  const closeAttributes = useCallback(() => {
    setTagAssetId(null);
    setTagAssetName('');
  }, []);

  return {
    editDialogOpen,
    editingAsset,
    editingAssetType,
    openEditDialog,
    closeEditDialog,
    cryptoDialogOpen,
    cryptoEditingAsset,
    closeCryptoDialog,
    handleDelete,
    tagAssetId,
    tagAssetName,
    openAttributes,
    closeAttributes,
  };
}
