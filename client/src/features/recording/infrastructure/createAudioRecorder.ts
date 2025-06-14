import type {AudioRecorder} from "../entities/AudioRecorder.ts";
import {WebAudioRecorder} from "../entities/WebAudioRecorder.ts";

export const createAudioRecorder = (): AudioRecorder => {
    return new WebAudioRecorder();
};