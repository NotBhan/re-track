import { ProcessingEngine } from '@core/engine';
import { ReportGenerator } from '@features/report';

export function runApplication(): string {
  const engine = new ProcessingEngine();
  const reporter = new ReportGenerator();
  const summary = reporter.generateSummaryReport(engine);
  return summary;
}

export const applicationSummary = runApplication();
