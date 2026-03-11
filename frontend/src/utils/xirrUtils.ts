/**
 * XIRR utility functions for safe display and aggregation.
 *
 * Astronomical XIRR values (e.g. annualising a 2-day holding) can break
 * weighted averages and render nonsensical UI. We cap at ±1000%.
 */

export const XIRR_CAP = 1000;

/**
 * Clamp an XIRR value to the safe range [-XIRR_CAP, +XIRR_CAP].
 * Returns null for null/undefined input.
 */
export function clampXirr(value: number | null | undefined): number | null {
  if (value == null) return null;
  if (!isFinite(value)) return null;
  return Math.max(-XIRR_CAP, Math.min(XIRR_CAP, value));
}

/**
 * Format a (possibly extreme) XIRR value for display.
 * Returns a formatted string like "+12.34%" or "N/A".
 */
export function formatXirr(value: number | null | undefined): string {
  const clamped = clampXirr(value);
  if (clamped == null) return 'N/A';
  const sign = clamped >= 0 ? '+' : '';
  return `${sign}${clamped.toFixed(2)}%`;
}
