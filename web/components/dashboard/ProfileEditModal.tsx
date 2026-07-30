"use client";

import { useState } from "react";
import { COLLEGES, findCollegeForDepartment, getDepartments } from "@/data/departments";
import { patchStudent } from "@/lib/api";
import type { MetaResponse, Student } from "@/lib/types";
import CustomSelect from "@/components/ui/CustomSelect";

interface Props {
  student: Student;
  meta: MetaResponse | null;
  onClose: () => void;
  onSaved: (student: Student) => Promise<void>;
}

export default function ProfileEditModal({ student, meta, onClose, onSaved }: Props) {
  const [college, setCollege] = useState(() => findCollegeForDepartment(student.department));
  const [department, setDepartment] = useState(student.department);
  const [grade, setGrade] = useState(student.grade);
  const [enrollmentStatus, setEnrollmentStatus] = useState(
    student.enrollment_status || "enrolled"
  );
  const [sido, setSido] = useState(student.region_sido);
  const [sigungu, setSigungu] = useState(student.region_sigungu);
  const [interests, setInterests] = useState<string[]>(student.interest_categories);
  const [activityTypes, setActivityTypes] = useState<string[]>(
    student.preferred_activity_types ?? []
  );
  const [notifyOptIn, setNotifyOptIn] = useState(student.notify_opt_in === 1);
  const [isInternational, setIsInternational] = useState(student.is_international === 1);
  const [preferenceText, setPreferenceText] = useState(student.preference_text || "");
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sigunguOptions = meta && sido ? meta.regions[sido] ?? [] : [];
  const requiredComplete = Boolean(
    college && department && grade && enrollmentStatus && sido && sigungu
  );

  function toggleInterest(tag: string) {
    setInterests((prev) =>
      prev.includes(tag) ? prev.filter((v) => v !== tag) : [...prev, tag]
    );
  }

  function toggleActivityType(tag: string) {
    setActivityTypes((prev) =>
      prev.includes(tag) ? prev.filter((v) => v !== tag) : [...prev, tag]
    );
  }

  async function handleSave() {
    if (!requiredComplete) {
      setError("필수 정보를 모두 선택해주세요.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await patchStudent(student.id, {
        department,
        grade,
        enrollment_status: enrollmentStatus,
        region_sido: sido,
        region_sigungu: sigungu,
        interest_categories: interests,
        preferred_activity_types: activityTypes,
        notify_opt_in: notifyOptIn ? 1 : 0,
        is_international: isInternational ? 1 : 0,
        preference_text: preferenceText,
      });
      setRefreshing(true);
      await onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했어요.");
      setSaving(false);
      setRefreshing(false);
    }
  }

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (!saving && e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-card">
        <div className="modal-head">
          <h3>프로필 편집</h3>
          <button className="modal-close" onClick={onClose} disabled={saving}>
            ✕
          </button>
        </div>
        <div className="modal-body">
          <div className="section-subtitle" style={{ marginTop: 0 }}>
            전공 · 학년
          </div>
          <div className="field">
            <div className="row">
              <CustomSelect
                value={college}
                options={COLLEGES.map((item) => ({ value: item.name, label: item.name }))}
                onChange={(newCollege) => {
                  setCollege(newCollege);
                  setDepartment(getDepartments(newCollege)[0] ?? "");
                }}
              />
              <CustomSelect
                value={department}
                options={getDepartments(college).map((name) => ({ value: name, label: name }))}
                onChange={setDepartment}
              />
              <CustomSelect
                value={String(grade)}
                options={[1, 2, 3, 4].map((value) => ({
                  value: String(value),
                  label: `${value}학년`,
                }))}
                onChange={(value) => setGrade(Number(value))}
              />
            </div>
          </div>
          <div className="field">
            <label>학적 상태</label>
            <CustomSelect
              value={enrollmentStatus}
              options={[
                { value: "freshman", label: "신입생" },
                { value: "enrolled", label: "재학생" },
                { value: "on_leave", label: "휴학생" },
                { value: "graduating", label: "졸업예정자" },
              ]}
              onChange={setEnrollmentStatus}
            />
          </div>

          <div className="section-subtitle">거주지역</div>
          <div className="field">
            <div className="row">
              <CustomSelect
                value={sido}
                placeholder="시·도 선택"
                options={Object.keys(meta?.regions ?? {}).map((name) => ({
                  value: name,
                  label: name,
                }))}
                onChange={(value) => {
                  setSido(value);
                  setSigungu("");
                }}
              />
              <CustomSelect
                value={sigungu}
                placeholder="시·군·구 선택"
                disabled={!sido}
                options={sigunguOptions.map((name) => ({ value: name, label: name }))}
                onChange={setSigungu}
              />
            </div>
          </div>
          <div className="field">
            <div className="toggle-row">
              <div className="label">
                <b>🌐 국제학생(유학생)이에요</b>
                <small>켜면 국제학생 대상 공지도 함께 보여드려요</small>
              </div>
              <div
                className={`toggle${isInternational ? " on" : ""}`}
                onClick={() => setIsInternational((v) => !v)}
              />
            </div>
          </div>

          <div className="section-subtitle">관심 주제</div>
          <div className="field">
            <div className="tag-picker">
              {(meta?.interest_categories ?? []).map((tag) => (
                <span
                  key={tag}
                  className={`tag${interests.includes(tag) ? " on" : ""}`}
                  onClick={() => toggleInterest(tag)}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="section-subtitle">선호 활동 유형</div>
          <div className="field">
            <div className="tag-picker">
              {(meta?.preferred_activity_types ?? []).map((tag) => (
                <span
                  key={tag}
                  className={`tag${activityTypes.includes(tag) ? " on" : ""}`}
                  onClick={() => toggleActivityType(tag)}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="section-subtitle">원하는 활동 설명</div>
          <div className="field">
            <textarea
              className="input preference-input"
              value={preferenceText}
              maxLength={500}
              onChange={(e) => setPreferenceText(e.target.value)}
              placeholder="예: AI 프로젝트와 해커톤으로 포트폴리오를 만들고 싶어요."
            />
          </div>

          <div className="section-subtitle">알림</div>
          <div className="field">
            <div className="toggle-row">
              <div className="label">
                <b>이메일 알림</b>
                <small>{student.email || "이메일 미설정"} · 하루 1회 요약</small>
              </div>
              <div
                className={`toggle${notifyOptIn ? " on" : ""}`}
                onClick={() => setNotifyOptIn((v) => !v)}
              />
            </div>
          </div>
          {error && (
            <div className="hint" style={{ color: "var(--kw)" }}>
              {error}
            </div>
          )}
          {saving && (
            <div className="profile-save-status" role="status" aria-live="polite">
              <span className="loading-spinner" aria-hidden="true" />
              <span>
                {refreshing
                  ? "새 프로필에 맞춰 추천을 다시 계산하고 있어요."
                  : "프로필을 저장하고 있어요."}
              </span>
            </div>
          )}
        </div>
        <div className="modal-foot">
          <button className="btn btn-ghost" onClick={onClose} disabled={saving}>
            취소
          </button>
              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={saving || !requiredComplete}
              >
            {refreshing ? "추천 반영 중..." : saving ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}
