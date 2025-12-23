/**
 * Mock implementation for skills operations
 */

export const skillsMock = {
  skills: {
    list: async () => [],

    install: async (skillPath: string) => ({
      success: true,
      data: {
        output: `Mock: Installed skill from ${skillPath}`
      }
    }),

    remove: async (skillPath: string) => {
      console.log('[browser-mock] Removing skill:', skillPath);
      return { success: true };
    },

    getContent: async (skillPath: string) => ({
      success: true,
      data: {
        content: `# Mock Skill\n\nThis is a mock skill content for ${skillPath}`,
        name: 'Mock Skill',
        description: 'A mock skill for browser testing',
        category: 'development',
        version: '1.0.0'
      }
    })
  }
};
