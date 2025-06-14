import { useEffect, useState } from "react";

export function useSimpleRecordingTimer(status: "idle" | "recording" | "paused" | "stopped") {
    const [elapsedSec, setElapsedSec] = useState(0);

    useEffect(() => {
        let interval: number | undefined;
        if (status === "recording") {
            interval = window.setInterval(() => {
                setElapsedSec(prev => prev + 1);
            }, 1000);
        } else if (status === "idle" || status === "stopped") {
            setElapsedSec(0); // 녹음이 중지/초기화되면 시간 리셋
        }
        return () => {
            if (interval) clearInterval(interval);
        };
    }, [status]);

    return elapsedSec;
}
