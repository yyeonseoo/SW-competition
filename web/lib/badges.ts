// common.py의 ACTIVITY_CATEGORIES(백엔드 분류 문자열) → prototype_v2.html의 뱃지 클래스/표시 라벨 매핑.
// 분류 로직 자체는 여기서 재구현하지 않는다 — 백엔드가 이미 분류한 activity_category를
// 화면에 어떻게 보여줄지만 결정하는 프레젠테이션 전용 매핑.
const BADGE_CLASS: Record<string, string> = {
  공모전: "contest",
  교육: "edu",
  "장학·지원": "scholar",
  대외활동: "activity",
  "인턴·채용": "intern",
};

const DISPLAY_LABEL: Record<string, string> = {
  공모전: "공모전",
  교육: "교육/특강",
  "장학·지원": "장학/지원",
  대외활동: "대외활동",
  "인턴·채용": "인턴/채용",
  기타: "기타",
};

export function badgeClassFor(category: string): string {
  return BADGE_CLASS[category] ?? "";
}

export function displayLabelFor(category: string): string {
  return DISPLAY_LABEL[category] ?? category;
}
