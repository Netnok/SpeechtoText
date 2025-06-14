// features/recording/hooks/useRecorder.ts

import { useEffect, useRef, useState, useCallback } from 'react';
import { createAudioRecorder } from '../infrastructure/createAudioRecorder';
import type { AudioRecorder } from "../entities/AudioRecorder";
import type { RecordingChunk, RecordingStatus } from "../types/RecordingType";

export const useRecorder = (chunkDurationMs?: number) => {
    const [status, setStatus] = useState<RecordingStatus>('idle');
    const [chunks, setChunks] = useState<RecordingChunk[]>([]);
    
    const recorderRef = useRef<AudioRecorder | null>(null);

    // 이 useEffect는 훅이 처음 사용될 때(마운트 시) 단 한 번만 실행됩니다.
    // 녹음기 인스턴스를 생성하고, 이벤트 핸들러(콜백)를 영구적으로 등록하는 역할을 합니다.
    useEffect(() => {
        // AudioRecorder 인스턴스 생성
        const recorder = createAudioRecorder();
        recorderRef.current = recorder;

        // [이벤트 등록 1] 새로운 오디오 청크가 준비되었을 때 실행될 콜백
        recorder.onChunkReady((blob, startTime, endTime) => {
            // Blob을 재생 가능한 임시 URL로 변환
            const url = URL.createObjectURL(blob);
            // 새로운 청크 정보를 chunks 상태 배열에 추가
            setChunks(prev => [
                ...prev,
                {
                    id: crypto.randomUUID(),
                    audioUrl: url,
                    startTime,
                    endTime,
                }
            ]);
        });

        // [이벤트 등록 2] 녹음이 완전히 중지되었을 때 실행될 콜백
        recorder.onStop((fullRecordingBlob) => {
            console.log("녹음이 중지되었습니다. 전체 Blob 크기:", fullRecordingBlob.size);
            setStatus('stopped');
        });

        // [이벤트 등록 3] 오류 발생 시 실행될 콜백
        recorder.onError((error) => {
            console.error('녹음 중 오류가 발생했습니다:', error);
            setStatus('stopped'); // 'failed' 상태가 RecordingStatus 타입에 정의되어 있어야 함
        });

        // [cleanup 함수] 컴포넌트가 화면에서 사라질 때(unmount) 실행됩니다.
        return () => {
            if (recorderRef.current) {
                recorderRef.current.destroy(); // 마이크 스트림 해제 등 리소스 정리
                recorderRef.current = null;
            }
            // 남아있는 모든 Blob URL을 메모리에서 해제하여 메모리 누수 방지
            setChunks(prevChunks => {
                prevChunks.forEach(chunk => URL.revokeObjectURL(chunk.audioUrl));
                return []; 
            });
        };
    }, []); // 의존성 배열이 비어있으므로, mount 시 한 번만 실행됩니다.

    // 이 함수는 이전 녹음 데이터를 정리하고 새 녹음을 시작합니다.
    const start = useCallback(() => {
        // 이전 녹음으로 생성된 모든 청크와 URL을 정리합니다.
        setChunks(prevChunks => {
            prevChunks.forEach(chunk => URL.revokeObjectURL(chunk.audioUrl));
            return [];
        });

        if (recorderRef.current) {
            // start 메소드에 chunkDurationMs를 전달하여 녹음 주기를 설정합니다.
            // chunkDurationMs가 undefined이면, stop() 시 한 번만 청크가 생성됩니다.
            recorderRef.current.start({ timeSliceMs: chunkDurationMs });
            setStatus('recording');
        } else {
            console.error("Recorder가 초기화되지 않았습니다.");
            setStatus('stopped');
        }
    }, [chunkDurationMs]); // chunkDurationMs가 변경될 때만 이 함수가 새로 생성됩니다.

    // stop, pause, resume 함수들은 recorder의 해당 메소드를 호출하는 간단한 래퍼(wrapper)입니다.
    const stop = useCallback(() => {
        if (recorderRef.current && (status === 'recording' || status === 'paused')) {
            recorderRef.current.stop();
            // 실제 status 변경('stopped')은 위에서 등록한 onStop 콜백에서 처리됩니다.
        }
    }, [status]);

    const pause = useCallback(() => {
        if (recorderRef.current && status === 'recording') {
            recorderRef.current.pause();
            setStatus('paused');
        }
    }, [status]);

    const resume = useCallback(() => {
        if (recorderRef.current && status === 'paused') {
            recorderRef.current.resume();
            setStatus('recording');
        }
    }, [status]);

    // UI 컴포넌트에서 사용할 상태와 제어 함수들을 반환합니다.
    return {
        status,
        chunks,
        start,
        stop,
        pause,
        resume,
    };
};