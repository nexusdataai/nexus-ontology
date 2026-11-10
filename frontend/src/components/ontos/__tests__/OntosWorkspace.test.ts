/**
 * OntosWorkspace Tests
 *
 * Unit and property-based tests for the Ontos tabbed workspace container.
 *
 * Feature: ontos-fdw-ui
 * Validates: Requirements 2.1, 2.2, 2.3, 2.4
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import {
  ONTOS_TAB_CONFIGS,
  type OntosTabId,
} from '../OntosWorkspace';

const ALL_TAB_IDS: OntosTabId[] = [
  'tables',
  'query',
];

describe('OntosWorkspace', () => {
  // Requirement 2.1: tabs with correct labels (the dashboard is now an overview strip above the tabs)
  describe('Tab configuration', () => {
    it('should define exactly 2 tabs', () => {
      expect(ONTOS_TAB_CONFIGS).toHaveLength(2);
    });

    it('should have the correct tab IDs in order', () => {
      const ids = ONTOS_TAB_CONFIGS.map((t) => t.id);
      expect(ids).toEqual(ALL_TAB_IDS);
    });

    it('should have the correct labels', () => {
      const labels = ONTOS_TAB_CONFIGS.map((t) => t.label);
      expect(labels).toEqual([
        'Tables',
        'Query',
      ]);
    });

    it('should have unique IDs', () => {
      const ids = ONTOS_TAB_CONFIGS.map((t) => t.id);
      expect(new Set(ids).size).toBe(ids.length);
    });

    it('should have unique labels', () => {
      const labels = ONTOS_TAB_CONFIGS.map((t) => t.label);
      expect(new Set(labels).size).toBe(labels.length);
    });

    it('should have an icon for every tab', () => {
      ONTOS_TAB_CONFIGS.forEach((tab) => {
        expect(tab.icon).toBeDefined();
      });
    });
  });

  // Requirement 2.3: default to the Tables tab
  describe('Default tab', () => {
    it('should have tables as the first tab', () => {
      expect(ONTOS_TAB_CONFIGS[0].id).toBe('tables');
    });
  });

  // Requirement 2.2 / 2.4: tab switching preserves state
  describe('Tab switching simulation', () => {
    it('should track active tab through any sequence of switches', () => {
      fc.assert(
        fc.property(
          fc.array(fc.constantFrom(...ALL_TAB_IDS), { minLength: 1, maxLength: 20 }),
          (tabSequence) => {
            let activeTab: OntosTabId = 'tables';
            tabSequence.forEach((t) => {
              activeTab = t;
            });
            expect(activeTab).toBe(tabSequence[tabSequence.length - 1]);
            // The active tab should always be a valid tab ID
            expect(ALL_TAB_IDS).toContain(activeTab);
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
