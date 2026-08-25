export interface EngineConfig {
  maxWorkers: number;
  timeoutMs: number;
  bufferCapacity: number;
}

export interface PipelineStatus {
  activeJobs: number;
  completedJobs: number;
  failedJobs: number;
  uptimeSeconds: number;
}

export interface PipelineRunner {
  configure(config: EngineConfig): void;
  execute(): PipelineStatus;
}
