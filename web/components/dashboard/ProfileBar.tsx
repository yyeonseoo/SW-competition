"use client";

import type { Student } from "@/lib/types";

interface Props {
  student: Student;
  newTodayCount: number;
  onEditClick: () => void;
}

export default function ProfileBar({ student, newTodayCount, onEditClick }: Props) {
  return (
    <div className="profile-bar">
      <div>
        <div className="greeting">
          <b>{student.department} ({student.grade}학년)</b>님의 맞춤 비교과 활동 대시보드
        </div>
        <div className="profile-chips">
          <span className="chip major">
            {student.department} · {student.grade}학년
          </span>
          <span className="chip icon">
            {student.region_sido} {student.region_sigungu}
          </span>
          <span className="chip interest">
            {student.interest_categories.length > 0
              ? student.interest_categories.join(" · ")
              : "관심분야 미설정"}
          </span>
        </div>
      </div>
      <button className="btn-edit" onClick={onEditClick}>
        프로필 편집
      </button>
    </div>
  );
}
