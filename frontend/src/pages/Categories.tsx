import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  Tabs,
  Tab,
  Tooltip,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Category as CategoryIcon
} from '@mui/icons-material';
import api from '../services/api';

interface Category {
  id: number;
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  keywords?: string;
  is_system: boolean;
  is_income: boolean;
  is_active: boolean;
}

const Categories: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [filteredCategories, setFilteredCategories] = useState<Category[]>([]);
  const [tabValue, setTabValue] = useState(0); // 0: Expense, 1: Income
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    icon: '',
    color: '#4CAF50',
    keywords: '',
    is_income: false,
    is_active: true
  });

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    // Filter categories based on selected tab
    const isIncome = tabValue === 1;
    setFilteredCategories(
      categories.filter(cat => cat.is_income === isIncome && cat.is_active)
    );
  }, [categories, tabValue]);

  const fetchCategories = async () => {
    try {
      const response = await api.get('/expense-categories/');
      setCategories(response.data);
    } catch (err) {
      setError('Failed to fetch categories');
    }
  };

  const handleOpenDialog = (category?: Category) => {
    if (category) {
      setEditingCategory(category);
      setFormData({
        name: category.name,
        description: category.description || '',
        icon: category.icon || '',
        color: category.color || '#4CAF50',
        keywords: category.keywords || '',
        is_income: category.is_income,
        is_active: category.is_active
      });
    } else {
      setEditingCategory(null);
      setFormData({
        name: '',
        description: '',
        icon: '',
        color: '#4CAF50',
        keywords: '',
        is_income: tabValue === 1,
        is_active: true
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingCategory(null);
    setError('');
  };

  const handleSaveCategory = async () => {
    if (!formData.name.trim()) {
      setError('Category name is required');
      return;
    }

    try {
      if (editingCategory) {
        await api.put(`/expense-categories/${editingCategory.id}`, formData);
        setSuccess('Category updated successfully');
      } else {
        await api.post('/expense-categories/', formData);
        setSuccess('Category created successfully');
      }
      
      handleCloseDialog();
      fetchCategories();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save category');
    }
  };

  const handleDeleteCategory = async (categoryId: number) => {
    if (!window.confirm('Are you sure you want to delete this category?')) {
      return;
    }

    try {
      await api.delete(`/expense-categories/${categoryId}`);
      setSuccess('Category deleted successfully');
      fetchCategories();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete category');
      setTimeout(() => setError(''), 5000);
    }
  };

  const handleRecategorize = async () => {
    if (!window.confirm('This will re-categorize all expenses based on current keywords. Continue?')) {
      return;
    }

    try {
      const response = await api.post('/expense-categories/recategorize', {});
      
      setSuccess(
        `Re-categorization complete! ${response.data.total_affected} expenses updated ` +
        `(${response.data.updated} changed, ${response.data.marked_categorized} marked as categorized)`
      );
      setTimeout(() => setSuccess(''), 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to re-categorize expenses');
      setTimeout(() => setError(''), 5000);
    }
  };

  const getKeywordArray = (keywords?: string): string[] => {
    if (!keywords) return [];
    return keywords.split(',').map(k => k.trim()).filter(k => k);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CategoryIcon /> Expense Categories
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            color="secondary"
            onClick={handleRecategorize}
          >
            Re-categorize All Expenses
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add Category
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      {/* Info Card */}
      <Card sx={{ mb: 3, bgcolor: 'info.light', color: 'info.contrastText' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            💡 How Auto-Categorization Works
          </Typography>
          <Typography variant="body2">
            Add keywords to your categories to automatically categorize transactions. When a transaction 
            description contains any of the keywords, it will be assigned to that category. Keywords are 
            case-insensitive and matched as substrings.
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            <strong>Example:</strong> If you add keywords "uber,lyft,taxi" to "Transportation", any transaction 
            with "Uber" or "LYFT" in the description will be automatically categorized as Transportation.
          </Typography>
        </CardContent>
      </Card>

      {/* Tabs for Expense/Income */}
      <Paper sx={{ mb: 2 }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label={`Expense Categories (${categories.filter(c => !c.is_income && c.is_active).length})`} />
          <Tab label={`Income Categories (${categories.filter(c => c.is_income && c.is_active).length})`} />
        </Tabs>
      </Paper>

      {/* Categories Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: 'grey.100' }}>
              <TableCell sx={{ fontWeight: 'bold' }}>Icon</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Name</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Description</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Keywords</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Type</TableCell>
              <TableCell align="center" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredCategories.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography color="textSecondary">
                    No categories found. Click "Add Category" to create one.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredCategories.map((category) => (
                <TableRow
                  key={category.id}
                  sx={{ '&:hover': { backgroundColor: 'grey.50' } }}
                >
                  <TableCell>
                    <Box
                      sx={{
                        width: 40,
                        height: 40,
                        borderRadius: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        bgcolor: category.color || '#4CAF50',
                        fontSize: '1.5rem'
                      }}
                    >
                      {category.icon || '📁'}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body1" fontWeight="medium">
                      {category.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="textSecondary">
                      {category.description || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, maxWidth: 400 }}>
                      {getKeywordArray(category.keywords).slice(0, 5).map((keyword, idx) => (
                        <Chip
                          key={idx}
                          label={keyword}
                          size="small"
                          variant="outlined"
                        />
                      ))}
                      {getKeywordArray(category.keywords).length > 5 && (
                        <Tooltip title={getKeywordArray(category.keywords).slice(5).join(', ')}>
                          <Chip
                            label={`+${getKeywordArray(category.keywords).length - 5} more`}
                            size="small"
                            color="primary"
                          />
                        </Tooltip>
                      )}
                      {getKeywordArray(category.keywords).length === 0 && (
                        <Typography variant="body2" color="textSecondary">
                          No keywords
                        </Typography>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={category.is_system ? 'System' : 'Custom'}
                      size="small"
                      color={category.is_system ? 'default' : 'primary'}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Tooltip title="Edit category">
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(category)}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={category.is_system ? 'System categories cannot be deleted' : 'Delete'}>
                      <span>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteCategory(category.id)}
                          disabled={category.is_system}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingCategory ? 'Edit Category' : 'Add New Category'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={8}>
              <TextField
                fullWidth
                label="Category Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Icon (Emoji)"
                value={formData.icon}
                onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                placeholder="🛒"
                helperText="Use an emoji"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Color"
                type="color"
                value={formData.color}
                onChange={(e) => setFormData({ ...formData, color: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_income}
                    onChange={(e) => setFormData({ ...formData, is_income: e.target.checked })}
                  />
                }
                label="Income Category"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Keywords (comma-separated)"
                value={formData.keywords}
                onChange={(e) => setFormData({ ...formData, keywords: e.target.value })}
                multiline
                rows={3}
                placeholder="grocery,supermarket,walmart,food"
                helperText="Add keywords to automatically categorize transactions. Separate with commas."
              />
            </Grid>
            <Grid item xs={12}>
              <Alert severity="info">
                <Typography variant="body2">
                  <strong>Tip:</strong> Add multiple variations of keywords for better matching. 
                  For example: "uber,lyft,taxi,cab,ola" for transportation.
                </Typography>
              </Alert>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveCategory} variant="contained">
            {editingCategory ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Categories;

// Made with Bob
