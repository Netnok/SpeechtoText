# test_gcp_stt.py (MP3 파일용)
from google.cloud import speech
from google.auth.exceptions import DefaultCredentialsError, GoogleAuthError
import os

# --- 설정 (사용자 환경에 맞게 수정) ---
# 1. GCP 서비스 계정 JSON 키 파일 경로 (환경 변수 설정 권장)
#    터미널에서 'export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-keyfile.json"' 실행
#    이 스크립트 실행 전에 반드시 위 환경 변수가 설정되어 있어야 합니다.

# 2. 테스트할 MP3 파일의 GCS URI (실제 GCS 경로로 변경!)
#    예: "gs://your-actual-gcs-bucket-name/test_audio/sample_ko.mp3"
#    이 파일은 미리 GCS 버킷에 업로드되어 있어야 하며, 명확한 한국어 음성이 포함된 MP3 파일 권장
GCS_AUDIO_URI = "gs://my-gcp-speech-test-bucket-882341/1_0000.wav"

# 3. MP3 파일에 맞는 RecognitionConfig 설정
AUDIO_ENCODING = speech.RecognitionConfig.AudioEncoding.MP3
# MP3의 경우 sample_rate_hertz는 파일 헤더에서 읽어오는 경우가 많으므로,
# None으로 설정하여 API가 자동 감지하도록 하거나, 실제 파일의 샘플 레이트를 안다면 명시.
# AUDIO_SAMPLE_RATE_HERTZ = 44100  # 예시: MP3 파일의 실제 샘플 레이트 (모른다면 None 또는 주석 처리)
AUDIO_SAMPLE_RATE_HERTZ = None # API 자동 감지 시도
AUDIO_LANGUAGE_CODE = "ko-KR"    # 한국어
# MP3는 보통 스테레오일 수도 있지만, 음성 인식은 모노로 처리되는 경우가 많음.
# API가 자동 처리하거나, 문제가 생기면 1로 명시 고려.
AUDIO_CHANNEL_COUNT = None # API 자동 감지 시도 (또는 1로 명시)

# ------------------------------------------

def transcribe_gcs_audio_sample(gcs_uri: str):
    """GCS에 있는 단일 오디오 파일을 Speech-to-Text API로 분석합니다."""
    
    print(f"GCP 인증 정보 (GOOGLE_APPLICATION_CREDENTIALS): {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")

    try:
        client = speech.SpeechClient()
        print("SpeechClient 초기화 성공.")
    except DefaultCredentialsError as e:
        print(f"SpeechClient 초기화 실패 (DefaultCredentialsError): {e}")
        print("GOOGLE_APPLICATION_CREDENTIALS 환경 변수가 올바르게 설정되었는지, JSON 키 파일 경로가 정확한지 확인하세요.")
        return
    except Exception as e:
        print(f"SpeechClient 초기화 중 예상치 못한 오류: {e}")
        return

    recognition_config_args = {
        "encoding": AUDIO_ENCODING,
        "language_code": AUDIO_LANGUAGE_CODE,
        "enable_automatic_punctuation": True,
        # "model": "latest_long", # 필요시 특정 모델 지정
    }
    if AUDIO_SAMPLE_RATE_HERTZ is not None:
        recognition_config_args["sample_rate_hertz"] = AUDIO_SAMPLE_RATE_HERTZ
    if AUDIO_CHANNEL_COUNT is not None:
        recognition_config_args["audio_channel_count"] = AUDIO_CHANNEL_COUNT
    
    audio_config = speech.RecognitionConfig(**recognition_config_args)
    
    audio_input = speech.RecognitionAudio(uri=gcs_uri)

    print(f"\nSpeech-to-Text API 요청 전송 중...")
    print(f"GCS URI: {gcs_uri}")
    print(f"RecognitionConfig: {audio_config}") # 이 부분을 통해 실제 어떤 설정으로 요청하는지 확인 가능

    try:
        operation = client.long_running_recognize(config=audio_config, audio=audio_input)
        print(f"STT 작업 시작됨. Operation Name: {operation.operation.name}")
        
        print("결과 대기 중... (최대 5분)")
        response = operation.result(timeout=300) # 5분 대기

        print("\n--- 전체 API 응답 (Raw Response) ---")
        print(response)
        print("------------------------------------")

        if not response.results:
            print("\n오디오에서 음성을 감지하지 못했거나 변환된 텍스트가 없습니다.")
            # operation.metadata.error_message 와 response.error는 다를 수 있음.
            # long_running_recognize의 경우 operation.metadata에 최종 오류 정보가 담길 수 있음.
            # 하지만 response 객체 자체에도 error 필드가 있을 수 있음 (v2 API 등)
            # 일단 response 객체에 error 필드가 있는지 확인 (API 버전에 따라 다를 수 있음)
            if hasattr(response, 'error') and response.error and hasattr(response.error, 'message'):
                 print(f"API 오류 메시지 (response.error): {response.error.message}")
            # 또는 operation.metadata 확인 (좀 더 일반적일 수 있음)
            elif operation.metadata and hasattr(operation.metadata, 'error_status') and operation.metadata.error_status.message:
                 print(f"API 오류 메시지 (operation.metadata.error_status): {operation.metadata.error_status.message}")


        for i, result in enumerate(response.results):
            if result.alternatives:
                print(f"\n결과 #{i+1}:")
                print(f"  Transcript: {result.alternatives[0].transcript}")
                print(f"  Confidence: {result.alternatives[0].confidence:.2f}")
                if result.language_code:
                    print(f"  Detected Language: {result.language_code}")
            else:
                print(f"\n결과 #{i+1}: 변환된 내용 없음 (No alternatives)")
        
        if response.total_billed_time:
            print(f"\n청구된 오디오 처리 시간: {response.total_billed_time.total_seconds()} 초")

    except GoogleAuthError as e:
        print(f"\nGoogle 인증 오류 발생: {e}")
        print("서비스 계정 JSON 키 파일 또는 해당 계정의 IAM 권한을 확인하세요.")
    except Exception as e:
        print(f"\nSTT API 호출 또는 결과 처리 중 오류 발생: {e}")
        if 'operation' in locals() and hasattr(operation, 'metadata'):
            if operation.metadata and hasattr(operation.metadata, 'error_status') and operation.metadata.error_status.message:
                 print(f"Operation Metadata Error: {operation.metadata.error_status.message}")
            elif operation.metadata and hasattr(operation.metadata, 'error_message'): # 일부 오래된 API 응답 방식 호환
                 print(f"Operation Metadata Error: {operation.metadata.error_message}")


if __name__ == "__main__":
    if "여기에_실제_GCS_버킷이름" in GCS_AUDIO_URI: # 플레이스홀더가 여전히 있는지 확인
        print("스크립트 상단의 GCS_AUDIO_URI 변수를 실제 MP3 파일이 있는 GCS 경로로 수정해주세요!")
    else:
        transcribe_gcs_audio_sample(GCS_AUDIO_URI)