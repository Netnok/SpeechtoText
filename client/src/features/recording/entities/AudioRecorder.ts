export interface AudioRecorder {
    start(options?: { timeSliceMs?: number }): void;
    stop(): void;
    pause(): void;
    resume(): void;
    destroy(): void;

    onStop(callback: (blob: Blob) => void): void;
    onChunkReady(callback: (chunk: Blob, startTime: number, endTime: number) => void): void;
    onError(callback: (error: Error) => void): void;
}

