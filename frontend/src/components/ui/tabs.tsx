import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"

import { cn } from "@/lib/utils"

/**
 * Tabs
 * ----------------------------------------------------------------------------
 * One tab component for the whole product, two looks:
 *  - variant="line"    (default for page-level sections) underline tabs
 *  - variant="segment" compact segmented control for switching a view in place
 *
 * Set the variant once on <TabsList>; triggers inherit it.
 * Long tab rows scroll horizontally on small screens instead of wrapping.
 */
type TabsVariant = "segment" | "line"

const TabsVariantContext = React.createContext<TabsVariant>("segment")

const Tabs = TabsPrimitive.Root

interface TabsListProps
  extends React.ComponentPropsWithoutRef<typeof TabsPrimitive.List> {
  variant?: TabsVariant
}

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  TabsListProps
>(({ className, variant = "segment", ...props }, ref) => (
  <TabsVariantContext.Provider value={variant}>
    <TabsPrimitive.List
      ref={ref}
      data-variant={variant}
      className={cn(
        "scrollbar-hide max-w-full overflow-x-auto text-muted-foreground",
        variant === "segment" &&
          "inline-flex h-9 items-center gap-0.5 rounded-lg border border-border bg-surface-2 p-0.5",
        variant === "line" &&
          "flex h-10 w-full items-stretch gap-5 border-b border-border",
        className
      )}
      {...props}
    />
  </TabsVariantContext.Provider>
))
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => {
  const variant = React.useContext(TabsVariantContext)
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-colors duration-200 ease-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
        variant === "segment" &&
          "h-full rounded-md px-3 hover:text-foreground data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-xs",
        variant === "line" &&
          "px-0.5 hover:text-foreground data-[state=active]:text-foreground after:absolute after:inset-x-0 after:-bottom-px after:h-0.5 after:origin-center after:scale-x-0 after:rounded-full after:bg-primary after:transition-transform after:duration-300 after:ease-brand-out data-[state=active]:after:scale-x-100",
        className
      )}
      {...props}
    />
  )
})
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-4 focus-visible:outline-none data-[state=active]:animate-fade-in",
      className
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
