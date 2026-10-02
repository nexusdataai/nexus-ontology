import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  MoreVertical,
  Settings,
  Moon,
  Sun,
  Download,
  HelpCircle,
  MessageSquare,
  Info,
  LogOut,
  User,
  BarChart3,
  RefreshCw,
  FileText,
  Shield,
  Bell,
  Globe,
  Monitor,
  Smartphone,
  Palette,
  Move,
  Eye,
  EyeOff,
  Save
} from 'lucide-react';
import { useTheme } from '@/hooks/use-theme';

interface MenuAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  action: () => void;
  category: 'theme' | 'data' | 'help' | 'settings' | 'profile' | 'system';
  description: string;
  enabled: boolean;
  order: number;
}

const CustomizableUserMenu: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [menuActions, setMenuActions] = useState<MenuAction[]>([]);
  const { theme, setTheme } = useTheme();

  // Define all available menu actions
  const defaultActions: MenuAction[] = [
    {
      id: 'theme-toggle',
      label: theme === 'dark' ? 'Light Mode' : 'Dark Mode',
      icon: theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />,
      action: () => setTheme(theme === 'dark' ? 'light' : 'dark'),
      category: 'theme',
      description: 'Switch between light and dark themes',
      enabled: true,
      order: 1
    },
    {
      id: 'profile-settings',
      label: 'Profile Settings',
      icon: <User className="h-4 w-4" />,
      action: () => console.log('Opening profile settings...'),
      category: 'profile',
      description: 'Manage your account and profile information',
      enabled: true,
      order: 2
    },
    {
      id: 'export-data',
      label: 'Export Dashboard',
      icon: <Download className="h-4 w-4" />,
      action: () => console.log('Exporting dashboard data...'),
      category: 'data',
      description: 'Export current dashboard data to CSV or PDF',
      enabled: true,
      order: 3
    },
    {
      id: 'refresh-data',
      label: 'Refresh Data',
      icon: <RefreshCw className="h-4 w-4" />,
      action: () => {
        console.log('Refreshing data...');
        // Simulate refresh
        setTimeout(() => console.log('Data refreshed!'), 1000);
      },
      category: 'data',
      description: 'Manually refresh all dashboard data',
      enabled: false,
      order: 4
    },
    {
      id: 'custom-dashboard',
      label: 'Dashboard Layout',
      icon: <BarChart3 className="h-4 w-4" />,
      action: () => console.log('Opening dashboard customization...'),
      category: 'settings',
      description: 'Customize dashboard layout and widgets',
      enabled: false,
      order: 5
    },
    {
      id: 'notifications',
      label: 'Notification Settings',
      icon: <Bell className="h-4 w-4" />,
      action: () => console.log('Opening notification settings...'),
      category: 'settings',
      description: 'Configure alerts and notification preferences',
      enabled: false,
      order: 6
    },
    {
      id: 'help-docs',
      label: 'Help & Documentation',
      icon: <HelpCircle className="h-4 w-4" />,
      action: () => window.open('https://docs.totogi.com', '_blank'),
      category: 'help',
      description: 'Access user guides and documentation',
      enabled: true,
      order: 7
    },
    {
      id: 'feedback',
      label: 'Send Feedback',
      icon: <MessageSquare className="h-4 w-4" />,
      action: () => console.log('Opening feedback form...'),
      category: 'help',
      description: 'Share your thoughts and suggestions',
      enabled: true,
      order: 8
    },
    {
      id: 'mobile-view',
      label: 'Mobile View',
      icon: <Smartphone className="h-4 w-4" />,
      action: () => console.log('Switching to mobile view...'),
      category: 'settings',
      description: 'Optimize interface for mobile devices',
      enabled: false,
      order: 9
    },
    {
      id: 'api-docs',
      label: 'API Documentation',
      icon: <FileText className="h-4 w-4" />,
      action: () => window.open('https://api.totogi.com/docs', '_blank'),
      category: 'help',
      description: 'View API documentation and integration guides',
      enabled: false,
      order: 10
    },
    {
      id: 'security-settings',
      label: 'Security & Privacy',
      icon: <Shield className="h-4 w-4" />,
      action: () => console.log('Opening security settings...'),
      category: 'profile',
      description: 'Manage password, 2FA, and privacy settings',
      enabled: false,
      order: 11
    },
    {
      id: 'about',
      label: 'About Totogi',
      icon: <Info className="h-4 w-4" />,
      action: () => console.log('Showing about dialog...'),
      category: 'system',
      description: 'Version information and company details',
      enabled: true,
      order: 12
    }
  ];

  // Load saved preferences from localStorage
  useEffect(() => {
    const savedPreferences = localStorage.getItem('userMenuPreferences');
    if (savedPreferences) {
      try {
        const parsed = JSON.parse(savedPreferences);
        setMenuActions(parsed);
      } catch (error) {
        console.error('Error loading menu preferences:', error);
        setMenuActions(defaultActions);
      }
    } else {
      setMenuActions(defaultActions);
    }
  }, [theme]); // Re-run when theme changes to update theme toggle

  // Save preferences to localStorage
  const savePreferences = (actions: MenuAction[]) => {
    localStorage.setItem('userMenuPreferences', JSON.stringify(actions));
    setMenuActions(actions);
  };

  // Toggle action enabled/disabled
  const toggleAction = (actionId: string) => {
    const updatedActions = menuActions.map(action =>
      action.id === actionId ? { ...action, enabled: !action.enabled } : action
    );
    savePreferences(updatedActions);
  };

  // Move action up in order
  const moveActionUp = (actionId: string) => {
    const actionIndex = menuActions.findIndex(action => action.id === actionId);
    if (actionIndex > 0) {
      const updatedActions = [...menuActions];
      [updatedActions[actionIndex - 1], updatedActions[actionIndex]] = 
      [updatedActions[actionIndex], updatedActions[actionIndex - 1]];
      
      // Update order numbers
      updatedActions.forEach((action, index) => {
        action.order = index + 1;
      });
      
      savePreferences(updatedActions);
    }
  };

  // Move action down in order
  const moveActionDown = (actionId: string) => {
    const actionIndex = menuActions.findIndex(action => action.id === actionId);
    if (actionIndex < menuActions.length - 1) {
      const updatedActions = [...menuActions];
      [updatedActions[actionIndex], updatedActions[actionIndex + 1]] = 
      [updatedActions[actionIndex + 1], updatedActions[actionIndex]];
      
      // Update order numbers
      updatedActions.forEach((action, index) => {
        action.order = index + 1;
      });
      
      savePreferences(updatedActions);
    }
  };

  // Get enabled actions sorted by order
  const enabledActions = menuActions
    .filter(action => action.enabled)
    .sort((a, b) => a.order - b.order);

  // Group actions by category for settings view
  const actionsByCategory = menuActions.reduce((acc, action) => {
    if (!acc[action.category]) {
      acc[action.category] = [];
    }
    acc[action.category].push(action);
    return acc;
  }, {} as Record<string, MenuAction[]>);

  const categoryLabels = {
    theme: '🎨 Appearance',
    profile: '👤 Profile & Account',
    data: '📊 Data & Analytics',
    settings: '⚙️ Dashboard Settings',
    help: '❓ Help & Support',
    system: 'ℹ️ System & Info'
  };

  return (
    <>
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild>
          <Button 
            variant="ghost" 
            size="sm"
            className="h-10 w-10 p-0 rounded-full hover:bg-secondary/50"
            title="Quick Actions Menu"
          >
            <MoreVertical className="h-5 w-5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent 
          align="end" 
          className="w-56 bg-background/95 backdrop-blur-sm border shadow-lg"
          sideOffset={8}
        >
          {enabledActions.length === 0 ? (
            <DropdownMenuItem disabled>
              <span className="text-muted-foreground">No actions enabled</span>
            </DropdownMenuItem>
          ) : (
            enabledActions.map((action, index) => (
              <div key={action.id}>
                <DropdownMenuItem
                  className="gap-2 cursor-pointer"
                  onClick={() => {
                    action.action();
                    setOpen(false);
                  }}
                >
                  {action.icon}
                  <span>{action.label}</span>
                </DropdownMenuItem>
                {index < enabledActions.length - 1 && index === 1 && <DropdownMenuSeparator />}
                {index < enabledActions.length - 1 && index === 4 && <DropdownMenuSeparator />}
              </div>
            ))
          )}
          
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="gap-2 cursor-pointer"
            onClick={() => {
              setSettingsOpen(true);
              setOpen(false);
            }}
          >
            <Settings className="h-4 w-4" />
            <span>Customize Menu</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Menu Customization Dialog */}
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Customize Quick Actions Menu
            </DialogTitle>
            <DialogDescription>
              Choose which actions appear in your quick menu and arrange them in your preferred order.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            {Object.entries(categoryLabels).map(([category, label]) => {
              const actions = actionsByCategory[category] || [];
              if (actions.length === 0) return null;
              
              return (
                <Card key={category}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">{label}</CardTitle>
                    <CardDescription>
                      {actions.filter(a => a.enabled).length} of {actions.length} actions enabled
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {actions.map((action) => (
                      <div 
                        key={action.id}
                        className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
                      >
                        <div className="flex items-center gap-3 flex-1">
                          {action.icon}
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{action.label}</span>
                              {action.enabled && (
                                <Badge variant="secondary" className="text-xs">Enabled</Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">
                              {action.description}
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          {action.enabled && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => moveActionUp(action.id)}
                                disabled={action.order === 1}
                                title="Move up"
                              >
                                ↑
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => moveActionDown(action.id)}
                                disabled={action.order === menuActions.length}
                                title="Move down"
                              >
                                ↓
                              </Button>
                            </>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleAction(action.id)}
                            title={action.enabled ? 'Disable' : 'Enable'}
                          >
                            {action.enabled ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              );
            })}
          </div>
          
          <DialogFooter>
            <div className="flex items-center justify-between w-full">
              <p className="text-sm text-muted-foreground">
                {enabledActions.length} actions enabled • Changes saved automatically
              </p>
              <Button onClick={() => setSettingsOpen(false)}>
                <Save className="h-4 w-4 mr-2" />
                Done
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default CustomizableUserMenu;