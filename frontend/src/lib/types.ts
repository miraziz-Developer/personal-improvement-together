// Mirrors backend/src/pit/api/schemas.py

export type Category = "sport" | "code" | "study" | "reading" | "health" | "custom";
export type Mode = "free" | "stake";
export type DayStatus = "pending" | "done" | "frozen" | "missed" | "awaiting_review" | "paused";
export type ProofStatus = "pending" | "approved" | "rejected" | "needs_review";

export interface Task {
  key: string;
  title: string;
  minutes: number;
  required: boolean;
  at?: string | null; // local "HH:MM"; the coach reminds at that time
}
export type Week = Task[][];

export interface Milestone {
  theme: string;
  goal: string;
  lessons: string[];
}

export interface Roadmap {
  outcome: string;
  weeks: Milestone[];
  months: string[]; // what is true at the end of each 30 days
}

export interface Focus {
  week: number;
  weeks: number;
  theme: string;
  goal: string;
  lesson: string | null;
  month: number;
  month_goal: string | null;
}

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
  locale: "uz" | "ru";
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
  roadmap: Roadmap | null;
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
    focus: Focus | null;
  };
  week: Week;
  can_cancel: boolean;
  roadmap: Roadmap | null;
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
  roadmap: Roadmap | null;
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

export interface Badge {
  key: string;
  emoji: string;
  title: string;
  hint: string;
  earned: boolean;
}

export interface BusyBlock {
  label: string;
  weekdays: number[]; // 0 = Monday
  start: string;
  end: string;
}

export interface LifeGoal {
  key: string;
  goal: string;
  title: string;
  description: string;
  category: Category;
  difficulty: number;
  verification_prompt: string;
  week: Week;
  roadmap: Roadmap | null;
  participation_id: string | null;
}

export interface LifePlan {
  id: string;
  status: "draft" | "started";
  duration_days: number;
  wake: string;
  sleep: string;
  busy: BusyBlock[];
  budgets: number[];
  goals: LifeGoal[];
  runs: LifePlanRun[]; // challenges already running, timed into the routine
}

export interface LifePlanRun {
  participation_id: string;
  title: string;
  category: Category;
  week: Week;
}

export interface RoutineCandidate {
  participation_id: string;
  title: string;
  category: Category;
  tasks: { key: string; title: string; minutes: number; required: boolean; at: string | null; weekdays: number[] }[];
}

export interface CreatedChallenge {
  challenge: Challenge;
  participation_id: string | null;
  status: Participation["status"] | null;
  invite_code: string | null;
  members: number;
}

export interface RoutineItem {
  kind: "wake" | "busy" | "task" | "sleep";
  start: string;
  end: string | null;
  title: string;
  participation_id: string | null;
  challenge_title: string | null;
  category: Category | null;
  task: TodayTask | null;
  lesson: string | null;
}

export interface Routine {
  date: string;
  has_life_plan: boolean;
  frame: { wake: string; sleep: string; busy: BusyBlock[] } | null;
  items: RoutineItem[];
  untimed: RoutineItem[];
  months: { participation_id: string; title: string; month: number; goal: string }[];
}
