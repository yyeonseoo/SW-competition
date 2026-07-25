"use client";

import { COLLEGES, getDepartments } from "@/data/departments";

interface Props {
  college: string;
  department: string;
  grade: number;
  onChangeCollege: (v: string) => void;
  onChangeDepartment: (v: string) => void;
  onChangeGrade: (v: number) => void;
}

export default function StepMajor({
  college,
  department,
  grade,
  onChangeCollege,
  onChangeDepartment,
  onChangeGrade,
}: Props) {
  return (
    <>
      <h1>어떤 전공이세요?</h1>
      <p className="lead">공고의 지원 자격을 걸러내는 데 사용해요.</p>

      <div className="field">
        <label>단과대학</label>
        <select
          className="select"
          value={college}
          onChange={(e) => onChangeCollege(e.target.value)}
        >
          {COLLEGES.map((c) => (
            <option key={c.id} value={c.name}>
              {c.name}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>학과</label>
        <select
          className="select"
          value={department}
          onChange={(e) => onChangeDepartment(e.target.value)}
        >
          {getDepartments(college).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>학년</label>
        <select
          className="select"
          value={grade}
          onChange={(e) => onChangeGrade(Number(e.target.value))}
        >
          {[1, 2, 3, 4].map((g) => (
            <option key={g} value={g}>
              {g}학년
            </option>
          ))}
        </select>
      </div>
    </>
  );
}
