const KEY = "kwlife_student_id";

export function getStoredStudentId(): number | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(KEY);
  return raw ? Number(raw) : null;
}

export function setStoredStudentId(id: number) {
  window.localStorage.setItem(KEY, String(id));
}

export function clearStoredStudentId() {
  window.localStorage.removeItem(KEY);
}
