"use client";

import type { ActivityCard } from "@/lib/types";

interface Props {
  open: boolean;
  cards: ActivityCard[];
  onClose: () => void;
}

export default function NotificationDrawer({ open, cards, onClose }: Props) {
  return (
    <div
      className={`side-overlay${open ? " open" : ""}`}
      aria-hidden={!open}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside className="notification-drawer" aria-label="알림">
        <div className="drawer-head">
          <div>
            <span className="profile-eyebrow">놓치지 마세요</span>
            <h2>알림</h2>
          </div>
          <button type="button" className="drawer-close" onClick={onClose}>
            닫기
          </button>
        </div>

        <p className="drawer-caption">
          마감이 3일 이내로 남은 맞춤 공고를 모았어요.
        </p>

        <div className="notification-list">
          {cards.length === 0 ? (
            <div className="notification-empty">
              지금은 새로 확인할 마감 알림이 없어요.
            </div>
          ) : (
            cards.map((card) => (
              <a
                className="notification-item"
                href={card.url}
                target="_blank"
                rel="noreferrer"
                key={`${card.id}-${card.url}`}
              >
                <span className="notification-dday">
                  {card.dday === 0 ? "D-DAY" : `D-${card.dday}`}
                </span>
                <strong>{card.title}</strong>
                <small>
                  {card.source} · {card.deadline_date || "기간 확인 필요"}
                </small>
              </a>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
