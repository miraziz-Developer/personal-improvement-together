// Mirrors backend/src/pit/api/schemas.py

export type Category = "sport" | "code" | "study" | "reading" | "health" | "custom";
export type Mode = "free" | "stake";
export type DayStatus = "pending" | "done" | "frozen" | "missed" | "awaiting_review";
export type ProofStatus = "pending" | "approved" | "rejected" | "needs_review";

export interface Task {
  key: string;
  title: string;
  minutes: number;
  required: boolean;
}
export type Week = Task[][];

export interface Region {
  id: string;
  name_uz: string;
  name_ru: string;
}

export interface Me {
  id: string;
  username: string;
  birth_date: string;
  birth_year: number;
  region_id: string;
  region_name: string;
  phone: string | null;
  phone_verified: boolean;
  role: "user" | "moderator" | "admin";
  wallet: { available: number; locked: number };
  points: number;
  active_challenges: number;
  completed_challenges: number;
  best_streak: number;
  unread_notifications: number;
  telegram_linked: boolean;
}

export interface Challenge {
  id: string;
  title: string;
  description: string;
  category: Category;
  duration_days: number;
  difficulty: number;
  proof_types: string[];
  stake_allowed: boolean;
  min_stake: number;
  max_stake: number;
  days_per_week: number;
  minutes_per_week: number;
  participants: number;
  week: Week;
}

export interface Participation {
  id: string;
  challenge_id: string;
  title: string;
  category: Category;
  status: "scheduled" | "active" | "completed" | "failed" | "cancelled";
  mode: Mode;
  stake: number;
  start_date: string;
  end_date: string;
  days_completed: number;
  total_days: number;
  current_streak: number;
  best_streak: number;
  freezes_left: number;
  today_status: DayStatus | null;
}

export interface TodayTask extends Task {
  proof_status: ProofStatus | null;
  reason: string | null;
}

export interface ParticipationDetail extends Participation {
  calendar: { date: string; status: DayStatus }[];
  today: {
    date: string;
    is_rest_day: boolean;
    status: DayStatus | null;
    tasks: TodayTask[];
    daily_code: string | null;
  };
  week: Week;
  can_cancel: boolean;
}

export interface Proof {
  id: string;
  status: ProofStatus;
  task_key: string;
  for_date: string;
  reason: string | null;
  reviewed_by_human: boolean;
}

export interface Plan {
  id: string;
  status: "draft" | "started";
  title: string;
  description: string;
  category: Category;
  duration_days: number;
  difficulty: number;
  verification_prompt: string;
  week: Week;
  budgets: number[];
  participation_id: string | null;
}

export interface Notification {
  id: string;
  moment: string;
  title: string;
  body: string;
  created_at: string;
  read: boolean;
}

export interface Leaderboard {
  scope: string;
  period: string;
  title: string;
  entries: { rank: number; user_id: string; username: string; points: number; is_me: boolean }[];
  me: { rank: number; points: number } | null;
  size: number;
  hidden: boolean;
}

export interface Wallet {
  available: number;
  locked: number;
  transactions: { id: string; kind: string; amount: number; created_at: string }[];
}

export interface ReviewItem {
  flagged: boolean;
  proof_id: string;
  username: string;
  challenge_title: string;
  task_key: string;
  for_date: string;
  text_note: string | null;
  image_url: string | null;
  ai_reason: string | null;
  ai_confidence: number | null;
  stake: number;
}

export interface GroupMember {
  username: string;
  is_me: boolean;
  is_owner: boolean;
  status: Participation["status"];
  today_status: DayStatus | null;
  current_streak: number;
  best_streak: number;
  days_completed: number;
  total_days: number;
}

export interface GroupBoard {
  invite_code: string;
  members: GroupMember[];
}

export interface GroupPreview {
  invite_code: string;
  challenge_title: string;
  challenge_description: string;
  category: Category;
  duration_days: number;
  owner: string;
  members: number;
  is_full: boolean;
  week: Week;
}

export type ReportReason = "abuse" | "bad_name" | "spam" | "other";

export interface ReportItem {
  id: string;
  reporter: string;
  reported: string;
  reason: ReportReason;
  details: string;
  created_at: string;
  reports_against: number;
}
