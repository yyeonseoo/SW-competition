"use client";

import type { Student } from "@/lib/types";

interface Props {
  student: Student;
  open: boolean;
  onClose: () => void;
  onEditClick: () => void;
}

export default function ProfileBar({
  student,
  open,
  onClose,
  onEditClick,
}: Props) {
  const region = [student.region_sido, student.region_sigungu]
    .filter(Boolean)
    .join(" ");
  const interests =
    student.interest_categories.length > 0
      ? student.interest_categories.join(" · ")
      : "관심분야 미설정";
  const activityTypes =
    student.preferred_activity_types?.length > 0
      ? student.preferred_activity_types.join(" · ")
      : "선호 활동 유형 미설정";

  return (
    <div
      className={`side-overlay${open ? " open" : ""}`}
      aria-hidden={!open}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside className="profile-drawer" aria-label="내 프로필">
        <div className="drawer-head">
          <div>
            <span className="profile-eyebrow">내 추천 기준</span>
            <h2>프로필</h2>
          </div>
          <button type="button" className="drawer-close" onClick={onClose}>
            닫기
          </button>
        </div>

        <div className="drawer-avatar">{student.department.slice(0, 2)}</div>
        <strong className="drawer-student">
          {student.department} · {student.grade}학년
        </strong>
        <p className="drawer-caption">아래 정보를 기준으로 공고를 추천해요.</p>

        <dl className="profile-details">
          <div>
            <dt>학과 · 학년</dt>
            <dd>{student.department} · {student.grade}학년</dd>
          </div>
          <div>
            <dt>지역</dt>
            <dd>{region || "미설정"}</dd>
          </div>
          <div>
            <dt>관심 주제</dt>
            <dd>{interests}</dd>
          </div>
          <div>
            <dt>선호 활동 유형</dt>
            <dd>{activityTypes}</dd>
          </div>
        </dl>

        <button
          type="button"
          className="btn btn-primary drawer-edit"
          onClick={onEditClick}
        >
          추천 기준 수정
        </button>
      </aside>
    </div>
  );
}
