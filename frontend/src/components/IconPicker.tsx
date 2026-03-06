import React, { useState, useMemo } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  InputAdornment,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  // ── Finance & Money ──
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  ShowChart,
  BarChart,
  PieChart,
  DonutSmall,
  AccountBalance,
  AccountBalanceWallet,
  Savings,
  Wallet,
  CreditCard,
  MonetizationOn,
  Paid,
  CurrencyExchange,
  AttachMoney,
  RequestQuote,
  Receipt,
  ReceiptLong,
  PriceCheck,
  Sell,
  ShoppingCart,
  Store,
  LocalMall,
  Redeem,
  CardGiftcard,
  Token,
  CurrencyBitcoin,

  // ── Charts & Data ──
  BubbleChart,
  ScatterPlot,
  Timeline,
  Insights,
  Analytics,
  Assessment,
  Leaderboard,
  Equalizer,
  StackedLineChart,

  // ── Security & Status ──
  Shield,
  Lock,
  Security,
  Gavel,
  Verified,
  CheckCircle,
  Warning,
  Info,
  Help,
  VerifiedUser,
  AdminPanelSettings,
  Policy,
  GppGood,
  GppBad,
  Fingerprint,
  VpnKey,
  Key,

  // ── Real Estate & Property ──
  Home,
  Apartment,
  Landscape,
  Agriculture,
  Factory,
  Cottage,
  Domain,
  LocationCity,
  Foundation,
  Roofing,
  MapsHomeWork,
  Villa,

  // ── Nature & Environment ──
  Park,
  Forest,
  Terrain,
  WbSunny,
  NightsStay,
  Cloud,
  Air,
  WaterDrop,
  Grain,
  Spa,
  Yard,
  Grass,
  NaturePeople,

  // ── People & Social ──
  Person,
  Groups,
  ChildCare,
  Elderly,
  Business,
  Work,
  School,
  VolunteerActivism,
  Handshake,
  Diversity3,
  FamilyRestroom,
  SupervisedUserCircle,
  Engineering,

  // ── Travel & Transport ──
  Public,
  Explore,
  Map,
  Anchor,
  Rocket,
  Flight,
  DirectionsCar,
  DirectionsBoat,
  Train,
  LocalShipping,
  Sailing,
  TwoWheeler,

  // ── Health & Wellness ──
  FitnessCenter,
  HealthAndSafety,
  Psychology,
  SelfImprovement,
  LocalHospital,
  MedicalServices,
  Vaccines,
  MonitorHeart,
  Bloodtype,

  // ── Energy & Power ──
  LocalFireDepartment,
  Bolt,
  Speed,
  Timer,
  FlashOn,
  BatteryChargingFull,
  ElectricBolt,
  SolarPower,
  WindPower,
  EnergySavingsLeaf,
  Thermostat,
  Propane,
  OilBarrel,

  // ── Awards & Achievements ──
  Star,
  Favorite,
  EmojiEvents,
  WorkspacePremium,
  MilitaryTech,
  Grade,
  Stars,
  AutoAwesome,
  Whatshot,
  LocalActivity,
  Celebration,

  // ── Labels & Organization ──
  Flag,
  Bookmark,
  Label,
  Category,
  Layers,
  FilterList,
  Sort,
  LocalOffer,
  Style,
  Inventory2,
  FolderSpecial,
  Topic,
  Hub,
  AccountTree,
  DeviceHub,
  Lan,
  Share,
  Interests,

  // ── Tools & Settings ──
  Extension,
  Tune,
  Palette,
  Brush,
  Construction,
  Build,
  Settings,
  Handyman,
  Plumbing,
  Carpenter,
  Architecture,

  // ── Media & Creative ──
  MusicNote,
  Videocam,
  PhotoCamera,
  Image,
  CameraAlt,
  ColorLens,
  Draw,
  DesignServices,
  AutoFixHigh,

  // ── Communication ──
  Email,
  Phone,
  Chat,
  Forum,
  Campaign,
  Notifications,
  Announcement,
  RecordVoiceOver,

  // ── Education & Learning ──
  MenuBook,
  LocalLibrary,
  HistoryEdu,
  Science,
  Biotech,
  Calculate,
  Functions,

  // ── Shapes & Symbols ──
  Circle,
  Square,
  Hexagon,
  Pentagon,
  ChangeHistory,
  FiberManualRecord,
  RadioButtonChecked,
  Brightness1,
  AllInclusive,
  Flare,
  Adjust,
  HighlightAlt,
  CropSquare,

  // ── Misc ──
  Diamond,
  LightMode,
  DarkMode,
  Visibility,
  Balance,
  Scale,
  Compress,
  Expand,
  SwapHoriz,
  SwapVert,
  CompareArrows,
  SyncAlt,
  Loop,
  Autorenew,
  Refresh,
  RestartAlt,
  Pending,
  Schedule,
  Update,
  EventRepeat,
  CalendarMonth,
  DateRange,
  AccessTime,
  Timelapse,
  HourglassEmpty,
  HourglassFull,
} from '@mui/icons-material';

// Curated icon map: name -> component
export const ICON_MAP: Record<string, React.ComponentType<any>> = {
  // Finance & Money
  TrendingUp, TrendingDown, TrendingFlat, ShowChart, BarChart, PieChart, DonutSmall,
  AccountBalance, AccountBalanceWallet, Savings, Wallet, CreditCard,
  MonetizationOn, Paid, CurrencyExchange, AttachMoney, RequestQuote,
  Receipt, ReceiptLong, PriceCheck, Sell, ShoppingCart, Store, LocalMall,
  Redeem, CardGiftcard, Token, CurrencyBitcoin,

  // Charts & Data
  BubbleChart, ScatterPlot, Timeline, Insights, Analytics, Assessment,
  Leaderboard, Equalizer, StackedLineChart,

  // Security & Status
  Shield, Lock, Security, Gavel, Verified, CheckCircle, Warning, Info, Help,
  VerifiedUser, AdminPanelSettings, Policy, GppGood, GppBad,
  Fingerprint, VpnKey, Key,

  // Real Estate & Property
  Home, Apartment, Landscape, Agriculture, Factory, Cottage,
  Domain, LocationCity, Foundation, Roofing, MapsHomeWork, Villa,

  // Nature & Environment
  Park, Forest, Terrain, WbSunny, NightsStay, Cloud, Air, WaterDrop, Grain,
  Spa, Yard, Grass, NaturePeople,

  // People & Social
  Person, Groups, ChildCare, Elderly, Business, Work, School,
  VolunteerActivism, Handshake, Diversity3, FamilyRestroom,
  SupervisedUserCircle, Engineering,

  // Travel & Transport
  Public, Explore, Map, Anchor, Rocket, Flight, DirectionsCar,
  DirectionsBoat, Train, LocalShipping, Sailing, TwoWheeler,

  // Health & Wellness
  FitnessCenter, HealthAndSafety, Psychology, SelfImprovement,
  LocalHospital, MedicalServices, Vaccines, MonitorHeart, Bloodtype,

  // Energy & Power
  LocalFireDepartment, Bolt, Speed, Timer, FlashOn, BatteryChargingFull,
  ElectricBolt, SolarPower, WindPower, EnergySavingsLeaf, Thermostat,
  Propane, OilBarrel,

  // Awards & Achievements
  Star, Favorite, EmojiEvents, WorkspacePremium, MilitaryTech, Grade, Stars,
  AutoAwesome, Whatshot, LocalActivity, Celebration,

  // Labels & Organization
  Flag, Bookmark, Label, Category, Layers, FilterList, Sort, LocalOffer,
  Style, Inventory2, FolderSpecial, Topic, Hub, AccountTree, DeviceHub,
  Lan, Share, Interests,

  // Tools & Settings
  Extension, Tune, Palette, Brush, Construction, Build, Settings,
  Handyman, Plumbing, Carpenter, Architecture,

  // Media & Creative
  MusicNote, Videocam, PhotoCamera, Image, CameraAlt, ColorLens,
  Draw, DesignServices, AutoFixHigh,

  // Communication
  Email, Phone, Chat, Forum, Campaign, Notifications, Announcement,
  RecordVoiceOver,

  // Education & Learning
  MenuBook, LocalLibrary, HistoryEdu, Science, Biotech, Calculate, Functions,

  // Shapes & Symbols
  Circle, Square, Hexagon, Pentagon, ChangeHistory, FiberManualRecord,
  RadioButtonChecked, Brightness1, AllInclusive, Flare, Adjust,
  HighlightAlt, CropSquare,

  // Misc
  Diamond, LightMode, DarkMode, Visibility, Balance, Scale,
  Compress, Expand, SwapHoriz, SwapVert, CompareArrows, SyncAlt,
  Loop, Autorenew, Refresh, RestartAlt, Pending, Schedule, Update,
  EventRepeat, CalendarMonth, DateRange, AccessTime, Timelapse,
  HourglassEmpty, HourglassFull,
};

const ICON_NAMES = Object.keys(ICON_MAP);

/** Renders an MUI icon by its stored name string. Returns null if not found. */
export const DynamicIcon: React.FC<{ name: string | null | undefined; fontSize?: 'small' | 'medium' | 'inherit'; color?: string }> = ({
  name,
  fontSize = 'small',
  color,
}) => {
  if (!name) return null;
  const IconComp = ICON_MAP[name];
  if (!IconComp) return null;
  return <IconComp fontSize={fontSize} sx={color ? { color } : undefined} />;
};

interface IconPickerProps {
  value: string;
  onChange: (iconName: string) => void;
  label?: string;
}

const IconPicker: React.FC<IconPickerProps> = ({ value, onChange, label = 'Icon' }) => {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search.trim()) return ICON_NAMES;
    const q = search.toLowerCase();
    return ICON_NAMES.filter((n) => n.toLowerCase().includes(q));
  }, [search]);

  const SelectedIcon = value ? ICON_MAP[value] : null;

  return (
    <>
      <TextField
        label={label}
        value={value || ''}
        onClick={() => setOpen(true)}
        fullWidth
        placeholder="Click to select an icon"
        InputProps={{
          readOnly: true,
          startAdornment: SelectedIcon ? (
            <InputAdornment position="start">
              <SelectedIcon fontSize="small" />
            </InputAdornment>
          ) : undefined,
        }}
        sx={{ cursor: 'pointer' }}
      />

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Choose an Icon</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            size="small"
            fullWidth
            placeholder="Search icons..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ mb: 2, mt: 1 }}
          />
          {filtered.length === 0 ? (
            <Typography color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
              No icons match "{search}"
            </Typography>
          ) : (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, maxHeight: 320, overflow: 'auto' }}>
              {filtered.map((name) => {
                const IconComp = ICON_MAP[name];
                const isSelected = value === name;
                return (
                  <Tooltip key={name} title={name} arrow>
                    <IconButton
                      onClick={() => {
                        onChange(name);
                        setOpen(false);
                        setSearch('');
                      }}
                      sx={{
                        border: isSelected ? '2px solid' : '1px solid',
                        borderColor: isSelected ? 'primary.main' : 'divider',
                        borderRadius: 1,
                        bgcolor: isSelected ? 'primary.light' : 'transparent',
                        color: isSelected ? 'primary.contrastText' : 'text.primary',
                        width: 40,
                        height: 40,
                        '&:hover': { bgcolor: isSelected ? 'primary.light' : 'action.hover' },
                      }}
                    >
                      <IconComp fontSize="small" />
                    </IconButton>
                  </Tooltip>
                );
              })}
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default IconPicker;
