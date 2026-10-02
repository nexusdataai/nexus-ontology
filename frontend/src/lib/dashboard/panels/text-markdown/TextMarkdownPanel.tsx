import type { PanelProps } from '../types';

export function TextMarkdownPanel({ options }: PanelProps) {
  const content = (options.content as string) || 'Enter some text...';
  const mode = (options.mode as string) || 'markdown';

  if (mode === 'html') {
    return (
      <div className="p-4 h-full overflow-auto prose prose-sm dark:prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: content }} />
    );
  }

  return (
    <div className="p-4 h-full overflow-auto">
      <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">{content}</div>
    </div>
  );
}
