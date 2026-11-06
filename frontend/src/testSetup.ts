import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Without vitest's globals, Testing Library doesn't unmount between tests by itself
afterEach(cleanup);
