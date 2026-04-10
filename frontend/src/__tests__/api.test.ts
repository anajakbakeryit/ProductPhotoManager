import { describe, it, expect } from 'vitest';
import { setToken, getToken } from '../lib/api';

describe('api token management', () => {
  it('should start with null token', () => {
    setToken(null);
    expect(getToken()).toBeNull();
  });

  it('should set and get token', () => {
    setToken('test-jwt-token');
    expect(getToken()).toBe('test-jwt-token');
  });

  it('should clear token', () => {
    setToken('test-jwt-token');
    setToken(null);
    expect(getToken()).toBeNull();
  });
});
