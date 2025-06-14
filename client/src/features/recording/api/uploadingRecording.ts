// uploadingRecording.ts

import apiClient from "../../../shared/lib/api/apiClient";
import type { UploadResponse, ResultResponse } from './types';

export interface UploadRecordingParams {
    blob: Blob;
    filename?: string;
}

// Job ID를 반환하는 업로드 함수
export const uploadRecording = async (
    params: UploadRecordingParams
): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', params.blob, params.filename ?? 'recording.webm');
    const res = await apiClient.post<UploadResponse>('/upload', formData); 
    return res.data;
};

// 결과를 조회하는 함수
export const getResult = async (jobId: string): Promise<ResultResponse> => {
    const res = await apiClient.get<ResultResponse>(`/result/${jobId}`);
    return res.data;
};