IMAGE_MAX_RETRY = 1  # 이미지 재생성 상한 1회
COPY_MAX_RETRY = 2  # 카피 생성/규제 재시도 상한
SELF_CHECK_MAX_RETRY = 0  # 자가점검 반려는 재시도 없이 즉시 차단한다 — self_check_retry_count는 관찰용 카운터

IMAGE_TIMEOUT_SECONDS = 35  # 단일 이미지 호출 상한(HTTP 타임아웃)
IMAGE_DEADLINE_SECONDS = 50  # 이미지 생성 전체(재시도 포함) 예산
