import React from "react";
import type { RecordingChunk } from "../../recording/types/RecordingType.ts";

interface TranscriptChunkBlockProps {
    chunk: RecordingChunk;
    isUploading: boolean;
    transcript?: string;
    error?: string;
    onUpload: (id: string, audioUrl: string) => void;
    onAskAI?: (id: string, transcript: string) => void;
    aiResponse?: string;
    isAIResponding?: boolean;
}

export const TranscriptChunkBlock: React.FC<TranscriptChunkBlockProps> = ({
                                                                              chunk,
                                                                              isUploading,
                                                                              transcript,
                                                                              error,
                                                                              onUpload,
                                                                              onAskAI,
                                                                              aiResponse,
                                                                              isAIResponding,
                                                                          }) => {
    // 시간 포맷 (ms → mm:ss)
    const formatTime = (ms: number) => {
        const sec = Math.floor(ms / 1000);
        const m = String(Math.floor(sec / 60)).padStart(2, '0');
        const s = String(sec % 60).padStart(2, '0');
        return `${m}:${s}`;
    };

    return (
        <div className="p-4 rounded-xl shadow bg-gray-50 flex flex-col gap-2">
            {/* 시간 정보 */}
            <div className="text-xs text-gray-400 mb-1">
                [{formatTime(chunk.startTime)} ~ {formatTime(chunk.endTime)}]
            </div>
            {/* 오디오 플레이어 */}
            <audio controls src={chunk.audioUrl} className="w-full" />
            {/* 업로드/변환 버튼 및 상태 */}
            <div className="flex gap-2 items-center">
                <button
                    disabled={isUploading}
                    onClick={() => onUpload(chunk.id, chunk.audioUrl)}
                    className="btn btn-sm"
                >
                    {isUploading ? "변환 중..." : "업로드/변환"}
                </button>
                {error && <span className="text-red-500 text-xs">{error}</span>}
            </div>
            {/* 변환 결과(스크립트) */}
            {transcript && (
                <textarea
                    className="w-full border rounded p-2 text-sm bg-white mt-1"
                    value={transcript}
                    readOnly
                    rows={Math.max(2, Math.ceil(transcript.length / 40))}
                />
            )}
            {/* AI 응답 요청 및 결과 (선택적) */}
            {transcript && onAskAI && (
                <div className="flex flex-col gap-1 mt-1">
                    <button
                        disabled={isAIResponding}
                        className="btn btn-xs self-end"
                        onClick={() => onAskAI(chunk.id, transcript)}
                    >
                        {isAIResponding ? "AI 응답 중..." : "AI에게 질문"}
                    </button>
                    {aiResponse && (
                        <div className="mt-1 p-2 bg-white border rounded text-sm">
                            <b>AI 응답:</b> {aiResponse}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default TranscriptChunkBlock;
