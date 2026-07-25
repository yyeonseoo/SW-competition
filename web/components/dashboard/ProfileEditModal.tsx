"use client";

import { useState } from "react";
import { COLLEGES, DEPARTMENTS } from "@/data/departments";
import { patchStudent } from "@/lib/api";
import type { MetaResponse, Student } from "@/lib/types";

interface Props {
  student: Student;
  meta: MetaResponse | null;
  onClose: () => void;
  onSaved: (student: Student) => void;
}

export default function ProfileEditModal({ student, meta, onClose, onSaved }: Props) {
  const [college, setCollege] = useState(COLLEGES[0]);
  const [department, setDepartment] = useState(student.department);
  const [grade, setGrade] = useState(student.grade);
  const [sido, setSido] = useState(student.region_sido);
  const [sigungu, setSigungu] = useState(student.region_sigungu);
  const [interests, setInterests] = useState<string[]>(student.interest_categories);
  const [notifyOptIn, setNotifyOptIn] = useState(student.notify_opt_in === 1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sigunguOptions = meta && sido ? meta.regions[sido] ?? [] : [];

  function toggleInterest(tag: string) {
    setInterests((prev) =>
      prev.includes(tag) ? prev.filter((v) => v !== tag) : [...prev, tag]
    );
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const updated = await patchStudent(student.id, {
        department,
        grade,
        region_sido: sido,
        region_sigungu: sigungu,
        interest_categories: interests,
        notify_opt_in: notifyOptIn ? 1 : 0,
      });
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했어요.");
      setSaving(false);
    }
  }

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-card">
        <div className="modal-head">
          <h3>프로필 편집</h3>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="modal-body">
          <div className="section-subtitle" style={{ marginTop: 0 }}>
            전공 · 학년
          </div>
          <div className="field">
            <div className="row">
              <select className="select" value={college} onChange={(e) => setCollege(e.target.value)}>
                {COLLEGES.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              <select
                className="select"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              >
                {DEPARTMENTS.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              <select
                className="select"
                value={grade}
                onChange={(e) => setGrade(Number(e.target.value))}
              >
                {[1, 2, 3, 4].map((g) => (
                  <option key={g} value={g}>
                    {g}학년
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="section-subtitle">거주지역</div>
          <div className="field">
            <div className="row">
              <select
                className="select"
                value={sido}
                onChange={(e) => {
                  setSido(e.target.value);
                  setSigungu("");
                }}
              >
                <option value="">시·도 선택</option>
                {meta &&
                  Object.keys(meta.regions).map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
              </select>
              <select className="select" value={sigungu} onChange={(e) => setSigungu(e.target.value)}>
                <option value="">구/시·군 선택</option>
                {sigunguOptions.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="section-subtitle">관심분야</div>
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
        </div>
        <div className="modal-foot">
          <button className="btn btn-ghost" onClick={onClose}>
            취소
          </button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}
