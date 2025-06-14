// 1. /upload 요청 시 백엔드가 반환하는 응답 타입
export interface UploadResponse {
    job_id: string;
    message: string;
}

// 2. /result/{job_id} 요청 시 백엔드가 반환하는 응답 타입
export interface ResultResponse {
    status: 'Processing' | 'Completed' | 'Failed';
    transcription?: string;
    error?: string;
    error_detail?: string;
    detected_language?: string;
}