import type { AudioRecorder } from "./AudioRecorder.ts";

export class WebAudioRecorder implements AudioRecorder {
    private recorder: MediaRecorder | null = null;
    private stream: MediaStream | null = null;
    private stopCallback: ((blob: Blob) => void) | null = null;
    private errorCallback: ((error: Error) => void) | null = null;
    private chunkReadyCallback: ((chunk: Blob, start: number, end: number) => void) | null = null;

    // chunk용 타임스탬프 관리
    private recordingStartTime: number | null = null;
    private lastChunkTime: number | null = null;
    private chunks: Blob[] = [];

    async init(mimeType = 'audio/webm') {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.recorder = new MediaRecorder(this.stream, { mimeType });

        this.recorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                const now = Date.now();
                if (this.chunkReadyCallback && this.lastChunkTime !== null) {
                    this.chunkReadyCallback(e.data, this.lastChunkTime, now);
                }
                this.chunks.push(e.data);
                this.lastChunkTime = now;
            }
        };

        this.recorder.onstop = () => {
            const blob = new Blob(this.chunks, { type: this.recorder?.mimeType || 'audio/webm' });
            this.stopCallback?.(blob);
            this.chunks = [];
            this.recordingStartTime = null;
            this.lastChunkTime = null;
        };

        this.recorder.onerror = (e) => {
            this.errorCallback?.(e.error);
        };
    }

    onStop(cb: (blob: Blob) => void) {
        this.stopCallback = cb;
    }

    onChunkReady(cb: (chunk: Blob, start: number, end: number) => void) {
        this.chunkReadyCallback = cb;
    }

    onError(cb: (error: Error) => void) {
        this.errorCallback = cb;
    }

    async start(options?: { timeSliceMs?: number }) {
        if (!this.recorder) await this.init();
        this.chunks = [];
        this.recordingStartTime = Date.now();
        this.lastChunkTime = this.recordingStartTime;
        // chunk 주기 설정 (기본값 60초)
        const timeSlice = options?.timeSliceMs ?? 60000;
        this.recorder?.start(timeSlice);
    }

    pause() {
        this.recorder?.pause();
    }

    resume() {
        this.recorder?.resume();
    }

    stop() {
        this.recorder?.stop();
    }

    destroy() {
        this.recorder?.stream?.getTracks().forEach((t) => t.stop());
        this.recorder = null;
        this.stream = null;
        this.chunks = [];
        this.recordingStartTime = null;
        this.lastChunkTime = null;
    }
}
