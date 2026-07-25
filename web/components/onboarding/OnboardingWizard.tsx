"use client";

import { useEffect, useState } from "react";
import { DEFAULT_COLLEGE, DEFAULT_DEPARTMENT, getDepartments } from "@/data/departments";
import { createStudent, getMeta } from "@/lib/api";
import { setStoredStudentId } from "@/lib/studentId";
import type { MetaResponse } from "@/lib/types";
import StepInterest from "./StepInterest";
import StepMajor from "./StepMajor";
import StepRegion from "./StepRegion";

interface Props {
  onComplete: (studentId: number) => void;
}

export default function OnboardingWizard({ onComplete }: Props) {
  const [step, setStep] = useState(1);
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [college, setCollege] = useState(DEFAULT_COLLEGE);
  const [department, setDepartment] = useState(DEFAULT_DEPARTMENT);
  const [grade, setGrade] = useState(3);
  const [sido, setSido] = useState("");
  const [sigungu, setSigungu] = useState("");
  const [interests, setInterests] = useState<string[]>([]);
  const [notifyOptIn, setNotifyOptIn] = useState(true);
  const [email, setEmail] = useState("");

  useEffect(() => {
    getMeta()
      .then(setMeta)
      .catch(() => setError("서버에 연결할 수 없어요. 백엔드(api.py)가 실행 중인지 확인해주세요."));
  }, []);

  function toggleInterest(tag: string) {
    setInterests((prev) =>
      prev.includes(tag) ? prev.filter((v) => v !== tag) : [...prev, tag]
    );
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const student = await createStudent({
        department,
        grade,
        region_sido: sido,
        region_sigungu: sigungu,
        interest_categories: interests,
        email: email || null,
        notify_opt_in: notifyOptIn ? 1 : 0,
      });
      setStoredStudentId(student.id);
      onComplete(student.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "프로필 저장에 실패했어요.");
      setSubmitting(false);
    }
  }

  return (
    <div className="onboarding-card">
      <div className="steps">
        <div className={`step${step === 1 ? " on" : step > 1 ? " done" : ""}`}>
          <span className="dot">{step > 1 ? "✓" : 1}</span> 전공·학년
        </div>
        <div className={`step-line${step > 1 ? " done" : ""}`} />
        <div className={`step${step === 2 ? " on" : step > 2 ? " done" : ""}`}>
          <span className="dot">{step > 2 ? "✓" : 2}</span> 거주지역
        </div>
        <div className={`step-line${step > 2 ? " done" : ""}`} />
        <div className={`step${step === 3 ? " on" : ""}`}>
          <span className="dot">3</span> 관심분야·알림
        </div>
      </div>

      <div className="step-panel active" key={step}>
        {step === 1 && (
          <>
            <StepMajor
              college={college}
              department={department}
              grade={grade}
              onChangeCollege={(v) => {
                setCollege(v);
                setDepartment(getDepartments(v)[0] ?? "");
              }}
              onChangeDepartment={setDepartment}
              onChangeGrade={setGrade}
            />
            <div className="cta-row">
              <button className="btn btn-text" onClick={submit} disabled={submitting}>
                건너뛰기
              </button>
              <button className="btn btn-primary" onClick={() => setStep(2)}>
                다음 →
              </button>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            {meta ? (
              <StepRegion
                regions={meta.regions}
                sido={sido}
                sigungu={sigungu}
                onChangeSido={(v) => {
                  setSido(v);
                  setSigungu("");
                }}
                onChangeSigungu={setSigungu}
              />
            ) : (
              <p className="lead">지역 목록을 불러오는 중...</p>
            )}
            <div className="hint">
              해당 없거나 나중에 정해도 돼요.{" "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  setStep(3);
                }}
              >
                이 단계 건너뛰기
              </a>
            </div>
            <div className="cta-row">
              <button className="btn btn-ghost" onClick={() => setStep(1)}>
                ← 이전
              </button>
              <button className="btn btn-primary" onClick={() => setStep(3)}>
                다음 →
              </button>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            {meta ? (
              <StepInterest
                allInterests={meta.interest_categories}
                selected={interests}
                onToggle={toggleInterest}
                notifyOptIn={notifyOptIn}
                onToggleNotify={() => setNotifyOptIn((v) => !v)}
                email={email}
                onChangeEmail={setEmail}
              />
            ) : (
              <p className="lead">관심분야 목록을 불러오는 중...</p>
            )}
            {error && (
              <div className="hint" style={{ color: "var(--kw)" }}>
                {error}
              </div>
            )}
            <div className="cta-row">
              <button className="btn btn-ghost" onClick={() => setStep(2)}>
                ← 이전
              </button>
              <button className="btn btn-primary" onClick={submit} disabled={submitting}>
                {submitting ? "저장 중..." : "시작하기"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
