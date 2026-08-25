import { ProcessingEngine } from '@core/engine';
import { PipelineStatus } from '@core/types';
import { formatReportData } from '@shared/format';

export class ReportGenerator {
  public generateSummaryReport(engine: ProcessingEngine): string {
    const status: PipelineStatus = engine.execute();
    return formatReportData(status);
  }
}
