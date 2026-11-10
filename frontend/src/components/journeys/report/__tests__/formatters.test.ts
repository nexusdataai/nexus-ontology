/**
 * Tests for the report formatters utility module.
 *
 * Each format code in the YAML schema vocabulary
 * (percent / integer / decimal / duration / currency / text) must
 * produce a stable display string; regressions here would silently
 * mangle every per-journey-type report KPI tile.
 */

import { describe, expect, it } from 'vitest';
import { formatValue, statusColorClass } from '../formatters';

describe('formatValue', () => {
  it('renders -- for null / undefined', () => {
    expect(formatValue(null, 'integer')).toBe('--');
    expect(formatValue(undefined as any, 'percent')).toBe('--');
    expect(formatValue('', 'decimal')).toBe('--');
  });

  it('renders percent with one decimal', () => {
    expect(formatValue(15, 'percent')).toBe('15.0%');
    expect(formatValue(15.789, 'percent')).toBe('15.8%');
  });

  it('renders integer with thousands separator above 10k', () => {
    expect(formatValue(42, 'integer')).toBe('42');
    expect(formatValue(15000, 'integer')).toBe('15,000');
  });

  it('renders decimal with two decimal places', () => {
    expect(formatValue(3.14159, 'decimal')).toBe('3.14');
    expect(formatValue(2, 'decimal')).toBe('2.00');
  });

  it('renders duration in seconds-minutes-hours', () => {
    expect(formatValue(45, 'duration')).toBe('45s');
    expect(formatValue(95, 'duration')).toBe('1m 35s');
    expect(formatValue(3700, 'duration')).toBe('1h 1m');
    expect(formatValue(0, 'duration')).toBe('0s');
  });

  it('renders currency with compact suffixes for large amounts', () => {
    expect(formatValue(500, 'currency')).toBe('$500');
    expect(formatValue(15_000, 'currency')).toBe('$15.0K');
    expect(formatValue(2_500_000, 'currency')).toBe('$2.50M');
  });

  it('passes text through unchanged', () => {
    expect(formatValue('Positive', 'text')).toBe('Positive');
  });

  it('falls back to string conversion for unknown formats', () => {
    expect(formatValue(42, 'wat')).toBe('42');
  });

  it('handles non-numeric strings gracefully', () => {
    // Numeric formats fall back to the raw string when not a number.
    expect(formatValue('N/A', 'percent')).toBe('N/A%');
    expect(formatValue('N/A', 'integer')).toBe('N/A');
  });
});

describe('statusColorClass', () => {
  it('maps status -> design token colour classes', () => {
    expect(statusColorClass('critical')).toBe('text-destructive');
    expect(statusColorClass('warn')).toBe('text-warning');
    expect(statusColorClass('ok')).toBe('text-success');
  });

  it('returns empty string for null / unknown status', () => {
    expect(statusColorClass(null)).toBe('');
    expect(statusColorClass(undefined)).toBe('');
    expect(statusColorClass('rainbow')).toBe('');
  });
});
