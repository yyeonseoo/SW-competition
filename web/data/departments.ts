// 광운대학교 실제 단과대학→학과 목록 (사용자 제공 departments.json 기반, 2026-07-25).
// 전공 정밀 매칭 교체 지점은 recommend.py::department_matches — 여기는 온보딩/프로필 편집
// 화면의 단과대학→학과 cascading select에 쓰인다.
import raw from "./departments.json";

export interface College {
  id: string;
  name: string;
  departments: string[];
}

export const COLLEGES: College[] = raw.colleges;

export const COLLEGE_NAMES: string[] = COLLEGES.map((college) => college.name);

export function getDepartments(collegeName: string): string[] {
  return COLLEGES.find((college) => college.name === collegeName)?.departments ?? [];
}

export function findCollegeForDepartment(departmentName: string): string {
  const found = COLLEGES.find((college) => college.departments.includes(departmentName));
  return found ? found.name : COLLEGE_NAMES[0];
}

export const DEFAULT_COLLEGE = COLLEGE_NAMES[0];
export const DEFAULT_DEPARTMENT = COLLEGES[0]?.departments[0] ?? "";
