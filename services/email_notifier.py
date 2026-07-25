import os
import smtplib
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Tuple

from database import DB_NAME, get_db_connection
from recommend import _card_from_activity, recommend_for_student_id

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", SMTP_USER or "noreply-kwlife@kw.ac.kr")


def get_opted_in_students() -> List[int]:
    """알림 수신에 동의(notify_opt_in=1)했고 이메일이 기입된 학생 ID 목록을 조회합니다."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id FROM students WHERE notify_opt_in = 1 AND email IS NOT NULL AND email != ''"
        ).fetchall()
        return [row["id"] for row in rows]


def get_new_recommendations(student_id: int) -> Tuple[dict, list]:
    """해당 학생 맞춤 공고 중, 최근 24시간 이내(전날 12시/16시 + 오늘 8시 수집분) 최초 발견된 신규 공고만 가려서 반환합니다."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    cutoff = now_kst - timedelta(hours=24)
    cutoff_str = cutoff.isoformat()

    student, matched_activities = recommend_for_student_id(student_id)
    new_cards = []
    for act in matched_activities:
        card = _card_from_activity(act)
        first_seen = str(card.get("first_seen_at") or "")
        # 당일 등록된 신규(is_new=True)이거나 최근 24시간 내 유입된 신규 공고인 경우
        if card.get("is_new") or (first_seen and first_seen >= cutoff_str):
            new_cards.append(card)
    return student, new_cards


def render_email_html(student: dict, new_cards: list) -> str:
    """광운대 레드 상징색을 활용한 HTML 이메일 템플릿을 생성합니다."""
    cards_html = ""
    for card in new_cards:
        dday_badge = f"D-{card['dday']}" if card.get("dday") is not None and card["dday"] >= 0 else "마감 임박"
        if card.get("dday") == 0:
            dday_badge = "오늘 마감"
            
        cards_html += f"""
        <div style="border: 1px solid #e0e0e0; border-left: 5px solid #8B0000; border-radius: 6px; padding: 16px; margin-bottom: 14px; background-color: #ffffff;">
            <div style="font-size: 12px; color: #666666; margin-bottom: 6px;">
                <span style="display: inline-block; background-color: #fce8e8; color: #8B0000; font-weight: bold; padding: 2px 8px; border-radius: 12px; margin-right: 6px;">{card['activity_category']}</span>
                <span>{card['source']}</span>
                <span style="float: right; color: #d32f2f; font-weight: bold;">{dday_badge}</span>
            </div>
            <h3 style="margin: 0 0 8px 0; font-size: 16px; color: #111111;">
                <a href="{card['url']}" style="color: #111111; text-decoration: none;">{card['title']}</a>
            </h3>
            <div style="font-size: 13px; color: #555555; line-height: 1.5;">
                <p style="margin: 4px 0;"><strong>관심분야:</strong> {', '.join(card['interest_categories'])}</p>
                <p style="margin: 4px 0;"><strong>참여대상:</strong> {card.get('target_raw', '확인 필요')}</p>
                <p style="margin: 4px 0;"><strong>마감일자:</strong> {card.get('deadline_date', '확인 필요')}</p>
            </div>
            <div style="margin-top: 12px;">
                <a href="{card['url']}" style="display: inline-block; font-size: 13px; color: #ffffff; background-color: #8B0000; text-decoration: none; padding: 6px 14px; border-radius: 4px; font-weight: 500;">공고 원문 보러가기 →</a>
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>KW-LIFE 맞춤 공고 알림</title>
    </head>
    <body style="font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f7f7f7; padding: 20px; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
            <div style="background-color: #8B0000; padding: 24px; text-align: center; color: #ffffff;">
                <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;">KW-LIFE 맞춤 추천 알림</h1>
                <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.9;">광운대 학생 맞춤형 비교과 활동 추천 시스템</p>
            </div>
            
            <div style="padding: 24px;">
                <p style="font-size: 16px; color: #333333; margin-top: 0;">
                    <strong>{student['name']}</strong> ({student['department']} {student['grade']}학년) 님, 안녕하세요!<br>
                    오늘 회원님의 관심분야 및 프로필 조건과 일치하는 <strong>새로운 비교과 활동 공고가 {len(new_cards)}건</strong> 등록되었습니다.
                </p>
                <hr style="border: none; border-top: 1px solid #eeeeee; margin: 20px 0;">
                
                {cards_html}

                <div style="margin-top: 30px; padding: 14px; background-color: #f9f9f9; border-radius: 6px; text-align: center; font-size: 12px; color: #888888;">
                    <p style="margin: 0;">본 이메일은 KW-LIFE 알림 수신에 동의해주신 학생분들께 1일 1회 발송됩니다.<br>
                    더 이상 알림을 원치 않으시면 프로필 설정 화면에서 알림 수신 동의를 해제해주시기 바랍니다.</p>
                    <p style="margin: 8px 0 0 0; font-weight: bold; color: #666666;">© Kwangwoon University SW Competition - Team KW-LIFE</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """SMTP 서버를 이용해 이메일을 발송합니다. 환경변수 미설정 시 콘솔 로그 시뮬레이션으로 fallback합니다."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"\n[EMAIL SIMULATION (SMTP 설정 안됨)]")
        print(f"  → To: {to_email}")
        print(f"  → Subject: {subject}")
        print(f"  → HTML Body Preview (길이 {len(html_body)} 바이트 생성됨)")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

        print(f"  → [이메일 발송 성공] To: {to_email} / Subject: {subject}")
        return True
    except Exception as e:
        print(f"  → [이메일 발송 실패] To: {to_email} / Error: {e}")
        return False


def run_daily_notifications():
    """하루 1회 배치 실행 시 대상 학생을 찾아 신규 매칭 공고 알림을 발송하는 메인 진입점입니다."""
    print("====== [KW-LIFE 이메일 맞춤 알림 발송 서비스] ======")
    student_ids = get_opted_in_students()
    print(f"알림 동의 학생 수: {len(student_ids)}명")

    notified_count = 0
    for sid in student_ids:
        try:
            student, new_cards = get_new_recommendations(sid)
            if not new_cards:
                print(f"  - [{student['name']} ({student['email']})] 님: 오늘 등록된 신규 맞춤 공고 없음")
                continue

            subject = f"[KW-LIFE] {student['name']}님을 위한 신규 맞춤 공고 {len(new_cards)}건이 도착했습니다!"
            html = render_email_html(student, new_cards)
            
            success = send_email(student["email"], subject, html)
            if success:
                notified_count += 1
        except Exception as err:
            print(f"  - [오류 발생] 학생 ID {sid} 알림 발송 실패: {err}")

    print(f"====== 알림 발송 처리 완료: {notified_count}명 발송됨 ======\n")


if __name__ == "__main__":
    run_daily_notifications()
