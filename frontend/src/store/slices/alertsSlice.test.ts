import reducer, { clearError, fetchAlerts, deleteAlert } from './alertsSlice';

describe('alertsSlice', () => {
  const initialState = {
    alerts: [],
    unreadCount: 0,
    loading: false,
    error: null,
  };

  it('returns initial state', () => {
    const state = reducer(undefined, { type: 'unknown' });
    expect(state.alerts).toEqual([]);
    expect(state.unreadCount).toBe(0);
  });

  it('fetchAlerts.fulfilled computes unreadCount', () => {
    const alerts = [
      { id: 1, is_read: false },
      { id: 2, is_read: true },
      { id: 3, is_read: false },
    ];
    const state = reducer(initialState, {
      type: fetchAlerts.fulfilled.type,
      payload: alerts,
    });
    expect(state.alerts).toHaveLength(3);
    expect(state.unreadCount).toBe(2);
  });

  it('deleteAlert.fulfilled removes alert and recomputes count', () => {
    const withAlerts = {
      ...initialState,
      alerts: [
        { id: 1, is_read: false },
        { id: 2, is_read: false },
      ],
      unreadCount: 2,
    };
    const state = reducer(withAlerts, {
      type: deleteAlert.fulfilled.type,
      payload: 1,
    });
    expect(state.alerts).toHaveLength(1);
    expect(state.alerts[0].id).toBe(2);
    expect(state.unreadCount).toBe(1);
  });

  it('clearError resets error', () => {
    const withError = { ...initialState, error: 'some error' };
    const state = reducer(withError, clearError());
    expect(state.error).toBeNull();
  });
});
