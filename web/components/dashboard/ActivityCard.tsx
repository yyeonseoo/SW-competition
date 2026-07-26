"use client";

import { badgeClassFor, displayLabelFor } from "@/lib/badges";
import type { ActivityCard as ActivityCardType } from "@/lib/types";

interface Props {
  card: ActivityCardType;
}

export default function ActivityCard({ card }: Props) {
  const regionLabel = card.region_detail || card.region_sido;

  return (
    <div className="card">
      <div className="tags">
        <span className={`badge cat ${badgeClassFor(card.activity_category)}`}>
          {displayLabelFor(card.activity_category)}
        </span>
        {/* 교내는 관심분야로 필터링하지 않으므로(학과만 봄) 관심분야 뱃지도 보여주지 않는다. */}
        {card.campus_scope === "교외" &&
          card.interest_categories
            .filter((tag) => tag !== "기타")
            .map((tag) => (
              <span key={tag} className="badge">
                {tag}
              </span>
            ))}
        {card.region_relevant && regionLabel && (
          <span className="badge region">📍 {regionLabel}</span>
        )}
        {card.is_new && <span className="badge new">NEW</span>}
      </div>
      <h4>{card.title}</h4>
      {card.recommendation_reason && (
        <div
          className={`recommendation-reason${
            card.eligibility_uncertain ? " uncertain" : ""
          }`}
        >
          {card.eligibility_uncertain ? "⚠️" : "✨"} {card.recommendation_reason}
        </div>
      )}
      <div className="meta">
        <span>
          <b>{card.source}</b>
        </span>
        <span>
          {card.deadline_date ? `모집 ~ ${card.deadline_date}` : "모집기간 확인 필요"}
        </span>
        <span>
          {card.date_basis === "GPT 구조화 시작일" ||
          card.date_basis === "링커리어 접수 시작일"
            ? "모집 시작"
            : "등록"}{" "}
          {card.reference_date}
        </span>
      </div>
      <div className="footer">
        <div className="target">모집대상 : {card.target_raw || "확인 필요"}</div>
        <a href={card.url} target="_blank" rel="noreferrer" className="link">
          바로가기 →
        </a>
      </div>
    </div>
  );
}
