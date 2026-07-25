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
        {card.interest_categories
          .filter((tag) => tag !== "기타")
          .map((tag) => (
            <span key={tag} className="badge">
              {tag}
            </span>
          ))}
        {card.region_relevant && regionLabel && (
          <span className="badge region">📍 {regionLabel}</span>
        )}
        {card.ocr_used === 1 && <span className="badge ocr">🖼 이미지 OCR</span>}
        {card.is_new && <span className="badge new">NEW</span>}
      </div>
      <h4>{card.title}</h4>
      <div className="meta">
        <span>
          <b>{card.source}</b>
        </span>
        <span>
          {card.deadline_date ? `모집 ~ ${card.deadline_date}` : "모집기간 확인 필요"}
        </span>
        <span>등록 {card.reference_date}</span>
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
