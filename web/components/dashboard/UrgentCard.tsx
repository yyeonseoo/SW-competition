"use client";

import { badgeClassFor, displayLabelFor } from "@/lib/badges";
import type { ActivityCard as ActivityCardType } from "@/lib/types";

interface Props {
  card: ActivityCardType;
}

export default function UrgentCard({ card }: Props) {
  return (
    <div
      className="card-urgent"
      style={{ cursor: "pointer" }}
      onClick={() => window.open(card.url, "_blank", "noopener,noreferrer")}
    >
      <div className="top">
        <span className="dday">D-{card.dday}</span>
        <span className={`badge cat ${badgeClassFor(card.activity_category)}`}>
          {displayLabelFor(card.activity_category)}
        </span>
        {card.campus_scope === "교외" &&
          card.interest_categories
            .filter((tag) => tag !== "기타")
            .slice(0, 2)
            .map((tag) => (
              <span key={tag} className="badge">
                {tag}
              </span>
            ))}
      </div>
      <h4>{card.title}</h4>
      <div className="meta">
        {card.source} · 마감 {card.deadline_date} ·{" "}
        {card.date_basis === "GPT 구조화 시작일" ||
        card.date_basis === "링커리어 접수 시작일"
          ? "모집 시작"
          : "등록"}{" "}
        {card.reference_date}
      </div>
    </div>
  );
}
