/**
 * FeatureAccessList Component
 *
 * Features against the current plan: what is included and what is not.
 * A plain list with a check or a dash, grouped, divided by hairlines.
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4
 */

import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import {
  FeatureAccessListProps,
  FeatureAccessItem,
  LicenseTier,
  TIER_LABELS,
  compareTiers
} from '@/types/license';

// ============================================================================
// Helper Functions
// ============================================================================

function getTierLabel(tier: LicenseTier): string {
  return TIER_LABELS[tier] || tier;
}

// ============================================================================
// Feature Item Component
// ============================================================================

interface FeatureItemProps {
  feature: FeatureAccessItem;
  currentTier: LicenseTier | null;
  index: number;
}

function FeatureItem({ feature, currentTier, index }: FeatureItemProps) {
  const isAccessible = compareTiers(currentTier, feature.required_tier);

  return (
    <li
      className="rise flex items-start gap-3 border-b border-border py-3.5"
      style={{ '--i': index } as React.CSSProperties}
      data-testid={`feature-item-${feature.feature_id}`}
      data-accessible={isAccessible}
    >
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center">
        {isAccessible ? (
          <Icon name="check" label="Included" className="h-4 w-4 text-success" data-testid="accessible-icon" />
        ) : (
          <Icon name="minus" label="Not included" className="h-4 w-4 text-subtle-foreground" data-testid="locked-icon" />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <h4 className={`text-sm font-medium ${isAccessible ? 'text-foreground' : 'text-muted-foreground'}`}>
          {feature.feature_name}
        </h4>
        <p className="mt-0.5 text-sm text-muted-foreground">{feature.description}</p>
        {!isAccessible && (
          <p className="mt-1 text-xs text-primary dark:text-brand-hi" data-testid="upgrade-message">
            Upgrade to {getTierLabel(feature.required_tier)} to unlock
          </p>
        )}
      </div>
      <span className="shrink-0 whitespace-nowrap pt-0.5 text-xs text-muted-foreground" data-testid="tier-badge">
        {getTierLabel(feature.required_tier)}
      </span>
    </li>
  );
}

function Group({ title, count, features, currentTier }: { title: string; count: number; features: FeatureAccessItem[]; currentTier: LicenseTier | null }) {
  return (
    <section>
      <div className="flex items-baseline justify-between gap-3 border-b border-border pb-2">
        <h3 className="text-sm font-medium text-foreground">
          {title} <span className="num font-normal text-muted-foreground">({count})</span>
        </h3>
        <span className="text-xs text-muted-foreground">From plan</span>
      </div>
      <ul>
        {features.map((feature, i) => (
          <FeatureItem key={feature.feature_id} feature={feature} currentTier={currentTier} index={i} />
        ))}
      </ul>
    </section>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function FeatureAccessList({
  currentTier,
  features,
  isLoading
}: FeatureAccessListProps) {
  // Group features by accessibility
  const accessibleFeatures = features.filter(f => compareTiers(currentTier, f.required_tier));
  const lockedFeatures = features.filter(f => !compareTiers(currentTier, f.required_tier));

  return (
    <div className="max-w-3xl" data-testid="feature-access-list">
      <p className="text-sm text-muted-foreground">
        {currentTier
          ? <>What the <span className="font-medium text-foreground">{getTierLabel(currentTier)}</span> plan includes, and what a higher plan would add.</>
          : 'What each plan includes.'}
      </p>

      {isLoading ? (
        <div className="mt-5 space-y-3" aria-busy="true">
          {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      ) : features.length === 0 ? (
        <EmptyState className="mt-5" icon="list" title="No features to show" description="This installation does not list any licensed features." />
      ) : (
        <div className="mt-6 space-y-8">
          {/* No tier message */}
          {!currentTier && (
            <p className="flex items-start gap-2 text-sm text-muted-foreground">
              <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0 text-subtle-foreground" />
              Activate a license to unlock features.
            </p>
          )}

          {accessibleFeatures.length > 0 && (
            <Group title="Included in your plan" count={accessibleFeatures.length} features={accessibleFeatures} currentTier={currentTier} />
          )}

          {lockedFeatures.length > 0 && (
            <Group title="Not included" count={lockedFeatures.length} features={lockedFeatures} currentTier={currentTier} />
          )}
        </div>
      )}
    </div>
  );
}

export default FeatureAccessList;
