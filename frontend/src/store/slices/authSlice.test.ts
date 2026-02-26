import reducer, { logout, clearError, login, register, getCurrentUser } from './authSlice';

describe('authSlice', () => {
  const initialState = {
    user: null,
    token: null,
    isAuthenticated: false,
    loading: false,
    error: null,
  };

  it('returns initial state', () => {
    const state = reducer(undefined, { type: 'unknown' });
    expect(state.user).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('logout clears user, token, and isAuthenticated', () => {
    const authed = {
      ...initialState,
      user: { id: 1, email: 'a@b.com', username: 'a', full_name: 'A' },
      token: 'tok',
      isAuthenticated: true,
    };
    const state = reducer(authed, logout());
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('clearError resets error to null', () => {
    const withError = { ...initialState, error: 'some error' };
    const state = reducer(withError, clearError());
    expect(state.error).toBeNull();
  });

  it('login.pending sets loading true', () => {
    const state = reducer(initialState, { type: login.pending.type });
    expect(state.loading).toBe(true);
  });

  it('login.fulfilled sets token and isAuthenticated', () => {
    const state = reducer(initialState, {
      type: login.fulfilled.type,
      payload: { access_token: 'new-token', refresh_token: 'ref', token_type: 'bearer' },
    });
    expect(state.loading).toBe(false);
    expect(state.token).toBe('new-token');
    expect(state.isAuthenticated).toBe(true);
    expect(state.error).toBeNull();
  });

  it('login.rejected sets error string', () => {
    const state = reducer(initialState, {
      type: login.rejected.type,
      payload: 'Invalid credentials',
    });
    expect(state.loading).toBe(false);
    expect(state.error).toBe('Invalid credentials');
  });

  it('register.fulfilled does not set isAuthenticated', () => {
    const state = reducer(initialState, {
      type: register.fulfilled.type,
      payload: { id: 1, email: 'a@b.com', username: 'a' },
    });
    expect(state.isAuthenticated).toBe(false);
    expect(state.loading).toBe(false);
  });

  it('getCurrentUser.fulfilled sets user object', () => {
    const user = { id: 1, email: 'a@b.com', username: 'testuser', full_name: 'Test' };
    const state = reducer(initialState, {
      type: getCurrentUser.fulfilled.type,
      payload: user,
    });
    expect(state.user).toEqual(user);
  });

  it('getCurrentUser.rejected clears auth state', () => {
    const authed = { ...initialState, isAuthenticated: true, token: 'tok' };
    const state = reducer(authed, { type: getCurrentUser.rejected.type });
    expect(state.isAuthenticated).toBe(false);
    expect(state.token).toBeNull();
  });
});
