/**
 * Simple test for the updated TMF ODA HTTP service
 */

import { tmfOdaHttpService } from './tmfOdaHttpService';

export async function testTmfOdaHttpService() {
  console.log('🧪 Testing TMF ODA HTTP Service...');
  
  try {
    // Test 1: Health check
    console.log('1. Testing health check...');
    const isHealthy = await tmfOdaHttpService.healthCheck();
    console.log(`   Health check: ${isHealthy ? '✅ Healthy' : '❌ Failed'}`);
    
    // Test 2: Get available tools
    console.log('2. Testing tools listing...');
    const tools = await tmfOdaHttpService.getAvailableTools();
    console.log(`   Available tools: ${tools.tools?.length || 0}`);
    
    // Test 3: Journey info
    console.log('3. Testing journey info...');
    const journeyInfo = await tmfOdaHttpService.fetchJourneyInfo();
    console.log(`   Journey info: ${journeyInfo.summary?.total_journeys || 0} journeys found`);
    
    // Test 4: Journey statistics
    console.log('4. Testing journey statistics...');
    const stats = await tmfOdaHttpService.getJourneyStatistics();
    console.log(`   Statistics: ${stats.totalJourneys || 0} total journeys`);
    
    // Test 5: Journey summaries
    console.log('5. Testing journey summaries...');
    const summaries = await tmfOdaHttpService.getJourneySummaries();
    console.log(`   Summaries: ${summaries.length} journey summaries`);
    
    console.log('✅ All tests completed successfully!');
    return true;
  } catch (error) {
    console.error('❌ Test failed:', error);
    return false;
  }
} 