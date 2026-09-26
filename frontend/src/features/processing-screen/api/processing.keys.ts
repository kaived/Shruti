export const processingKeys = {
  all: ['processing'] as const,
  job: (jobId: string) => [...processingKeys.all, 'job', jobId] as const,
};
