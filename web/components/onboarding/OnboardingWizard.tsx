"use client";

import { useEffect, useState } from "react";
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

  const [college, setCollege] = useState("");
  const [department, setDepartment] = useState("");
  const [grade, setGrade] = useState(0);
  const [enrollmentStatus, setEnrollmentStatus] = useState("");
  const [sido, setSido] = useState("");
  const [sigungu, setSigungu] = useState("");
  const [isInternational, setIsInternational] = useState<boolean | null>(null);
  const [interests, setInterests] = useState<string[]>([]);
  const [activityTypes, setActivityTypes] = useState<string[]>([]);
  const [preferenceText, setPreferenceText] = useState("");
  const [notifyOptIn, setNotifyOptIn] = useState(true);
  const [email, setEmail] = useState("");

  useEffect(() => {
    getMeta()
      .then(setMeta)
      .catch(() => setError("서버에 연결할 수 없어요. 백엔드가 실행 중인지 확인해주세요."));
  }, []);

  const stepOneComplete = Boolean(college && department && grade && enrollmentStatus);
  const stepTwoComplete = Boolean(sido && sigungu && isInternational !== null);

  function toggleInterest(tag: string) {
    setInterests((current) =>
      current.includes(tag) ? current.filter((value) => value !== tag) : [...current, tag]
    );
  }

  function toggleActivityType(tag: string) {
    setActivityTypes((current) =>
      current.includes(tag) ? current.filter((value) => value !== tag) : [...current, tag]
    );
  }

  async function submit() {
    if (!stepOneComplete || !stepTwoComplete) return;
    setSubmitting(true);
    setError(null);
    try {
      const student = await createStudent({
        department,
        grade,
        enrollment_status: enrollmentStatus,
        region_sido: sido,
        region_sigungu: sigungu,
        interest_categories: interests,
        preferred_activity_types: activityTypes,
        email: email || null,
        notify_opt_in: notifyOptIn ? 1 : 0,
        is_international: isInternational === true ? 1 : 0,
        preference_text: preferenceText,
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
        {["학교 정보", "자격 정보", "관심 정보"].map((label, index) => {
          const number = index + 1;
          return (
            <div className="step-wrap" key={label}>
              <div className={`step${step === number ? " on" : step > number ? " done" : ""}`}>
                <span className="dot">{step > number ? "✓" : number}</span>
                {label}
              </div>
              {number < 3 && <div className={`step-line${step > number ? " done" : ""}`} />}
            </div>
          );
        })}
      </div>

      <div className="step-panel active" key={step}>
        {step === 1 && (
          <>
            <StepMajor
              college={college}
              department={department}
              grade={grade}
              enrollmentStatus={enrollmentStatus}
              onChangeCollege={(value) => {
                setCollege(value);
                setDepartment("");
              }}
              onChangeDepartment={setDepartment}
              onChangeGrade={setGrade}
              onChangeEnrollmentStatus={setEnrollmentStatus}
            />
            <div className="required-help">
              {!stepOneComplete && "필수 항목을 모두 선택하면 다음 단계로 이동할 수 있어요."}
            </div>
            <div className="cta-row">
              <button
                className="btn btn-primary"
                onClick={() => setStep(2)}
                disabled={!stepOneComplete}
              >
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
                onChangeSido={(value) => {
                  setSido(value);
                  setSigungu("");
                }}
                onChangeSigungu={setSigungu}
                isInternational={isInternational}
                onChangeInternational={setIsInternational}
              />
            ) : (
              <p className="lead">지역 목록을 불러오는 중...</p>
            )}
            <div className="required-help">
              {!stepTwoComplete && "필수 항목을 모두 선택하면 다음 단계로 이동할 수 있어요."}
            </div>
            <div className="cta-row">
              <button className="btn btn-ghost" onClick={() => setStep(1)}>
                ← 이전
              </button>
              <button
                className="btn btn-primary"
                onClick={() => setStep(3)}
                disabled={!stepTwoComplete}
              >
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
                allActivityTypes={meta.preferred_activity_types}
                selectedActivityTypes={activityTypes}
                onToggleActivityType={toggleActivityType}
                notifyOptIn={notifyOptIn}
                onToggleNotify={() => setNotifyOptIn((value) => !value)}
                email={email}
                onChangeEmail={setEmail}
                preferenceText={preferenceText}
                onChangePreferenceText={setPreferenceText}
              />
            ) : (
              <p className="lead">관심분야 목록을 불러오는 중...</p>
            )}
            <div className="optional-note">이 단계는 선택사항이며 비워두어도 추천받을 수 있어요.</div>
            {error && <div className="form-error">{error}</div>}
            <div className="cta-row">
              <button className="btn btn-ghost" onClick={() => setStep(2)}>
                ← 이전
              </button>
              <button className="btn btn-primary" onClick={submit} disabled={submitting}>
                {submitting ? "저장 중..." : "추천 시작하기"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
