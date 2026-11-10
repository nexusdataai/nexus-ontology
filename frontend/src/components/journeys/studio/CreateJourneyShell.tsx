/**
 * The one look of every "New journey" dialog. Presentational: each Create*
 * dialog keeps its own state and submit logic and renders through this shell.
 */
import type { ReactNode } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Icon } from '@/components/ds/Icon';
import { Field, InlineError } from '@/components/ds/kit';
import { sentenceCase } from './format';

interface CreateJourneyShellProps {
  open: boolean;
  onClose: () => void;
  /** e.g. "New Order-to-Cash Journey". Shown in sentence case. */
  title: string;
  description?: string;
  name: string;
  onNameChange: (value: string) => void;
  namePlaceholder?: string;
  /** What the journey does, one line per step: "Name (what it does)". */
  steps?: string[];
  error?: string | null;
  isSubmitting?: boolean;
  onSubmit: () => void;
  /** Extra fields under the name. */
  children?: ReactNode;
}

function splitStep(line: string): { name: string; hint: string } {
  const m = line.match(/^(.*?)\s*\((.*)\)\s*$/);
  if (!m) return { name: sentenceCase(line), hint: '' };
  const hint = m[2].trim();
  return { name: sentenceCase(m[1]), hint: hint ? hint.charAt(0).toUpperCase() + hint.slice(1) : '' };
}

export function CreateJourneyShell({
  open, onClose, title, description, name, onNameChange, namePlaceholder, steps, error, isSubmitting, onSubmit, children,
}: CreateJourneyShellProps) {
  const cleanTitle = sentenceCase(title.replace(/\s*&\s*/g, ' and '));
  const count = steps?.length || 0;
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="flex max-h-[90dvh] flex-col gap-0 p-0 sm:max-w-[500px]">
        <DialogHeader className="border-b border-border px-5 pb-4 pt-5 pr-12 text-left">
          <DialogTitle className="text-xl font-medium tracking-tight">{cleanTitle}</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            {description || (count > 0
              ? `Runs ${count} automated steps. You can run it now or put it on a schedule once it is created.`
              : 'You can run it now or put it on a schedule once it is created.')}
          </DialogDescription>
        </DialogHeader>

        <form
          className="scroll-thin min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5"
          onSubmit={(e) => { e.preventDefault(); if (!isSubmitting) onSubmit(); }}
        >
          <Field label="Journey name" htmlFor="new-journey-name">
            <Input id="new-journey-name" value={name} onChange={(e) => onNameChange(e.target.value)} placeholder={namePlaceholder} autoFocus />
          </Field>

          {children}

          {count > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-medium text-muted-foreground">What it runs</h3>
              <ol className="border-y border-border">
                {steps!.map((line, i) => {
                  const s = splitStep(line);
                  return (
                    <li key={i} className="flex items-baseline gap-3 border-b border-border py-2 text-sm last:border-b-0">
                      <span className="num w-4 shrink-0 text-right text-xs text-subtle-foreground">{i + 1}</span>
                      <span className="min-w-0">
                        <span className="text-foreground">{s.name}</span>
                        {s.hint && <span className="block text-xs text-muted-foreground">{s.hint}</span>}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </div>
          )}

          {error && <InlineError>{error}</InlineError>}
          {/* Lets Enter in the name field submit the form. */}
          <button type="submit" className="sr-only" tabIndex={-1} aria-hidden="true">Create journey</button>
        </form>

        <DialogFooter className="gap-2 border-t border-border px-5 py-3 sm:gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={onSubmit} disabled={isSubmitting}>
            {isSubmitting && <Icon name="spinner" className="animate-spin" />}
            Create journey
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default CreateJourneyShell;
