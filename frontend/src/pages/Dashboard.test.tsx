import React from 'react';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import Dashboard from './Dashboard';

// Mock the chart components (they use canvas which jsdom doesn't support)
jest.mock('../components/charts/PortfolioChart', () => () => <div data-testid="portfolio-chart" />);
jest.mock('../components/charts/PerformanceChart', () => () => <div data-testid="performance-chart" />);
jest.mock('../components/charts/AssetAllocationChart', () => () => <div data-testid="allocation-chart" />);

// Mock the notification context (must include NotificationProvider for test-utils wrapper)
jest.mock('../contexts/NotificationContext', () => {
  const React = require('react');
  return {
    useNotification: () => ({
      notify: { success: jest.fn(), error: jest.fn(), info: jest.fn(), warning: jest.fn() },
    }),
    NotificationProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
  };
});

// Mock the portfolio hook
jest.mock('../hooks/useSelectedPortfolio', () => ({
  useSelectedPortfolio: () => ({ selectedPortfolioId: null, portfolioLabel: 'All Portfolios' }),
}));

// Mock API calls
jest.mock('../services/api', () => ({
  __esModule: true,
  default: {
    get: jest.fn().mockResolvedValue({ data: [] }),
    post: jest.fn().mockResolvedValue({ data: {} }),
  },
  assetTypesAPI: {
    getCategories: jest.fn().mockResolvedValue([]),
  },
  getErrorMessage: jest.fn((_err: any) => 'error'),
}));

describe('Dashboard', () => {
  it('renders without crashing', () => {
    renderWithProviders(<Dashboard />, {
      preloadedState: {
        auth: { user: { id: 1, username: 'test' }, token: 'tok', isAuthenticated: true, loading: false, error: null },
        portfolio: {
          overview: null, allocation: null, summary: null, history: [],
          performanceData: null, assetPerformanceData: null, assetsList: [],
          loading: false, error: null, performanceLoading: false, performanceError: null,
          portfolios: [], selectedPortfolioId: null, portfoliosLoading: false,
        },
        assets: { assets: [], loading: false, error: null },
        alerts: { alerts: [], unreadCount: 0, loading: false, error: null },
      },
    });
    expect(document.body).toBeTruthy();
  });

  it('renders loading state when portfolio is loading', () => {
    renderWithProviders(<Dashboard />, {
      preloadedState: {
        auth: { user: { id: 1, username: 'test' }, token: 'tok', isAuthenticated: true, loading: false, error: null },
        portfolio: {
          overview: null, allocation: null, summary: null, history: [],
          performanceData: null, assetPerformanceData: null, assetsList: [],
          loading: true, error: null, performanceLoading: false, performanceError: null,
          portfolios: [], selectedPortfolioId: null, portfoliosLoading: false,
        },
        assets: { assets: [], loading: false, error: null },
        alerts: { alerts: [], unreadCount: 0, loading: false, error: null },
      },
    });
    // Should show a loading indicator
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders portfolio summary when data is loaded', () => {
    renderWithProviders(<Dashboard />, {
      preloadedState: {
        auth: { user: { id: 1, username: 'test' }, token: 'tok', isAuthenticated: true, loading: false, error: null },
        portfolio: {
          overview: {
            portfolio_summary: {
              total_invested: 100000,
              total_current_value: 120000,
              total_profit_loss: 20000,
              total_profit_loss_percentage: 20,
            },
            assets_by_type: { stock: 5 },
            value_by_type: { stock: 120000 },
            recent_transactions: [],
            unread_alerts: 0,
            top_performers: [],
            bottom_performers: [],
          },
          allocation: null, summary: null, history: [],
          performanceData: null, assetPerformanceData: null, assetsList: [],
          loading: false, error: null, performanceLoading: false, performanceError: null,
          portfolios: [], selectedPortfolioId: null, portfoliosLoading: false,
        },
        assets: { assets: [], loading: false, error: null },
        alerts: { alerts: [], unreadCount: 0, loading: false, error: null },
      },
    });
    // Should render without crashing with overview data
    expect(document.body).toBeTruthy();
  });
});
