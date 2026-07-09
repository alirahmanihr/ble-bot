// ── User ──
export interface User {
  chat_id: number;
  role: 'employer' | 'job_seeker' | null;
  reg_date: string;
  created_at: string;

  // Employer fields
  emp_name?: string;
  emp_company?: string;
  emp_industry?: string;
  emp_phone?: string;
  emp_position?: string;
  emp_address?: string;
  emp_email?: string;
  emp_website?: string;
  emp_gender?: string;
  emp_age?: string;

  // Job seeker fields
  js_name?: string;
  js_phone?: string;
  js_province?: string;
  js_job_title?: string;
  js_experience?: string;
  js_salary?: number;
  js_dob?: string;
  js_gender?: string;
  js_relocate?: string;
  js_cities?: string;
  js_categories?: string;
  js_skills?: string;
  js_rating?: number;
}

// ── Job ──
export interface Job {
  job_id: number;
  emp_cid: number;
  employer_name?: string;
  employer_company?: string;
  title: string;
  emp_type: string;
  location: string;
  salary: number;
  category: string;
  gender_req?: string;
  age_req?: string;
  status: 'active' | 'pending' | 'rejected' | 'draft' | 'pending_admin';
  admin_approved?: number;
  reject_reason?: string;
  post_date?: string;
  created_at: string;
}

// ── Application ──
export interface Application {
  app_id: number;
  job_id: number;
  job_title?: string;
  seeker_cid: number;
  employer_id: number;
  employer_company?: string;
  seeker_name?: string;
  resume_file?: string;
  resume_text?: string;
  status: 'pending_admin' | 'approved' | 'rejected' | 'draft';
  reject_reason?: string;
  sent_date?: string;
  created_at: string;
}

// ── Resume Request ──
export interface ResumeRequest {
  req_id: number;
  job_id: number;
  employer_id: number;
  seeker_id: number;
  seeker_name: string;
  employer_company: string;
  seeker_status: string;
  admin_status: string;
  created_at: string;
}

// ── Bot Message ──
export interface BotMessage {
  msg_id: number;
  chat_id: number;
  direction: 'in' | 'out';
  text: string;
  created_at: string;
}

// ── Stats ──
export interface Stats {
  total: number;
  employers: number;
  seekers: number;
  active: number;
  pending: number;
  pending_apps: number;
}

// ── API Responses ──
export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
}

export interface UsersResponse {
  count: number;
  users: User[];
}

export interface JobsResponse {
  count: number;
  jobs: Job[];
}

export interface ApplicationsResponse {
  count: number;
  applications: Application[];
}

export interface MessagesResponse {
  count: number;
  messages: BotMessage[];
}

// ── Settings ──
export interface WelcomeTextSetting {
  key: string;
  value: string;
}

export interface BotSettings {
  welcome_text: string;
  employer_menu: string[][];
  seeker_menu: string[][];
}

// ── Constants ──
export const CATEGORIES = [
  'برنامه‌نویسی و توسعه',
  'طراحی و گرافیک',
  'مدیریت و منابع انسانی',
  'بازاریابی و فروش',
  'مالی و حسابداری',
  'مهندسی و فنی',
  'آموزش و تدریس',
  'پشتیبانی و خدمات',
  'پزشکی و پیراپزشکی',
  'حقوقی و امور قراردادها',
  'حمل و نقل',
  'تولید و صنعت',
  'فروش و بازرگانی',
  'مدیریت پروژه',
  'امور اداری و دفتری',
  'رسانه و تولید محتوا',
  'امنیت و نظامی',
  'انرژی و نفت و گاز',
  'گردشگری و هتلداری',
  'سایر موارد',
] as const;

export const PROVINCES = [
  'تهران', 'اصفهان', 'مشهد', 'شیراز', 'تبریز',
  'اهواز', 'کرج', 'قم', 'یزد', 'رشت',
  'کرمان', 'ارومیه', 'زاهدان', 'بندرعباس', 'اردبیل',
  'اراک', 'ساری', 'همدان', 'سنندج', 'قزوین',
  'گرگان', 'بوشهر', 'خرم‌آباد', 'شهرکرد', 'ایلام',
  'بیرجند', 'بجنورد', 'زنجان', 'سمنان', 'یزد',
] as const;

export const INDUSTRIES = [
  'فناوری اطلاعات و نرم‌افزار',
  'صنعت و تولید',
  'ساختمان و عمران',
  'بازرگانی و فروش',
  'آموزش و پژوهش',
  'پزشکی و سلامت',
  'مالی و بانکی',
  'حمل و نقل و لجستیک',
  'خدمات و گردشگری',
  'کشاورزی',
  'رسانه و تبلیغات',
  'انرژی و نفت',
  'حقوقی و قراردادها',
  'تولید محتوا',
  'منابع انسانی',
] as const;
