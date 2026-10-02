// Test utility for cleaned relationships
export async function testCleanedRelationships() {
  try {
    console.log('🧪 Testing cleaned relationships...');
    
    // Load the cleaned relationships
    const response = await fetch('/TMF629_relationships.json');
    const data = await response.json();
    const relationships = data[0].consolidated_tmf629.relationships;
    
    console.log(`📊 Loaded ${relationships.length} cleaned relationships`);
    
    // Test 1: Verify no abstract entities
    const abstractEntities = ['PartyOrPartyRole', 'AttachmentRefOrValue', 'PartyRoleSpecificationRef'];
    const hasAbstractEntities = relationships.some((rel: any) => 
      abstractEntities.includes(rel.source) || abstractEntities.includes(rel.target)
    );
    
    console.log('✅ Test 1 - No abstract entities:', !hasAbstractEntities ? 'PASS' : 'FAIL');
    
    // Test 2: Check relationship types
    const relationshipTypes = [...new Set(relationships.map((rel: any) => rel.relationship))];
    console.log('📋 Relationship types found:', relationshipTypes);
    
    // Test 3: Sample relationships
    const sampleRels = relationships.slice(0, 5).map((rel: any) => 
      `${rel.source} --[${rel.relationship}]--> ${rel.target}`
    );
    console.log('🔗 Sample relationships:');
    sampleRels.forEach(rel => console.log(`  ${rel}`));
    
    // Test 4: Category distribution
    const byType = relationships.reduce((acc: any, rel: any) => {
      acc[rel.relationship] = (acc[rel.relationship] || 0) + 1;
      return acc;
    }, {});
    console.log('📈 Relationship type distribution:', byType);
    
    return {
      success: true,
      totalRelationships: relationships.length,
      relationshipTypes,
      hasAbstractEntities,
      distribution: byType
    };
    
  } catch (error) {
    console.error('❌ Test failed:', error);
    return { success: false, error };
  }
}

// Test the cleaned relationships when module loads
if (typeof window !== 'undefined') {
  // Only run in browser, not during SSR
  setTimeout(() => testCleanedRelationships(), 1000);
} 