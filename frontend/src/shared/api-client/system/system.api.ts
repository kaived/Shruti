import { HealthSchema, ReadinessSchema } from '../core/contracts';
import type { Health, Readiness } from '../core/contracts';
import { apiRequest } from '../core/http';

export async function fetchHealth(): Promise<Health> {
  return apiRequest('/api/health', HealthSchema, { cache: 'no-store' }, 'health');
}

export async function fetchReadiness(): Promise<Readiness> {
  return apiRequest('/api/readiness', ReadinessSchema, { cache: 'no-store' }, 'readiness');
}
