import { useMemo, useCallback } from 'react';
import { ResponsiveGridLayout, useContainerWidth, type Layout } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import type { PanelModel, GridPos } from '../model';
import type { TimeRange } from '../types';
import { PanelChrome } from './PanelChrome';

interface Props {
  panels: PanelModel[];
  timeRange?: TimeRange;
  isEditing: boolean;
  onLayoutChange: (panels: PanelModel[]) => void;
  onEditPanel: (panelId: number) => void;
  onDuplicatePanel: (panelId: number) => void;
  onRemovePanel: (panelId: number) => void;
}

const COLS = { lg: 24, md: 24, sm: 12, xs: 6 };
const BREAKPOINTS = { lg: 1200, md: 996, sm: 768, xs: 480 };
const ROW_HEIGHT = 30;

function panelToLayout(panel: PanelModel): Layout {
  return {
    i: String(panel.id),
    x: panel.gridPos.x,
    y: panel.gridPos.y,
    w: panel.gridPos.w,
    h: panel.gridPos.h,
    minW: 3,
    minH: 3,
  };
}

export function DashboardGrid({
  panels,
  timeRange,
  isEditing,
  onLayoutChange,
  onEditPanel,
  onDuplicatePanel,
  onRemovePanel,
}: Props) {
  const { width, containerRef } = useContainerWidth({ initialWidth: 1200 });

  const layouts = useMemo(
    () => ({ lg: panels.map(panelToLayout) }),
    [panels],
  );

  const handleLayoutChange = useCallback(
    (layout: Layout[]) => {
      const updated = panels.map((panel) => {
        const item = layout.find((l) => l.i === String(panel.id));
        if (!item) return panel;
        const newPos: GridPos = { x: item.x, y: item.y, w: item.w, h: item.h };
        if (
          newPos.x === panel.gridPos.x &&
          newPos.y === panel.gridPos.y &&
          newPos.w === panel.gridPos.w &&
          newPos.h === panel.gridPos.h
        ) {
          return panel;
        }
        return { ...panel, gridPos: newPos };
      });
      onLayoutChange(updated);
    },
    [panels, onLayoutChange],
  );

  if (panels.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 border-2 border-dashed border-border rounded-lg">
        <p className="text-sm text-muted-foreground">No panels. Click "Add Panel" to get started.</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} style={{ minHeight: 100 }}>
      {width > 0 && (
        <ResponsiveGridLayout
          className="layout"
          layouts={layouts}
          breakpoints={BREAKPOINTS}
          cols={COLS}
          rowHeight={ROW_HEIGHT}
          width={width}
          isDraggable={isEditing}
          isResizable={isEditing}
          onLayoutChange={handleLayoutChange}
          draggableHandle=".drag-handle"
          compactType="vertical"
          margin={[8, 8]}
        >
          {panels.map((panel) => (
            <div key={String(panel.id)} className="drag-handle">
              <PanelChrome
                panel={panel}
                width={panel.gridPos.w * (ROW_HEIGHT + 8)}
                height={panel.gridPos.h * (ROW_HEIGHT + 8)}
                timeRange={timeRange}
                isEditing={isEditing}
                onEdit={() => onEditPanel(panel.id)}
                onDuplicate={() => onDuplicatePanel(panel.id)}
                onRemove={() => onRemovePanel(panel.id)}
              />
            </div>
          ))}
        </ResponsiveGridLayout>
      )}
    </div>
  );
}
