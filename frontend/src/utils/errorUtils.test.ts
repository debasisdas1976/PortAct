import { getErrorMessage } from './errorUtils';

// Helper to create AxiosError-like objects
function makeAxiosError(overrides: any = {}): any {
  return {
    isAxiosError: true,
    response: overrides.response,
    code: overrides.code,
    message: overrides.message || '',
    ...overrides,
  };
}

describe('getErrorMessage', () => {
  it('returns fallback for null', () => {
    expect(getErrorMessage(null)).toBe('Something went wrong. Please try again.');
  });

  it('returns fallback for undefined', () => {
    expect(getErrorMessage(undefined)).toBe('Something went wrong. Please try again.');
  });

  it('extracts detail string from AxiosError response', () => {
    const err = makeAxiosError({
      response: { status: 400, data: { detail: 'Invalid email format' } },
    });
    expect(getErrorMessage(err)).toBe('Invalid email format');
  });

  it('returns network error message for ERR_NETWORK', () => {
    const err = makeAxiosError({ code: 'ERR_NETWORK' });
    expect(getErrorMessage(err)).toContain('Unable to connect');
  });

  it('returns timeout message for ECONNABORTED', () => {
    const err = makeAxiosError({
      code: 'ECONNABORTED',
      response: { status: 408, data: {} },
    });
    expect(getErrorMessage(err)).toContain('timed out');
  });

  it('filters technical messages containing Traceback', () => {
    const err = makeAxiosError({
      response: { status: 500, data: { detail: 'Traceback (most recent call last)...' } },
    });
    // Should fall through to 500 fallback, not expose the traceback
    expect(getErrorMessage(err)).not.toContain('Traceback');
  });

  it('handles array validation errors', () => {
    const err = makeAxiosError({
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ['body', 'name'], msg: 'field required', type: 'value_error.missing' },
          ],
        },
      },
    });
    const msg = getErrorMessage(err);
    expect(msg).toContain('name');
    expect(msg).toContain('required');
  });

  it('returns 401 message for expired session', () => {
    const err = makeAxiosError({
      response: { status: 401, data: {} },
    });
    expect(getErrorMessage(err)).toContain('session');
  });

  it('returns 403 permission message', () => {
    const err = makeAxiosError({
      response: { status: 403, data: {} },
    });
    expect(getErrorMessage(err)).toContain('permission');
  });

  it('handles plain string errors', () => {
    expect(getErrorMessage('Something broke')).toBe('Something broke');
  });

  it('handles Error object with short message', () => {
    expect(getErrorMessage(new Error('Bad input'))).toBe('Bad input');
  });

  it('handles Network Error in Error object', () => {
    expect(getErrorMessage(new Error('Network Error'))).toContain('Unable to connect');
  });

  it('respects custom fallback', () => {
    expect(getErrorMessage(null, 'Custom fallback')).toBe('Custom fallback');
  });
});
