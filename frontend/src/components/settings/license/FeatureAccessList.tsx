/**
 * FeatureAccessList Component
 * 
 * Displays features with tier requirements.
 * Shows accessible vs inaccessible features based on current tier.
 * 
 * Requirements: 6.1, 6.2, 6.3, 6.4
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Sparkles,
  CheckCircle,
  Lock,
  ArrowUpCircle,
  Loader2
} from 'lucide-react';
import { 
  FeatureAccessListProps, 
  FeatureAccessItem,
  LicenseTier,
  TIER_LABELS,
  TIER_LEVELS,
  compareTiers
} from '@/types/license';

// ============================================================================
// Helper Functions
// ============================================================================

function getTierBadgeColor(tier: LicenseTier): string {
  switch (tier) {
    case 'basic':
      return 'bg-gray-100 text-gray-700 border-gray-200';
    case 'professional':
      return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'enterprise':
      return 'bg-purple-100 text-purple-700 border-purple-200';
    default:
      return 'bg-gray-100 text-gray-700 border-gray-200';
  }
}

function getTierLabel(tier: LicenseTier): string {
  return TIER_LABELS[tier] || tier;
}

// ============================================================================
// Feature Item Component
// ============================================================================

interface FeatureItemProps {
  feature: FeatureAccessItem;
  currentTier: LicenseTier | null;
}

function FeatureItem({ feature, currentTier }: FeatureItemProps) {
  const isAccessible = compareTiers(currentTier, feature.required_tier);
  
  return (
    <div 
      className={`p-4 rounded-lg border ${
        isAccessible 
          ? 'bg-green-50 border-green-200' 
          : 'bg-gray-50 border-gray-200'
      }`}
      data-testid={`feature-item-${feature.feature_id}`}
      data-accessible={isAccessible}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            {isAccessible ? (
              <CheckCircle className="h-5 w-5 text-green-600" data-testid="accessible-icon" />
            ) : (
              <Lock className="h-5 w-5 text-gray-400" data-testid="locked-icon" />
            )}
            <h4 className={`font-medium ${isAccessible ? 'text-green-900' : 'text-gray-600'}`}>
              {feature.feature_name}
            </h4>
          </div>
          <p className={`text-sm ${isAccessible ? 'text-green-700' : 'text-gray-500'}`}>
            {feature.description}
          </p>
          
          {/* Upgrade message for inaccessible features */}
          {!isAccessible && (
            <div 
              className="flex items-center gap-1 mt-2 text-xs text-blue-600"
              data-testid="upgrade-message"
            >
              <ArrowUpCircle className="h-3 w-3" />
              <span>Upgrade to {getTierLabel(feature.required_tier)} to unlock</span>
            </div>
          )}
        </div>
        
        {/* Required Tier Badge */}
        <Badge 
          variant="outline" 
          className={getTierBadgeColor(feature.required_tier)}
          data-testid="tier-badge"
        >
          {getTierLabel(feature.required_tier)}
        </Badge>
      </div>
    </div>
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
    <Card data-testid="feature-access-list">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          Feature Access
        </CardTitle>
        <CardDescription>
          Features available with your current license tier
          {currentTier && (
            <Badge 
              variant="outline" 
              className={`ml-2 ${getTierBadgeColor(currentTier)}`}
            >
              {getTierLabel(currentTier)}
            </Badge>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : features.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Sparkles className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No features available</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Accessible Features */}
            {accessibleFeatures.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  Available Features ({accessibleFeatures.length})
                </h3>
                <div className="space-y-3">
                  {accessibleFeatures.map((feature) => (
                    <FeatureItem 
                      key={feature.feature_id} 
                      feature={feature} 
                      currentTier={currentTier} 
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Locked Features */}
            {lockedFeatures.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                  <Lock className="h-4 w-4 text-gray-400" />
                  Locked Features ({lockedFeatures.length})
                </h3>
                <div className="space-y-3">
                  {lockedFeatures.map((feature) => (
                    <FeatureItem 
                      key={feature.feature_id} 
                      feature={feature} 
                      currentTier={currentTier} 
                    />
                  ))}
                </div>
              </div>
            )}

            {/* No tier message */}
            {!currentTier && features.length > 0 && (
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex items-center gap-2 text-yellow-800">
                  <ArrowUpCircle className="h-5 w-5" />
                  <p className="text-sm">
                    Activate a license to unlock features
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default FeatureAccessList;
