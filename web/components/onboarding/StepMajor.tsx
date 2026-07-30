"use client";

import CustomSelect from "@/components/ui/CustomSelect";
import { COLLEGES, getDepartments } from "@/data/departments";

interface Props {
  college: string;
  department: string;
  grade: number;
  enrollmentStatus: string;
  onChangeCollege: (v: string) => void;
  onChangeDepartment: (v: string) => void;
  onChangeGrade: (v: number) => void;
  onChangeEnrollmentStatus: (v: string) => void;
}

export default function StepMajor({
  college,
  department,
  grade,
  enrollmentStatus,
  onChangeCollege,
  onChangeDepartment,
  onChangeGrade,
  onChangeEnrollmentStatus,
}: Props) {
  return (
    <>
      <h1>학교 정보를 알려주세요</h1>
      <p className="lead">지원자격을 확인하기 위한 필수 정보예요.</p>

      <div className="field">
        <label>단과대학 · 필수</label>
        <CustomSelect
          value={college}
          placeholder="단과대학을 선택하세요"
          options={COLLEGES.map((item) => ({ value: item.name, label: item.name }))}
          onChange={onChangeCollege}
        />
      </div>
      <div className="field">
        <label>학과·학부 · 필수</label>
        <CustomSelect
          value={department}
          placeholder="학과·학부를 선택하세요"
          disabled={!college}
          options={getDepartments(college).map((name) => ({ value: name, label: name }))}
          onChange={onChangeDepartment}
        />
      </div>
      <div className="field">
        <label>학년 · 필수</label>
        <CustomSelect
          value={grade ? String(grade) : ""}
          placeholder="학년을 선택하세요"
          options={[1, 2, 3, 4].map((value) => ({
            value: String(value),
            label: `${value}학년`,
          }))}
          onChange={(value) => onChangeGrade(Number(value))}
        />
      </div>
      <div className="field">
        <label>학적 상태 · 필수</label>
        <CustomSelect
          value={enrollmentStatus}
          placeholder="학적 상태를 선택하세요"
          options={[
            { value: "freshman", label: "신입생" },
            { value: "enrolled", label: "재학생" },
            { value: "on_leave", label: "휴학생" },
            { value: "graduating", label: "졸업예정자" },
          ]}
          onChange={onChangeEnrollmentStatus}
        />
      </div>
    </>
  );
}
