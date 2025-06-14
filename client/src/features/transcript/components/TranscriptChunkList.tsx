import React from 'react';
import type { RecordingChunk, ChunkStatus } from '../../recording/types/RecordingType';

interface TranscriptChunkListProps {
    chunks: RecordingChunk[];
    statuses: Record<string, ChunkStatus>;
    transcripts: Record<string, string>;
    errors: Record<string, string>;
    onUpload: (id: string, audioUrl: string) => void;
}

const TranscriptChunkList: React.FC<TranscriptChunkListProps> = ({
    chunks,
    statuses,
    transcripts,
    errors,
    onUpload,
}) => {
    return (
        <div className="flex flex-col gap-4 mt-4 max-h-[60vh] overflow-y-auto">
            {chunks.length === 0 && <p className="text-gray-500">녹음된 오디오 청크가 여기에 표시됩니다.</p>}
            
            {chunks.map((chunk, index) => {
                const chunkStatus = statuses[chunk.id] || 'idle';
                const transcriptText = transcripts[chunk.id];
                const errorText = errors[chunk.id];

                return (
                    <div key={chunk.id} className="p-4 rounded-xl shadow bg-gray-50 flex flex-col gap-2">
                        <div className="text-sm text-gray-500 font-semibold">
                            청크 #{index + 1}
                        </div>
                        <audio controls src={chunk.audioUrl} className="w-full" />
                        
                        {/* 업로드 버튼 및 상태 표시 */}
                        <div className="flex gap-2 items-center mt-2">
                            <button
                                onClick={() => onUpload(chunk.id, chunk.audioUrl)}
                                disabled={chunkStatus === 'uploading' || chunkStatus === 'processing'}
                                className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
                            >
                                변환하기
                            </button>
                            {chunkStatus === 'uploading' && <span className="text-gray-600">업로드 중...</span>}
                            {chunkStatus === 'processing' && <span className="text-blue-600">처리 중...</span>}
                            {chunkStatus === 'failed' && <span className="text-red-500">실패</span>}
                            {chunkStatus === 'completed' && <span className="text-green-600">완료</span>}
                        </div>

                        {/* --- 변환된 텍스트를 청크 바로 아래에 표시 --- */}
                        {transcriptText && (
                            <textarea
                                className="w-full border rounded p-2 text-sm bg-white mt-2"
                                readOnly
                                rows={3}
                                value={transcriptText}
                            />
                        )}
                        {errorText && (
                            <p className="text-red-500 text-sm mt-1">{errorText}</p>
                        )}
                    </div>
                );
            })}
        </div>
    );
};

export default TranscriptChunkList;