IMAGE_MAX_RETRY = 1  # 이미지 재생성 상한 1회
COPY_MAX_RETRY = 2  # 카피 생성/규제 재시도 상한


IMAGE_TIMEOUT_SECONDS = 20  # 단일 이미지 호출 상한(HTTP 타임아웃)
IMAGE_DEADLINE_SECONDS = 20  # 이미지 생성 전체(재시도 포함) 예산
