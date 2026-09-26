export const workspaceKeys = {
  all: ['workspace'] as const,
  results: (jobId: string) => [...workspaceKeys.all, 'results', jobId] as const,
};
