import Editor, { OnMount } from '@monaco-editor/react';
import { useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { TOOL_HELPER_REFERENCE } from './typings';

interface Props {
  value: string;
  onChange: (next: string) => void;
  height?: string;
  readOnly?: boolean;
}

export default function ToolEditor({ value, onChange, height = '60vh', readOnly = false }: Props) {
  const editorRef = useRef<unknown>(null);

  const handleMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    // Surface the helper cheat-sheet as a hover-able comment block at the
    // top of an unsaved/empty tool. Real Python LSP isn't available in
    // browser Monaco, so we keep this aspirational and rely on the side
    // panel for reference.
    void monaco;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-3 h-full">
      <div className="border border-border rounded-md overflow-hidden">
        <Editor
          height={height}
          defaultLanguage="python"
          value={value}
          theme="vs-dark"
          onChange={(v) => onChange(v ?? '')}
          onMount={handleMount}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            tabSize: 4,
            insertSpaces: true,
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            renderWhitespace: 'selection',
            readOnly,
          }}
        />
      </div>
      <Card className="overflow-auto" style={{ maxHeight: height }}>
        <CardContent className="pt-3 pb-3">
          <div className="text-[11px] font-semibold text-muted-foreground uppercase mb-2">
            Helpers reference
          </div>
          <pre className="text-[10px] font-mono leading-snug whitespace-pre-wrap text-muted-foreground">
{TOOL_HELPER_REFERENCE}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
