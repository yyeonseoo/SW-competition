export interface Student {
  id: number;
  name: string;
  department: string;
  grade: number;
  interest_categories: string[];
  region_sido: string;
  region_sigungu: string;
  email: string | null;
  notify_opt_in: number;
}

export interface ActivityCard {
  id: number;
  source: string;
  source_section: string;
  campus_scope: "교내" | "교외";
  title: string;
  url: string;
  activity_category: string;
  interest_categories: string[];
  region_sido: string;
  region_sigungu: string;
  region_detail: string;
  region_status: "resolved" | "nationwide" | "ambiguous" | "multiple";
  target: string[];
  target_raw: string;
  reference_date: string;
  date_basis: string;
  ocr_used: number;
  review_required: number;
  first_seen_at: string;
  last_seen_at: string;
  deadline_date: string;
  dday: number | null;
  is_new: boolean;
  region_relevant: boolean;
}

export interface DashboardResponse {
  student: Student;
  new_today_count: number;
  internal: {
    count: number;
    urgent: ActivityCard[];
    cards: ActivityCard[];
  };
  external: {
    count: number;
    urgent: ActivityCard[];
    kw_external_cards: ActivityCard[];
    linkareer_cards: ActivityCard[];
  };
}

export interface MetaResponse {
  interest_categories: string[];
  activity_categories: string[];
  regions: Record<string, string[]>;
}

export interface StudentInput {
  department: string;
  grade: number;
  region_sido: string;
  region_sigungu: string;
  interest_categories: string[];
  email?: string | null;
  notify_opt_in?: number;
}
