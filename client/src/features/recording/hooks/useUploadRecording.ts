// src/features/recording/hooks/useUploadRecording.ts

import { useState, useCallback, useEffect, useRef } from 'react';
import { uploadRecording, getResult } from "../api/uploadingRecording";
import type { UploadResponse, ResultResponse } from '../api/types';

// 각 청크의 상태를 나타내는 타입 정의
export type ChunkStatus = 'idle' | 'uploading' | 'processing' | 'completed' | 'failed';

export const useUploadRecording = () => {
    const [transcripts, setTranscripts] = useState<Record<string, string>>({});
    const [statuses, setStatuses] = useState<Record<string, ChunkStatus>>({});
    const [errors, setErrors] = useState<Record<string, string>>({});
    const pollingIntervals = useRef<Record<string, number>>({});

    const pollForResult = useCallback((chunkId: string, jobId: string) => {
        if (pollingIntervals.current[chunkId]) {
            clearInterval(pollingIntervals.current[chunkId]);
        }

        const intervalId = window.setInterval(async () => {
            try {
                const result: ResultResponse = await getResult(jobId);
                if (result.status !== 'Processing') {
                    clearInterval(intervalId);
                    delete pollingIntervals.current[chunkId];

                    const finalStatus = result.status.toLowerCase() as ChunkStatus;
                    setStatuses((prev) => ({ ...prev, [chunkId]: finalStatus }));

                    if (result.status === 'Completed') {
                        setTranscripts((prev) => ({ ...prev, [chunkId]: result.transcription || "" }));
                        if (result.error_detail) {
                            setErrors((prev) => ({ ...prev, [chunkId]: result.error_detail }));
                        }
                    } else if (result.status === 'Failed') {
                        setErrors((prev) => ({ ...prev, [chunkId]: result.error || "처리 실패" }));
                    }
                }
            } catch (err) {
                console.error(`청크(${chunkId}) 결과 조회 실패:`, err);
                clearInterval(intervalId);
                delete pollingIntervals.current[chunkId];
                setErrors((prev) => ({ ...prev, [chunkId]: "결과 조회 실패" }));
                setStatuses((prev) => ({ ...prev, [chunkId]: 'failed' }));
            }
        }, 5000); // 5초 간격으로 결과 확인
        pollingIntervals.current[chunkId] = intervalId;
    }, []);

    const upload = useCallback(async (chunkId: string, audioUrl: string) => {
        if (!audioUrl) return;

        setStatuses((prev) => ({ ...prev, [chunkId]: 'uploading' }));
        setTranscripts((prev) => { const rest = { ...prev }; delete rest[chunkId]; return rest; });
        setErrors((prev) => { const rest = { ...prev }; delete rest[chunkId]; return rest; });

        try {
            const blob = await fetch(audioUrl).then((res) => res.blob());
            const filename = `chunk-${chunkId}.webm`;

            const response: UploadResponse = await uploadRecording({ blob, filename }); 
            const jobId = response.job_id;

            if (jobId) {
                setStatuses((prev) => ({ ...prev, [chunkId]: 'processing' }));
                pollForResult(chunkId, jobId);
            } else {
                throw new Error("서버로부터 Job ID를 받지 못했습니다.");
            }
        } catch (err) {
            console.error(`청크(${chunkId}) 업로드 실패:`, err);
            const errorMessage = (err instanceof Error) ? err.message : "알 수 없는 업로드 오류";
            setErrors((prev) => ({ ...prev, [chunkId]: errorMessage }));
            setStatuses((prev) => ({ ...prev, [chunkId]: 'failed' }));
        }
    }, [pollForResult]);

    useEffect(() => {
        const intervals = pollingIntervals.current;
        return () => {
            Object.values(intervals).forEach(clearInterval);
        };
    }, []);

    return { upload, transcripts, statuses, errors };
};