import React from "react";
import { useUploadRecording } from "../features/recording/hooks/useUploadRecording";
import { RecorderControls } from "../features/recording/components/RecorderControls";
import { useRecorder } from "../features/recording/hooks/userRecorder";
import { useSimpleRecordingTimer } from "../features/recording/hooks/useRecordingTimer";
// 이 예시에서는 설명을 위해 RecordingSplitView 대신 TranscriptChunkList를 직접 사용
import TranscriptChunkList from "../features/transcript/components/TranscriptChunkList";

const RecordingPage: React.FC = () => {
    // 1분 단위로 청크 생성하도록 설정
    const { status: recordStatus, chunks, start, stop, pause, resume } = useRecorder(60000);

    const { upload, transcripts, statuses, errors } = useUploadRecording();

    const elapsedSec = useSimpleRecordingTimer(recordStatus);

    return (
        <div className="max-w-5xl mx-auto p-4">
            <h1 className="text-xl font-bold mb-4">🎙️ 녹음/변환 데모 (기준점 복구)</h1>

            <RecorderControls
                status={recordStatus}
                elapsedSec={elapsedSec}
                onStart={start}
                onStop={stop}
                onPause={pause}
                onResume={resume}
            />

            {/* 청크 목록과 그 결과를 표시하는 리스트 */}
            <div className="mt-6">
                <h2 className="text-lg font-semibold mb-2">처리 결과 목록</h2>
                <TranscriptChunkList
                    chunks={chunks}
                    statuses={statuses}
                    transcripts={transcripts}
                    errors={errors}
                    onUpload={upload}
                />
            </div>
        </div>
    );
};

export default RecordingPage;