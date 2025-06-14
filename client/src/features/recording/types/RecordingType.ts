export type RecordingChunk = {
    id: string;         // uuid 등으로 식별
    audioUrl: string;
    startTime: number;  // ms
    endTime: number;    // ms
    transcript?: string;
    aiResponse?: string;
};

export type RecordingStatus = 'idle' | 'recording' | 'paused' | 'stopped';