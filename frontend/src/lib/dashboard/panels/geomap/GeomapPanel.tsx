import { useMemo, useState, useCallback } from 'react';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { CHART_COLORS } from '@/components/ds/charts';
import { PanelState } from '../_shared';

interface MapPoint {
  lat: number;
  lng: number;
  label: string;
  value?: number;
  color: string;
  size: number;
}

const POINT_COLORS = CHART_COLORS;

function mercatorX(lng: number, width: number): number {
  return ((lng + 180) / 360) * width;
}

function mercatorY(lat: number, height: number): number {
  const latRad = (lat * Math.PI) / 180;
  const mercN = Math.log(Math.tan(Math.PI / 4 + latRad / 2));
  return (height / 2) - (height * mercN) / (2 * Math.PI);
}

export function GeomapPanel({ data, options, width, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length < 2) {
    return (
      <PanelState loading={loading} text="No data (need latitude and longitude fields)" />
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const fieldNames = frame.fields.map((f) => f.name);

  const latField = (options.latField as string) || fieldNames.find((n) => /lat/i.test(n)) || fieldNames[0];
  const lngField = (options.lngField as string) || fieldNames.find((n) => /lng|lon/i.test(n)) || (fieldNames.length > 1 ? fieldNames[1] : fieldNames[0]);
  const labelField = (options.labelField as string) || fieldNames.find((n) => /name|label|title|city|location/i.test(n));
  const valueField = (options.valueField as string) || fieldNames.find((n) => /value|size|count|amount/i.test(n));
  const colorField = (options.colorField as string) || fieldNames.find((n) => /group|type|category|status/i.test(n));
  const basePointSize = (options.pointSize as number) ?? 6;

  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const { points, bounds } = useMemo(() => {
    const colorMap: Record<string, string> = {};
    let colorIdx = 0;
    const pts: MapPoint[] = [];
    let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;

    for (const row of rows) {
      const lat = Number(row[latField]);
      const lng = Number(row[lngField]);
      if (isNaN(lat) || isNaN(lng)) continue;

      const label = labelField ? String(row[labelField] ?? '') : `${lat.toFixed(2)}, ${lng.toFixed(2)}`;
      const value = valueField ? Number(row[valueField]) : undefined;

      let color = POINT_COLORS[0];
      if (colorField && row[colorField]) {
        const key = String(row[colorField]);
        if (!colorMap[key]) {
          colorMap[key] = POINT_COLORS[colorIdx % POINT_COLORS.length];
          colorIdx++;
        }
        color = colorMap[key];
      }

      let size = basePointSize;
      if (value !== undefined && !isNaN(value)) {
        size = Math.max(basePointSize, Math.min(basePointSize + Math.sqrt(Math.abs(value)) * 0.5, 24));
      }

      pts.push({ lat, lng, label, value, color, size });
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
      if (lng < minLng) minLng = lng;
      if (lng > maxLng) maxLng = lng;
    }

    const latPad = Math.max((maxLat - minLat) * 0.15, 5);
    const lngPad = Math.max((maxLng - minLng) * 0.15, 5);

    return {
      points: pts,
      bounds: {
        minLat: minLat - latPad,
        maxLat: maxLat + latPad,
        minLng: minLng - lngPad,
        maxLng: maxLng + lngPad,
      },
    };
  }, [rows, latField, lngField, labelField, valueField, colorField, basePointSize]);

  const svgH = height - 16;
  const svgW = width;

  const projectX = useCallback(
    (lng: number) => {
      const fullX1 = mercatorX(bounds.minLng, 1000);
      const fullX2 = mercatorX(bounds.maxLng, 1000);
      const px = mercatorX(lng, 1000);
      return ((px - fullX1) / (fullX2 - fullX1)) * svgW;
    },
    [bounds, svgW],
  );

  const projectY = useCallback(
    (lat: number) => {
      const fullY1 = mercatorY(bounds.maxLat, 1000);
      const fullY2 = mercatorY(bounds.minLat, 1000);
      const py = mercatorY(lat, 1000);
      return ((py - fullY1) / (fullY2 - fullY1)) * svgH;
    },
    [bounds, svgH],
  );

  if (points.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        No valid coordinates found
      </div>
    );
  }

  return (
    <div className="relative h-full w-full overflow-hidden">
      <svg width={svgW} height={svgH} className="bg-muted/10 rounded">
        <rect x={0} y={0} width={svgW} height={svgH} fill="none" stroke="currentColor" strokeOpacity={0.1} rx={4} />

        {/* Grid lines */}
        {Array.from({ length: 7 }, (_, i) => {
          const lng = bounds.minLng + ((bounds.maxLng - bounds.minLng) * (i + 1)) / 8;
          const x = projectX(lng);
          return <line key={`vg-${i}`} x1={x} y1={0} x2={x} y2={svgH} stroke="currentColor" strokeOpacity={0.05} />;
        })}
        {Array.from({ length: 5 }, (_, i) => {
          const lat = bounds.minLat + ((bounds.maxLat - bounds.minLat) * (i + 1)) / 6;
          const y = projectY(lat);
          return <line key={`hg-${i}`} x1={0} y1={y} x2={svgW} y2={y} stroke="currentColor" strokeOpacity={0.05} />;
        })}

        {points.map((pt, i) => {
          const cx = projectX(pt.lng);
          const cy = projectY(pt.lat);
          const isHovered = hoveredIdx === i;
          return (
            <g
              key={i}
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
              style={{ cursor: 'pointer' }}
            >
              <circle
                cx={cx}
                cy={cy}
                r={isHovered ? pt.size + 2 : pt.size}
                fill={pt.color}
                fillOpacity={0.7}
                stroke={pt.color}
                strokeWidth={isHovered ? 2 : 1}
                strokeOpacity={0.9}
              />
              {isHovered && (
                <>
                  <rect
                    x={cx + pt.size + 4}
                    y={cy - 14}
                    width={Math.max(pt.label.length * 5.5 + 16, 60)}
                    height={pt.value !== undefined ? 28 : 18}
                    rx={3}
                    fill="hsl(var(--background))"
                    stroke="hsl(var(--border))"
                    strokeWidth={1}
                  />
                  <text
                    x={cx + pt.size + 10}
                    y={cy - 2}
                    className="fill-foreground"
                    fontSize={10}
                    fontWeight={500}
                  >
                    {pt.label}
                  </text>
                  {pt.value !== undefined && (
                    <text
                      x={cx + pt.size + 10}
                      y={cy + 10}
                      className="fill-muted-foreground"
                      fontSize={9}
                    >
                      Value: {pt.value.toFixed(2)}
                    </text>
                  )}
                </>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
