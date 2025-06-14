import React from "react";

interface TranscriptDetailPaneProps {
    chunk?: {
        startTime: number;
        endTime: number;
    } | null;
    transcript?: string;
    isLoading?: boolean;
    error?: string;
    // children: 추가 액션(예: AI 응답 등) slot 용도
    children?: React.ReactNode;
}

export const TranscriptDetailPane: React.FC<TranscriptDetailPaneProps> = ({
                                                                              chunk,
                                                                              transcript,
                                                                              isLoading,
                                                                              error,
                                                                              children,
                                                                          }) => {
    if (isLoading) {
        return (
            <div className="w-full max-w-xl min-h-[140px] flex items-center justify-center bg-gray-50 border border-dashed border-gray-300 rounded-lg shadow-inner">
                <span className="text-gray-400">로딩 중...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="w-full max-w-xl min-h-[140px] flex items-center justify-center bg-red-50 border border-dashed border-red-300 rounded-lg shadow-inner">
                <span className="text-red-500">{error}</span>
            </div>
        );
    }

    if (!chunk || !transcript) {
        return (
            <div className="w-full max-w-xl min-h-[140px] flex flex-col items-center justify-center bg-gray-50 border border-dashed border-gray-300 rounded-lg shadow-inner transition-all">
                <span className="text-2xl text-gray-300 mb-2">📝</span>
                <span className="text-gray-400 text-center leading-relaxed">
          청크를 선택하면<br/>여기에 변환된 텍스트가 표시됩니다.
        </span>
            </div>
        );
    }

    return (
        <div className="w-full">
            <h2 className="font-bold mb-2">청크 변환 결과</h2>
            <div className="bg-gray-50 rounded p-3 shadow">
                <div className="mb-1 text-xs text-gray-400">
                    {chunk.startTime} ~ {chunk.endTime}
                </div>
                <textarea
                    className="w-full border rounded p-2 text-sm bg-white"
                    value={transcript}
                    readOnly
                    rows={Math.max(3, Math.ceil((transcript.length || 0) / 40))}
                />
                {/* 추가 액션 slot */}
                {children}
            </div>
        </div>
    );
};
