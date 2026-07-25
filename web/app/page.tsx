"use client";

import { useEffect, useState } from "react";
import Dashboard from "@/components/dashboard/Dashboard";
import OnboardingWizard from "@/components/onboarding/OnboardingWizard";
import { clearStoredStudentId, getStoredStudentId } from "@/lib/studentId";

export default function Home() {
  // undefined = 아직 localStorage 확인 전 (첫 렌더 깜빡임 방지), null = 학생 없음(온보딩 필요)
  const [studentId, setStudentId] = useState<number | null | undefined>(undefined);

  useEffect(() => {
    setStudentId(getStoredStudentId());
  }, []);

  if (studentId === undefined) {
    return null;
  }

  if (studentId === null) {
    return (
      <section className="view">
        <header className="app-header">
          <div className="brand">
            <span className="logo">KW</span>
            <span className="name">KW-LIFE</span>
            <span className="sub">광운대 맞춤 공고 보드</span>
          </div>
        </header>
        <div className="onboarding-body">
          <OnboardingWizard onComplete={(id) => setStudentId(id)} />
        </div>
      </section>
    );
  }

  return (
    <Dashboard
      studentId={studentId}
      onReset={() => {
        clearStoredStudentId();
        setStudentId(null);
      }}
    />
  );
}
