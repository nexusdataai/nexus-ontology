import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '@/components/ds/Icon';
import {
  CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator,
} from '@/components/ui/command';
import { DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { NAV_GROUPS, SETTINGS_ITEM } from '@/config/navigation';
import { APP_REGISTRY } from '@/config/appRegistry';
import { useTheme } from '@/hooks/use-theme';

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Global search / jump-to. Opens with Ctrl+K (Cmd+K on macOS).
 * Navigation only: it does not call the backend.
 */
export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const nav = useNavigate();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onOpenChange]);

  const run = (fn: () => void) => {
    onOpenChange(false);
    fn();
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <DialogTitle className="sr-only">Search</DialogTitle>
      <DialogDescription className="sr-only">Jump to a page, a solution or an action.</DialogDescription>
      <CommandInput placeholder="Search or jump to…" />
      <CommandList className="scroll-thin max-h-[min(60dvh,420px)]">
        <CommandEmpty>No results.</CommandEmpty>

        {NAV_GROUPS.map(group => (
          <CommandGroup key={group.label} heading={group.label}>
            {group.items.map(item => (
              <CommandItem className="gap-2.5" key={item.id} value={`${item.name} ${item.hint || ''}`} onSelect={() => run(() => nav(item.path))}>
                <Icon name={item.icon} className="text-subtle-foreground" />
                <span>{item.name}</span>
                {item.hint && <span className="ml-auto hidden truncate pl-4 text-xs text-subtle-foreground sm:block">{item.hint}</span>}
              </CommandItem>
            ))}
          </CommandGroup>
        ))}

        <CommandSeparator />
        <CommandGroup heading="Solutions">
          {APP_REGISTRY.map(app => (
            <CommandItem className="gap-2.5" key={app.id} value={`${app.name} ${app.shortName} solution`} onSelect={() => run(() => nav(`/apps/${app.id}`))}>
              <app.icon className="text-subtle-foreground" />
              <span>{app.name}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />
        <CommandGroup heading="Actions">
          <CommandItem className="gap-2.5" value="settings preferences profile" onSelect={() => run(() => nav(SETTINGS_ITEM.path))}>
            <Icon name={SETTINGS_ITEM.icon} className="text-subtle-foreground" />
            <span>Open settings</span>
          </CommandItem>
          <CommandItem className="gap-2.5" value="design system components tokens reference" onSelect={() => run(() => nav('/design-system'))}>
            <Icon name="layers" className="text-subtle-foreground" />
            <span>Design system reference</span>
          </CommandItem>
          <CommandItem className="gap-2.5" value="toggle theme dark light appearance" onSelect={() => run(toggleTheme)}>
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} className="text-subtle-foreground" />
            <span>Switch to {theme === 'dark' ? 'light' : 'dark'} theme</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}

export default CommandPalette;
