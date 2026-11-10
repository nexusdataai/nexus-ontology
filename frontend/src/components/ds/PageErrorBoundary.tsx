import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ds/Icon';

interface State { error: Error | null }

/**
 * Catches a rendering error inside a page so the app shell (sidebar, top bar)
 * stays usable instead of the whole screen going blank.
 * Reset by navigating: Layout passes the pathname as `resetKey`.
 */
export class PageErrorBoundary extends React.Component<{ resetKey?: string; children: React.ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidUpdate(prev: { resetKey?: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Page failed to render:', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="page">
        <div role="alert" className="mx-auto mt-10 max-w-lg rounded-xl border border-border bg-card p-6">
          <div className="flex items-center gap-2.5 text-destructive">
            <Icon name="alert-triangle" className="h-[18px] w-[18px]" />
            <h2 className="text-md font-medium text-foreground">This page could not be displayed</h2>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Something went wrong while showing this screen. The rest of the app is still available from the menu.
          </p>
          <pre className="scroll-thin mt-3 max-h-32 overflow-auto rounded-md bg-surface-2 p-3 font-mono text-xs text-muted-foreground">{this.state.error.message}</pre>
          <div className="mt-4 flex gap-2">
            <Button size="sm" onClick={() => this.setState({ error: null })}>Try again</Button>
            <Button size="sm" variant="outline" onClick={() => window.location.reload()}>Reload page</Button>
          </div>
        </div>
      </div>
    );
  }
}

export default PageErrorBoundary;
