"use client";

import type { Student } from "@/lib/types";

interface Props {
  student: Student;
  onEditClick: () => void;
}

export default function ProfileBar({ student, onEditClick }: Props) {
  return (
    <div className="profile-bar">
      <div className="profile-card">
        <div className="profile-facts">
          <div className="profile-fact">
            <span className="profile-label">학과 · 학년</span>
            <strong>
              {student.department} · {student.grade}학년
            </strong>
          </div>
          <div className="profile-fact">
            <span className="profile-label">지역</span>
            <strong>
              {student.region_sido} {student.region_sigungu}
            </strong>
          </div>
          <div className="profile-fact interest">
            <span className="profile-label">관심분야</span>
            <strong>
              {student.interest_categories.length > 0
                ? student.interest_categories.join(" · ")
                : "미설정"}
            </strong>
          </div>
        </div>
        <button className="btn-edit" onClick={onEditClick}>
          프로필 수정
        </button>
      </div>
    </div>
  );
}
