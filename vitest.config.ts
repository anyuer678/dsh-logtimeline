import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts'],
      exclude: ['src/**/*.d.ts'],
      thresholds: {
        // Baseline measured 2026-09 with src/** filter: lines ~61%. Floor 60 keeps CI green.
        lines: 60,
        functions: 55,
        statements: 55
      }
    }
  }
})
