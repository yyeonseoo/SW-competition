import type {
  DashboardResponse,
  MetaResponse,
  Student,
  StudentInput,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `요청 실패: ${res.status}`);
  }
  return res.json();
}

export function getMeta() {
  return request<MetaResponse>("/api/meta");
}

export function createStudent(body: StudentInput) {
  return request<Student>("/api/students", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getStudent(id: number) {
  return request<Student>(`/api/students/${id}`);
}

export function patchStudent(id: number, body: Partial<StudentInput>) {
  return request<Student>(`/api/students/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function getDashboard(studentId: number) {
  return request<DashboardResponse>(`/api/dashboard?student_id=${studentId}`);
}
