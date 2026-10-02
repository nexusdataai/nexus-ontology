/**
 * iconMap maps the YAML schema's icon name strings to lucide-react
 * components. Each name shipped in a real report-schema YAML must
 * resolve; unknown names must fall back to the default (Activity).
 */

import { describe, expect, it } from 'vitest';
import { getIcon } from '../iconMap';
import {
  Activity, AlertTriangle, BarChart3, CheckCircle, Phone, ShoppingCart,
  TrendingUp, Workflow,
} from 'lucide-react';

describe('getIcon', () => {
  it('returns the matching component for a known name', () => {
    expect(getIcon('Activity')).toBe(Activity);
    expect(getIcon('AlertTriangle')).toBe(AlertTriangle);
    expect(getIcon('TrendingUp')).toBe(TrendingUp);
    expect(getIcon('Phone')).toBe(Phone);
    expect(getIcon('ShoppingCart')).toBe(ShoppingCart);
    expect(getIcon('BarChart3')).toBe(BarChart3);
    expect(getIcon('Workflow')).toBe(Workflow);
    expect(getIcon('CheckCircle')).toBe(CheckCircle);
  });

  it('returns Activity for unknown names', () => {
    expect(getIcon('NotARealIcon')).toBe(Activity);
  });

  it('returns Activity for null / empty input', () => {
    expect(getIcon(null)).toBe(Activity);
    expect(getIcon(undefined)).toBe(Activity);
    expect(getIcon('')).toBe(Activity);
  });
});
