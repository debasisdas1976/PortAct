import reducer, { clearError, fetchAssets } from './assetsSlice';

describe('assetsSlice', () => {
  const initialState = {
    assets: [],
    loading: false,
    error: null,
  };

  it('returns initial state', () => {
    const state = reducer(undefined, { type: 'unknown' });
    expect(state.assets).toEqual([]);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('clearError resets error', () => {
    const withError = { ...initialState, error: 'some error' };
    const state = reducer(withError, clearError());
    expect(state.error).toBeNull();
  });

  it('fetchAssets.pending sets loading', () => {
    const state = reducer(initialState, { type: fetchAssets.pending.type });
    expect(state.loading).toBe(true);
    expect(state.error).toBeNull();
  });

  it('fetchAssets.fulfilled stores assets', () => {
    const assets = [{ id: 1, name: 'Stock A' }, { id: 2, name: 'Stock B' }];
    const state = reducer(initialState, {
      type: fetchAssets.fulfilled.type,
      payload: assets,
    });
    expect(state.loading).toBe(false);
    expect(state.assets).toEqual(assets);
  });

  it('fetchAssets.rejected stores error', () => {
    const state = reducer(initialState, {
      type: fetchAssets.rejected.type,
      payload: 'Failed to load',
    });
    expect(state.loading).toBe(false);
    expect(state.error).toBe('Failed to load');
  });
});
