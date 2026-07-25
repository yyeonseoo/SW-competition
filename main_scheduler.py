import argparse
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from crawlers.kw_crawler import main as run_kw_crawler
from crawlers.linkareer_crawler import main as run_linkareer_crawler
from database import init_db
from services.email_notifier import run_daily_notifications

KST = ZoneInfo("Asia/Seoul")


def execute_batch(send_email: bool = True):
    """지정된 주기에 따라 실행되는 통합 배치 파이프라인 (크롤링 -> 분류/저장 -> 조건부 이메일 알림)"""
    start_time = datetime.now(KST)
    email_status = "ON (오전 8시 수신)" if send_email else "OFF (오후 12시/4시 수집 단독)"
    print(f"\n=======================================================")
    print(f" [KW-LIFE] 자동 수집 및 알림 파이프라인 시작 (이메일 발송: {email_status})")
    print(f" 실행 일시 (KST): {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=======================================================\n")

    # 1. DB 초기화 및 검증
    print(">> Step 1. 데이터베이스 초기화 및 스키마 점검")
    init_db()
    print("  → 데이터베이스 점검 완료\n")

    # 2. 광운대 공지사항 수집 (OCR 포함, 14일 치 보관 규칙 준수, 2차 노이즈 차단)
    print(">> Step 2. 광운대학교 공지사항 수집기 (kw_crawler) 실행")
    try:
        run_kw_crawler()
    except Exception as e:
        print(f"  [오류] kw_crawler 실행 중 문제가 발생했습니다: {e}", file=sys.stderr)
    print("  → 광운대 공지 수집 단계 완료\n")

    # 3. 링커리어 수집기 실행 (팀원 규칙: 헤드리스 브라우저, 부문별 10개 수집)
    print(">> Step 3. 외부 링커리어 공고 수집기 (linkareer_crawler) 실행")
    try:
        run_linkareer_crawler()
    except Exception as e:
        print(f"  [오류] linkareer_crawler 실행 중 문제가 발생했습니다: {e}", file=sys.stderr)
    print("  → 링커리어 수집 단계 완료\n")

    # 4. 맞춤형 신규 공고 이메일 알림 전송 (오전 8시에만 실행)
    if send_email:
        print(">> Step 4. 개인 맞춤형 신규 공고 이메일 알림 (email_notifier) 발송")
        try:
            run_daily_notifications()
        except Exception as e:
            print(f"  [오류] 이메일 알림 발송 중 문제가 발생했습니다: {e}", file=sys.stderr)
        print("  → 맞춤 이메일 알림 발송 단계 완료\n")
    else:
        print(">> Step 4. 이메일 알림 발송 생략 (오전 8시 이외 크롤링 타임에는 발송하지 않음)\n")

    end_time = datetime.now(KST)
    duration = (end_time - start_time).total_seconds()
    print(f"=======================================================")
    print(f" [KW-LIFE] 전체 배치 작업 종료! (총 소요 시간: {duration:.1f}초)")
    print(f"=======================================================\n")


# 하위 호환성 별칭
execute_daily_batch = execute_batch


def loop_scheduler(target_hours=(8, 12, 16), target_minute=0):
    """
    매일 오전 8시, 오후 12시, 오후 4시(16시)에 3회 자동 수집을 실행하고,
    오전 8시에만 신규 맞춤 공고 이메일을 발송하는 데몬 스케줄러입니다.
    """
    print(f"[*] 스케줄러 모드 가동 중... 매일 KST 기준 {', '.join(f'{h:02d}:{target_minute:02d}' for h in target_hours)}에 자동 수집이 실행됩니다.")
    print("[*] (참고: 이메일 알림 발송은 매일 오전 08:00 배치 실행 시에만 단 1회 진행됩니다.)")
    last_run_slot = None

    while True:
        now = datetime.now(KST)
        current_slot = (now.date(), now.hour)

        if (
            now.hour in target_hours
            and now.minute == target_minute
            and last_run_slot != current_slot
        ):
            print(f"[*] 스케줄러 트리거 도달! ({now.strftime('%Y-%m-%d %H:%M')}) - {now.hour}시 배치 시작")
            
            # 오전 8시에만 이메일 전송 (12시, 16시 수집 시에는 이메일 발송 SKIP)
            should_send_email = (now.hour == 8)
            execute_batch(send_email=should_send_email)
            
            last_run_slot = current_slot

        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(
        description="KW-LIFE 비교과 활동 추천 시스템 1일 3회 수집 및 오전 8시 알림 스케줄러"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="종료 없이 매일 오전 8시, 오후 12시, 오후 4시에 자동 배치를 실행하는 데몬 모드",
    )
    parser.add_argument(
        "--hours",
        type=int,
        nargs="+",
        default=[8, 12, 16],
        help="데몬 모드 시 배치를 실행할 시각 목록 (기본: 8 12 16)",
    )
    parser.add_argument(
        "--minute",
        type=int,
        default=0,
        help="데몬 모드 시 배치를 실행할 분 (0~59, 기본 0)",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="단건 배치 실행 시 이메일 발송 스텝을 생략하고 수집만 진행",
    )

    args = parser.parse_args()

    if args.daemon:
        loop_scheduler(tuple(args.hours), args.minute)
    else:
        # 기본 단건 즉시 실행 모드
        execute_batch(send_email=not args.no_email)


if __name__ == "__main__":
    main()
