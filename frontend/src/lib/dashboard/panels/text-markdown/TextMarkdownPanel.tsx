import ReactMarkdown from 'react-markdown';
import type { PanelProps } from '../types';

const PROSE =
  'scroll-thin h-full overflow-auto px-4 pb-4 pt-1 text-sm leading-relaxed text-muted-foreground ' +
  '[&_strong]:font-medium [&_strong]:text-foreground [&_p]:mb-2.5 [&_p:last-child]:mb-0 ' +
  '[&_h1]:mb-2 [&_h1]:text-md [&_h1]:font-medium [&_h1]:text-foreground [&_h2]:mb-2 [&_h2]:text-sm [&_h2]:font-medium [&_h2]:text-foreground ' +
  '[&_h3]:mb-1.5 [&_h3]:text-sm [&_h3]:font-medium [&_h3]:text-foreground [&_ul]:mb-2.5 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mb-2.5 [&_ol]:list-decimal [&_ol]:pl-5 ' +
  '[&_li]:mb-1 [&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4 dark:[&_a]:text-brand-hi [&_code]:rounded [&_code]:bg-surface-2 [&_code]:px-1 [&_code]:font-mono [&_code]:text-xs';

/** A note on a dashboard, written in Markdown (or HTML when the panel says so). */
export function TextMarkdownPanel({ options }: PanelProps) {
  const content = (options.content as string) || 'Add a note for the people reading this dashboard.';
  const mode = (options.mode as string) || 'markdown';

  if (mode === 'html') {
    return <div className={PROSE} dangerouslySetInnerHTML={{ __html: content }} />;
  }
  return (
    <div className={PROSE}>
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
