export const uploadKeys = {
  all: ['upload'] as const,
  capabilities: () => [...uploadKeys.all, 'capabilities'] as const,
};
