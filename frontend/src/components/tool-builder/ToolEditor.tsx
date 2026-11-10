import Editor, { OnMount } from '@monaco-editor/react';
import { useRef, useState } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock } from '@/components/ds/kit';
import { useTheme } from '@/components/ThemeProvider';
import { cn } from '@/lib/utils';
import { TOOL_HELPER_REFERENCE } from './typings';

interface Props {
  value: string;
  onChange: (next: string) => void;
  height?: string;
  readOnly?: boolean;
}

/**
 * Python editor for a tool, with the injected helpers listed beside it
 * (below it on small screens, behind a toggle).
 */
export default function ToolEditor({ value, onChange, height = '60vh', readOnly = false }: Props) {
  const editorRef = useRef<unknown>(null);
  const [showHelp, setShowHelp] = useState(true);
  // Re-render when the theme changes; the class on <html> says which one is on.
  useTheme();
  const dark = typeof document === 'undefined' || document.documentElement.classList.contains('dark');
  const fill = height === '100%';

  const handleMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    // Real Python language support is not available in the browser editor,
    // so the helper reference beside it is the guide.
    void monaco;
  };

  return (
    <div className={cn('grid min-h-0 gap-4', fill && 'h-full', showHelp ? 'grid-rows-[minmax(0,1fr)_auto] lg:grid-cols-[minmax(0,1fr)_320px] lg:grid-rows-1' : 'grid-cols-1')}>
      <div className={cn('relative min-h-[300px] overflow-hidden rounded-xl border border-border bg-card', fill && 'h-full')}>
        <Editor
          height={height}
          defaultLanguage="python"
          value={value}
          theme={dark ? 'vs-dark' : 'light'}
          onChange={(v) => onChange(v ?? '')}
          onMount={handleMount}
          loading={<Skeleton className="h-full w-full rounded-none" />}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            tabSize: 4,
            insertSpaces: true,
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            renderWhitespace: 'selection',
            padding: { top: 12, bottom: 12 },
            readOnly,
          }}
        />
        {!showHelp && (
          <button
            type="button"
            onClick={() => setShowHelp(true)}
            className="absolute right-3 top-3 inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-popover px-2 text-xs text-muted-foreground shadow-xs transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Icon name="help" className="h-3.5 w-3.5" /> Helpers
          </button>
        )}
      </div>

      {showHelp && (
        <aside className={cn('flex min-h-0 flex-col', fill ? 'max-h-56 lg:max-h-none' : '')} style={fill ? undefined : { maxHeight: height }} aria-label="Helpers reference">
          <div className="mb-2 flex items-center justify-between gap-3">
            <h3 className="text-sm font-medium text-foreground">Helpers you can call</h3>
            <button
              type="button"
              onClick={() => setShowHelp(false)}
              aria-label="Hide the helpers reference"
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Icon name="close" className="h-3.5 w-3.5" />
            </button>
          </div>
          <p className="mb-2 text-xs text-muted-foreground">Every tool is an async Python function. These objects are passed to it on each run.</p>
          <div className="scroll-thin min-h-0 flex-1 overflow-auto rounded-lg lg:pb-16">
            <CodeBlock wrap maxHeight={2000}>{TOOL_HELPER_REFERENCE}</CodeBlock>
          </div>
        </aside>
      )}
    </div>
  );
}
