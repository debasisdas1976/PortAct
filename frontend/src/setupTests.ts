import '@testing-library/jest-dom';

// Mock localStorage for tests (authSlice reads it at module load time)
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (i: number) => Object.keys(store)[i] || null,
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock window.matchMedia (used by MUI components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Suppress noisy React Router & MUI warnings in test output
const originalError = console.error;
const originalWarn = console.warn;
console.error = (...args: any[]) => {
  if (typeof args[0] === 'string' && (
    args[0].includes('React Router') ||
    args[0].includes('inside a test was not wrapped in act')
  )) return;
  originalError.call(console, ...args);
};
console.warn = (...args: any[]) => {
  if (typeof args[0] === 'string' && args[0].includes('React Router')) return;
  originalWarn.call(console, ...args);
};
