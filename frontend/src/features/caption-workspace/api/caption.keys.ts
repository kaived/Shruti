export const workspaceKeys = {
  all: ['workspace'] as const,
  results: (jobId: string) => [...workspaceKeys.all, 'results', jobId] as const,
  artifact: (jobId: string, name: string) => [...workspaceKeys.all, 'artifact', jobId, name] as const,
};
