import api, { authAPI } from './api';

// Mock axios at the module level
jest.mock('axios', () => {
  const actualAxios = jest.requireActual('axios');
  const instance = {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    patch: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    defaults: { baseURL: '', headers: { common: {} } },
  };
  return {
    ...actualAxios,
    create: jest.fn(() => instance),
    __mockInstance: instance,
  };
});

describe('api service', () => {
  it('api instance is created', () => {
    expect(api).toBeDefined();
  });

  it('authAPI has expected methods', () => {
    expect(typeof authAPI.login).toBe('function');
    expect(typeof authAPI.register).toBe('function');
    expect(typeof authAPI.getCurrentUser).toBe('function');
    expect(typeof authAPI.forgotPassword).toBe('function');
    expect(typeof authAPI.resetPassword).toBe('function');
  });

  it('authAPI.login calls api.post with form data', async () => {
    const mockPost = api.post as jest.Mock;
    mockPost.mockResolvedValueOnce({
      data: { access_token: 'tok', refresh_token: 'ref', token_type: 'bearer' },
    });

    const result = await authAPI.login({ username: 'testuser', password: 'pass' });
    expect(mockPost).toHaveBeenCalledWith(
      '/auth/login',
      expect.any(FormData),
      expect.objectContaining({ headers: expect.any(Object) }),
    );
    expect(result).toEqual({ access_token: 'tok', refresh_token: 'ref', token_type: 'bearer' });
  });

  it('authAPI.register calls api.post with JSON body', async () => {
    const mockPost = api.post as jest.Mock;
    mockPost.mockResolvedValueOnce({
      data: { id: 1, email: 'a@b.com', username: 'newuser' },
    });

    const userData = { email: 'a@b.com', username: 'newuser', full_name: 'New', password: 'pass1234' };
    const result = await authAPI.register(userData);
    expect(mockPost).toHaveBeenCalledWith('/auth/register', userData);
    expect(result.id).toBe(1);
  });
});
