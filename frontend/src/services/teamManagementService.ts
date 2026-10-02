import { TeamMember, UserRole, EnterpriseProfile } from '@/types/auth';

/**
 * Team Management Service
 * Handles team hierarchy, member management, and access control
 */
export class TeamManagementService {
  private static instance: TeamManagementService;
  private teamCache: Map<string, TeamMember[]> = new Map();
  private cacheExpiry: Map<string, number> = new Map();
  private readonly CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

  public static getInstance(): TeamManagementService {
    if (!TeamManagementService.instance) {
      TeamManagementService.instance = new TeamManagementService();
    }
    return TeamManagementService.instance;
  }

  /**
   * Get team members for a specific manager
   */
  async getTeamMembers(managerId: string, role: UserRole): Promise<TeamMember[]> {
    // Check cache first
    const cacheKey = `${managerId}_${role}`;
    if (this.isCacheValid(cacheKey)) {
      return this.teamCache.get(cacheKey) || [];
    }

    try {
      let teamMembers: TeamMember[] = [];

      if (role === 'Executive') {
        // Executives can see all users
        teamMembers = await this.fetchAllUsers();
      } else if (role === 'SalesManager') {
        // Sales Managers can see their direct reports
        teamMembers = await this.fetchDirectReports(managerId);
      }

      // Update cache
      this.teamCache.set(cacheKey, teamMembers);
      this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION);

      return teamMembers;
    } catch (error) {
      console.error('Error fetching team members:', error);
      return [];
    }
  }

  /**
   * Check if a user is in the manager's team
   */
  async isInTeam(managerId: string, targetUserId: string, managerRole: UserRole): Promise<boolean> {
    const teamMembers = await this.getTeamMembers(managerId, managerRole);
    return teamMembers.some(member => member.id === targetUserId);
  }

  /**
   * Get user's immediate manager
   */
  async getUserManager(userId: string): Promise<TeamMember | null> {
    try {
      // This would typically call your backend API
      // For now, we'll return null as a placeholder
      return null;
    } catch (error) {
      console.error('Error fetching user manager:', error);
      return null;
    }
  }

  /**
   * Get all users under a manager (including sub-teams for Executives)
   */
  async getAllSubordinates(managerId: string, role: UserRole): Promise<TeamMember[]> {
    if (role === 'Executive') {
      return this.fetchAllUsers();
    } else if (role === 'SalesManager') {
      return this.fetchDirectReports(managerId);
    }
    return [];
  }

  /**
   * Update team member information
   */
  async updateTeamMember(memberId: string, updates: Partial<TeamMember>): Promise<void> {
    try {
      // This would typically call your backend API
      console.log('Updating team member:', memberId, updates);
      
      // Invalidate cache for affected managers
      this.invalidateCache();
    } catch (error) {
      console.error('Error updating team member:', error);
      throw error;
    }
  }

  /**
   * Assign user to team/manager
   */
  async assignUserToManager(userId: string, managerId: string): Promise<void> {
    try {
      // This would typically call your backend API
      console.log('Assigning user to manager:', userId, managerId);
      
      // Invalidate cache
      this.invalidateCache();
    } catch (error) {
      console.error('Error assigning user to manager:', error);
      throw error;
    }
  }

  /**
   * Remove user from team
   */
  async removeUserFromTeam(userId: string, managerId: string): Promise<void> {
    try {
      // This would typically call your backend API
      console.log('Removing user from team:', userId, managerId);
      
      // Invalidate cache
      this.invalidateCache();
    } catch (error) {
      console.error('Error removing user from team:', error);
      throw error;
    }
  }

  /**
   * Get team hierarchy for organizational chart
   */
  async getTeamHierarchy(rootUserId?: string): Promise<TeamHierarchyNode> {
    try {
      // This would build the organizational hierarchy
      // For now, return a simple structure
      return {
        user: {
          id: rootUserId || 'root',
          email: 'root@company.com',
          full_name: 'Organization Root',
          role: 'Executive',
          department: 'Management',
          lastActive: new Date().toISOString()
        },
        children: []
      };
    } catch (error) {
      console.error('Error fetching team hierarchy:', error);
      throw error;
    }
  }

  /**
   * Private Methods
   */

  private async fetchAllUsers(): Promise<TeamMember[]> {
    try {
      // In a real implementation, this would call your backend API
      // or query Cognito User Pool with proper pagination
      
      const users = await this.queryCognitoUsers();
      return users.map(this.mapCognitoUserToTeamMember);
    } catch (error) {
      console.error('Error fetching all users:', error);
      return [];
    }
  }

  private async fetchDirectReports(managerId: string): Promise<TeamMember[]> {
    try {
      // Query users where custom:manager_id = managerId
      const users = await this.queryCognitoUsersByManager(managerId);
      return users.map(this.mapCognitoUserToTeamMember);
    } catch (error) {
      console.error('Error fetching direct reports:', error);
      return [];
    }
  }

  private async queryCognitoUsers(): Promise<any[]> {
    try {
      // This would use AWS SDK to query Cognito User Pool
      // For now, return empty array as placeholder
      
      // Example implementation would be:
      // const cognito = new AWS.CognitoIdentityServiceProvider();
      // const result = await cognito.listUsers({
      //   UserPoolId: 'your-user-pool-id',
      //   Limit: 60
      // }).promise();
      // return result.Users || [];
      
      return [];
    } catch (error) {
      console.error('Error querying Cognito users:', error);
      return [];
    }
  }

  private async queryCognitoUsersByManager(managerId: string): Promise<any[]> {
    try {
      // Query Cognito users with filter for manager_id
      // This would use Cognito's ListUsers API with AttributesToGet and Filter
      
      return [];
    } catch (error) {
      console.error('Error querying users by manager:', error);
      return [];
    }
  }

  private mapCognitoUserToTeamMember(cognitoUser: any): TeamMember {
    const attributes = this.parseUserAttributes(cognitoUser.Attributes || []);
    
    return {
      id: cognitoUser.Username,
      email: attributes.email || '',
      full_name: attributes.name || attributes.given_name || '',
      role: this.mapCognitoRoleToUserRole(attributes['custom:role']),
      department: attributes['custom:department'] || 'Unknown',
      lastActive: cognitoUser.UserLastModifiedDate || new Date().toISOString(),
      performanceScore: this.calculatePerformanceScore(cognitoUser)
    };
  }

  private parseUserAttributes(attributes: any[]): Record<string, string> {
    return attributes.reduce((acc, attr) => {
      acc[attr.Name] = attr.Value;
      return acc;
    }, {});
  }

  private mapCognitoRoleToUserRole(role: string): UserRole {
    switch (role) {
      case 'Executive':
      case 'SalesManager':
      case 'Rep':
        return role as UserRole;
      default:
        return 'Rep';
    }
  }

  private calculatePerformanceScore(cognitoUser: any): number {
    // This would calculate performance based on user data
    // For now, return a random score between 70-100
    return Math.floor(Math.random() * 30) + 70;
  }

  private isCacheValid(cacheKey: string): boolean {
    const expiry = this.cacheExpiry.get(cacheKey);
    return expiry ? Date.now() < expiry : false;
  }

  private invalidateCache(): void {
    this.teamCache.clear();
    this.cacheExpiry.clear();
  }

  /**
   * Clear all caches (useful for testing or force refresh)
   */
  public clearCache(): void {
    this.invalidateCache();
  }
}

// Types for team hierarchy
export interface TeamHierarchyNode {
  user: TeamMember;
  children: TeamHierarchyNode[];
  level?: number;
}

// Export singleton instance
export const teamManagementService = TeamManagementService.getInstance();
