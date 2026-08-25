import { PipelineStatus } from '@core/types';

export function formatReportData(status: PipelineStatus): string {
  return `Jobs: [Completed: ${status.completedJobs}, Active: ${status.activeJobs}, Failed: ${status.failedJobs}] (Uptime: ${status.uptimeSeconds}s)`;
}

export function sanitizeInput(raw: string): string {
  return raw.trim().replace(/[\r\n\t]+/g, ' ');
}
