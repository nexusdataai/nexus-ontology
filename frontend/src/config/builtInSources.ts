/**
 * Ids of the source systems the platform ships adapters for. The Data Plane
 * page describes each one; Home only needs to know how many there are, and
 * reads it from here so the two screens cannot disagree.
 */
export const BUILT_IN_SOURCE_IDS = ['sample-crm', 'sample-erp', 'sample-sap', 'sample-drive', 'sample-files', 'sample-social'] as const;
