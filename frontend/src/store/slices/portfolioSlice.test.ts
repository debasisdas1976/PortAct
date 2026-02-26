import reducer, {
  clearError,
  setSelectedPortfolioId,
  fetchPortfolioOverview,
} from './portfolioSlice';

describe('portfolioSlice', () => {
  const initialState = {
    overview: null,
    allocation: null,
    summary: null,
    history: [],
    performanceData: null,
    assetPerformanceData: null,
    assetsList: [],
    loading: false,
    error: null,
    performanceLoading: false,
    performanceError: null,
    portfolios: [],
    selectedPortfolioId: null,
    portfoliosLoading: false,
  };

  it('returns initial state', () => {
    const state = reducer(undefined, { type: 'unknown' });
    expect(state.overview).toBeNull();
    expect(state.portfolios).toEqual([]);
    expect(state.loading).toBe(false);
  });

  it('setSelectedPortfolioId updates state and localStorage', () => {
    const state = reducer(initialState, setSelectedPortfolioId(42));
    expect(state.selectedPortfolioId).toBe(42);
    expect(localStorage.getItem('selectedPortfolioId')).toBe('42');
  });

  it('setSelectedPortfolioId(null) removes from localStorage', () => {
    localStorage.setItem('selectedPortfolioId', '42');
    const state = reducer(initialState, setSelectedPortfolioId(null));
    expect(state.selectedPortfolioId).toBeNull();
    expect(localStorage.getItem('selectedPortfolioId')).toBeNull();
  });

  it('clearError resets error to null', () => {
    const withError = { ...initialState, error: 'some error' };
    const state = reducer(withError, clearError());
    expect(state.error).toBeNull();
  });

  it('fetchPortfolioOverview.pending sets loading true', () => {
    const state = reducer(initialState, { type: fetchPortfolioOverview.pending.type });
    expect(state.loading).toBe(true);
    expect(state.error).toBeNull();
  });

  it('fetchPortfolioOverview.fulfilled stores overview data', () => {
    const overview = { portfolio_summary: { total_invested: 1000 } };
    const state = reducer(initialState, {
      type: fetchPortfolioOverview.fulfilled.type,
      payload: overview,
    });
    expect(state.loading).toBe(false);
    expect(state.overview).toEqual(overview);
  });

  it('fetchPortfolioOverview.rejected stores error', () => {
    const state = reducer(initialState, {
      type: fetchPortfolioOverview.rejected.type,
      payload: 'Network error',
    });
    expect(state.loading).toBe(false);
    expect(state.error).toBe('Network error');
  });
});
