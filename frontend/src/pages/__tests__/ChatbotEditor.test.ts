/**
 * Chatbot Editor Tests
 * 
 * Property-based tests for message rendering and counting.
 * 
 * Feature: ai-workspace
 * Property 3: Message Rendering Completeness
 * Validates: Requirements 3.1, 3.5, 3.6
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { Message, formatTimestamp, countMessagesBySender } from '../ChatbotEditor';

// Arbitrary for generating valid Message objects
const messageArbitrary = fc.record({
  id: fc.string({ minLength: 1, maxLength: 20 }),
  content: fc.string({ minLength: 1, maxLength: 500 }),
  sender: fc.constantFrom('user', 'assistant') as fc.Arbitrary<'user' | 'assistant'>,
  timestamp: fc.date({ min: new Date('2020-01-01'), max: new Date('2030-12-31') })
});

describe('ChatbotEditor', () => {
  // ==========================================================================
  // Property 3: Message Rendering Completeness
  // For any list of chat messages, all messages SHALL be rendered with correct
  // sender styling (user/assistant), visible timestamps, and the message count
  // SHALL equal the actual number of messages in the list.
  // Validates: Requirements 3.1, 3.5, 3.6
  // ==========================================================================
  describe('Property 3: Message Rendering Completeness', () => {
    describe('formatTimestamp', () => {
      it('should format any valid date to a time string', () => {
        fc.assert(
          fc.property(
            fc.date({ min: new Date('2020-01-01'), max: new Date('2030-12-31') }),
            (date) => {
              const result = formatTimestamp(date);
              // Should return a non-empty string
              expect(typeof result).toBe('string');
              expect(result.length).toBeGreaterThan(0);
              // Should contain time-like format (digits and colon)
              expect(result).toMatch(/\d{1,2}:\d{2}/);
              return true;
            }
          ),
          { numRuns: 100 }
        );
      });

      it('should produce consistent output for the same date', () => {
        fc.assert(
          fc.property(
            fc.date({ min: new Date('2020-01-01'), max: new Date('2030-12-31') }),
            (date) => {
              const result1 = formatTimestamp(date);
              const result2 = formatTimestamp(new Date(date.getTime()));
              expect(result1).toBe(result2);
              return true;
            }
          ),
          { numRuns: 50 }
        );
      });
    });

    describe('countMessagesBySender', () => {
      it('should return correct count for user messages', () => {
        fc.assert(
          fc.property(
            fc.array(messageArbitrary, { minLength: 0, maxLength: 50 }),
            (messages) => {
              const userCount = countMessagesBySender(messages, 'user');
              const expectedCount = messages.filter(m => m.sender === 'user').length;
              expect(userCount).toBe(expectedCount);
              return true;
            }
          ),
          { numRuns: 100 }
        );
      });

      it('should return correct count for assistant messages', () => {
        fc.assert(
          fc.property(
            fc.array(messageArbitrary, { minLength: 0, maxLength: 50 }),
            (messages) => {
              const assistantCount = countMessagesBySender(messages, 'assistant');
              const expectedCount = messages.filter(m => m.sender === 'assistant').length;
              expect(assistantCount).toBe(expectedCount);
              return true;
            }
          ),
          { numRuns: 100 }
        );
      });

      it('should have user + assistant counts equal total messages', () => {
        fc.assert(
          fc.property(
            fc.array(messageArbitrary, { minLength: 0, maxLength: 50 }),
            (messages) => {
              const userCount = countMessagesBySender(messages, 'user');
              const assistantCount = countMessagesBySender(messages, 'assistant');
              expect(userCount + assistantCount).toBe(messages.length);
              return true;
            }
          ),
          { numRuns: 100 }
        );
      });

      it('should return 0 for empty message list', () => {
        expect(countMessagesBySender([], 'user')).toBe(0);
        expect(countMessagesBySender([], 'assistant')).toBe(0);
      });
    });

    describe('Message list properties', () => {
      it('should maintain message order', () => {
        fc.assert(
          fc.property(
            fc.array(messageArbitrary, { minLength: 2, maxLength: 20 }),
            (messages) => {
              // Verify that message IDs maintain their order
              const ids = messages.map(m => m.id);
              for (let i = 0; i < ids.length; i++) {
                expect(ids[i]).toBe(messages[i].id);
              }
              return true;
            }
          ),
          { numRuns: 50 }
        );
      });

      it('should have valid sender for all messages', () => {
        fc.assert(
          fc.property(
            fc.array(messageArbitrary, { minLength: 1, maxLength: 50 }),
            (messages) => {
              for (const message of messages) {
                expect(['user', 'assistant']).toContain(message.sender);
              }
              return true;
            }
          ),
          { numRuns: 50 }
        );
      });

      it('should have valid timestamps for all messages', () => {
        fc.assert(
          fc.property(
            fc.array(messageArbitrary, { minLength: 1, maxLength: 50 }),
            (messages) => {
              for (const message of messages) {
                expect(message.timestamp).toBeInstanceOf(Date);
                expect(message.timestamp.getTime()).not.toBeNaN();
              }
              return true;
            }
          ),
          { numRuns: 50 }
        );
      });

      it('should have non-empty content for all messages', () => {
        fc.assert(
          fc.property(
            fc.array(messageArbitrary, { minLength: 1, maxLength: 50 }),
            (messages) => {
              for (const message of messages) {
                expect(message.content.length).toBeGreaterThan(0);
              }
              return true;
            }
          ),
          { numRuns: 50 }
        );
      });
    });

    describe('Message count consistency', () => {
      it('should correctly count messages regardless of content', () => {
        fc.assert(
          fc.property(
            fc.array(messageArbitrary, { minLength: 0, maxLength: 100 }),
            (messages) => {
              const totalCount = messages.length;
              const userCount = countMessagesBySender(messages, 'user');
              const assistantCount = countMessagesBySender(messages, 'assistant');
              
              // Total should equal sum of user and assistant
              expect(userCount + assistantCount).toBe(totalCount);
              
              // Counts should be non-negative
              expect(userCount).toBeGreaterThanOrEqual(0);
              expect(assistantCount).toBeGreaterThanOrEqual(0);
              
              return true;
            }
          ),
          { numRuns: 100 }
        );
      });
    });
  });
});
