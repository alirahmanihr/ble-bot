// ── Mock data for local admin panel testing ──
// Used when Railway backend is unreachable

// Inline types (avoids dependency on @hamrakar/shared)
interface MockUser {
  chat_id: number;
  role: 'employer' | 'job_seeker' | null;
  reg_date: string;
  created_at: string;
  emp_name?: string;
  emp_company?: string;
  emp_industry?: string;
  emp_phone?: string;
  emp_position?: string;
  js_name?: string;
  js_phone?: string;
  js_province?: string;
  js_job_title?: string;
  js_experience?: string;
  js_skills?: string;
  js_gender?: string;
}

interface MockJob {
  job_id: number;
  emp_cid: number;
  employer_name?: string;
  employer_company?: string;
  title: string;
  emp_type: string;
  location: string;
  salary: number;
  category: string;
  status: string;
  admin_approved?: number;
  reject_reason?: string;
  post_date?: string;
  created_at: string;
}

interface MockApplication {
  app_id: number;
  job_id: number;
  job_title?: string;
  seeker_cid: number;
  employer_id: number;
  employer_company?: string;
  seeker_name?: string;
  resume_text?: string;
  status: string;
  reject_reason?: string;
  sent_date?: string;
  created_at: string;
}

interface MockMessage {
  msg_id: number;
  chat_id: number;
  direction: 'in' | 'out';
  text: string;
  created_at: string;
}

export const mockStats = {
  total: 47,
  employers: 23,
  seekers: 24,
  active: 112,
  pending: 8,
  pending_apps: 5,
};

export const mockUsers: MockUser[] = [
  { chat_id: 100001, role: 'employer', reg_date: '1404-04-01', created_at: '2026-06-20T10:30:00Z', emp_name: 'حسین رضایی', emp_company: 'بازرگانی چوب دشتی', emp_industry: 'بازرگانی و فروش', emp_phone: '09103327545', emp_position: 'مدیر عامل' },
  { chat_id: 100002, role: 'employer', reg_date: '1404-04-02', created_at: '2026-06-21T09:00:00Z', emp_name: 'مریم حسنی', emp_company: 'املاک یاس', emp_industry: 'خدمات و گردشگری', emp_phone: '09135222400', emp_position: 'مدیر دفتر' },
  { chat_id: 100003, role: 'employer', reg_date: '1404-04-03', created_at: '2026-06-22T08:15:00Z', emp_name: 'علی محمدی', emp_company: 'شرکت طبیعت', emp_industry: 'صنعت و تولید', emp_phone: '09907153440', emp_position: 'مدیر منابع انسانی' },
  { chat_id: 100004, role: 'employer', reg_date: '1404-04-04', created_at: '2026-06-23T11:00:00Z', emp_name: 'زهرا احمدی', emp_company: 'گالری طلای فلوریا', emp_industry: 'بازرگانی و فروش', emp_phone: '09131516573', emp_position: 'مدیر فروش' },
  { chat_id: 100005, role: 'employer', reg_date: '1404-04-05', created_at: '2026-06-24T07:45:00Z', emp_name: 'رضا کریمی', emp_company: 'شرکت اورست', emp_industry: 'صنعت و تولید', emp_phone: '09132541169', emp_position: 'مدیر تولید' },
  { chat_id: 200001, role: 'job_seeker', reg_date: '1404-04-06', created_at: '2026-06-25T14:00:00Z', js_name: 'سارا نوری', js_phone: '09121234567', js_province: 'یزد', js_job_title: 'حسابدار', js_experience: '۳ سال', js_skills: 'حسابداری,اکسل,نرم‌افزار پیشرو', js_gender: 'خانم' },
  { chat_id: 200002, role: 'job_seeker', reg_date: '1404-04-07', created_at: '2026-06-26T10:30:00Z', js_name: 'محمد جوادی', js_phone: '09131234568', js_province: 'یزد', js_job_title: 'راننده لیفتراک', js_experience: '۵ سال', js_skills: 'رانندگی لیفتراک,گواهینامه', js_gender: 'آقا' },
  { chat_id: 200003, role: 'job_seeker', reg_date: '1404-04-08', created_at: '2026-06-27T09:00:00Z', js_name: 'فاطمه رحیمی', js_phone: '09141234569', js_province: 'یزد', js_job_title: 'منشی', js_experience: '۲ سال', js_skills: 'کامپیوتر,پاسخگویی,آفیس', js_gender: 'خانم' },
  { chat_id: 200004, role: 'job_seeker', reg_date: '1404-04-09', created_at: '2026-06-28T16:00:00Z', js_name: 'امیر حسینی', js_phone: '09151234570', js_province: 'یزد', js_job_title: 'برقکار صنعتی', js_experience: '۷ سال', js_skills: 'برق صنعتی,PLC,تابلو برق', js_gender: 'آقا' },
  { chat_id: 200005, role: 'job_seeker', reg_date: '1404-04-10', created_at: '2026-06-29T08:30:00Z', js_name: 'نیلوفر صادقی', js_phone: '09161234571', js_province: 'یزد', js_job_title: 'فروشنده', js_experience: '۱ سال', js_skills: 'فروش,بازاریابی,ارتباط با مشتری', js_gender: 'خانم' },
];

export const mockJobs: MockJob[] = [
  { job_id: 1, emp_cid: 100001, employer_name: 'حسین رضایی', employer_company: 'بازرگانی چوب دشتی', title: 'حسابدار', emp_type: 'تمام وقت', location: 'یزد', salary: 15000000, category: 'مالی و حسابداری', status: 'pending', admin_approved: 0, post_date: '1404-04-10', created_at: '2026-07-01T10:00:00Z' },
  { job_id: 2, emp_cid: 100002, employer_name: 'مریم حسنی', employer_company: 'املاک یاس', title: 'منشی (خانم)', emp_type: 'تمام وقت', location: 'یزد', salary: 12000000, category: 'امور اداری و دفتری', status: 'pending', admin_approved: 0, post_date: '1404-04-10', created_at: '2026-07-01T11:00:00Z' },
  { job_id: 3, emp_cid: 100003, employer_name: 'علی محمدی', employer_company: 'شرکت طبیعت', title: 'نگهبان (آقا)', emp_type: 'چرخشی', location: 'شهرک صنعتی یزد', salary: 11000000, category: 'امنیت و نظامی', status: 'pending', admin_approved: 0, post_date: '1404-04-09', created_at: '2026-06-30T09:00:00Z' },
  { job_id: 4, emp_cid: 100004, employer_name: 'زهرا احمدی', employer_company: 'گالری طلای فلوریا', title: 'فروشنده طلا', emp_type: 'تمام وقت', location: 'یزد، خیابان قیام', salary: 20000000, category: 'فروش و بازرگانی', status: 'pending', admin_approved: 0, post_date: '1404-04-11', created_at: '2026-07-02T08:00:00Z' },
  { job_id: 5, emp_cid: 100005, employer_name: 'رضا کریمی', employer_company: 'شرکت اورست', title: 'کارشناس کنترل کیفیت', emp_type: 'سه شیفت', location: 'یزد', salary: 13000000, category: 'تولید و صنعت', status: 'pending', admin_approved: 0, post_date: '1404-04-09', created_at: '2026-06-30T14:00:00Z' },
  { job_id: 6, emp_cid: 100001, employer_name: 'حسین رضایی', employer_company: 'بازرگانی چوب دشتی', title: 'انباردار', emp_type: 'تمام وقت', location: 'یزد', salary: 10000000, category: 'حمل و نقل', status: 'pending', admin_approved: 0, post_date: '1404-04-12', created_at: '2026-07-03T07:00:00Z' },
  { job_id: 7, emp_cid: 100003, employer_name: 'علی محمدی', employer_company: 'شرکت طبیعت', title: 'نیروی حراست', emp_type: 'چرخشی ۱۲ ساعته', location: 'شهرک صنعتی یزد', salary: 12000000, category: 'امنیت و نظامی', status: 'pending', admin_approved: 0, post_date: '1404-04-10', created_at: '2026-07-01T12:00:00Z' },
  { job_id: 8, emp_cid: 100002, employer_name: 'مریم حسنی', employer_company: 'املاک یاس', title: 'ویزیتور تلفنی (خانم)', emp_type: 'پاره وقت', location: 'یزد', salary: 9000000, category: 'بازاریابی و فروش', status: 'pending', admin_approved: 0, post_date: '1404-04-08', created_at: '2026-06-29T15:00:00Z' },
  // Active (approved) jobs
  { job_id: 101, emp_cid: 100001, employer_name: 'حسین رضایی', employer_company: 'بازرگانی چوب دشتی', title: 'کمک حسابدار', emp_type: 'تمام وقت', location: 'یزد', salary: 8000000, category: 'مالی و حسابداری', status: 'active', admin_approved: 1, post_date: '1404-03-25', created_at: '2026-06-15T10:00:00Z' },
  { job_id: 102, emp_cid: 100004, employer_name: 'زهرا احمدی', employer_company: 'گالری طلای فلوریا', title: 'حسابدار طلا', emp_type: 'تمام وقت', location: 'یزد، بازارخان', salary: 25000000, category: 'مالی و حسابداری', status: 'active', admin_approved: 1, post_date: '1404-03-28', created_at: '2026-06-18T09:00:00Z' },
  { job_id: 103, emp_cid: 100003, employer_name: 'علی محمدی', employer_company: 'معدن بافق', title: 'راننده بابکت', emp_type: 'چرخشی ۲۰-۱۰', location: 'بافق', salary: 18000000, category: 'مهندسی و فنی', status: 'active', admin_approved: 1, post_date: '1404-03-20', created_at: '2026-06-10T08:00:00Z' },
  { job_id: 104, emp_cid: 100003, employer_name: 'علی محمدی', employer_company: 'معدن بافق', title: 'مکانیک ماشین‌آلات سنگین', emp_type: 'چرخشی ۲۰-۱۰', location: 'بافق', salary: 20000000, category: 'مهندسی و فنی', status: 'active', admin_approved: 1, post_date: '1404-03-20', created_at: '2026-06-10T08:30:00Z' },
  { job_id: 105, emp_cid: 100005, employer_name: 'رضا کریمی', employer_company: 'شرکت اورست', title: 'راننده لیفتراک', emp_type: 'سه شیفت', location: 'یزد', salary: 14000000, category: 'حمل و نقل', status: 'active', admin_approved: 1, post_date: '1404-03-30', created_at: '2026-06-20T11:00:00Z' },
  { job_id: 106, emp_cid: 100005, employer_name: 'رضا کریمی', employer_company: 'شرکت اورست', title: 'کارگر ساده', emp_type: 'سه شیفت', location: 'یزد', salary: 9500000, category: 'تولید و صنعت', status: 'active', admin_approved: 1, post_date: '1404-03-30', created_at: '2026-06-20T11:30:00Z' },
  { job_id: 107, emp_cid: 100002, employer_name: 'مریم حسنی', employer_company: 'املاک یاس', title: 'بازاریاب', emp_type: 'تمام وقت', location: 'یزد', salary: 12000000, category: 'بازاریابی و فروش', status: 'active', admin_approved: 1, post_date: '1404-04-01', created_at: '2026-06-22T10:00:00Z' },
  { job_id: 108, emp_cid: 100001, employer_name: 'حسین رضایی', employer_company: 'بازرگانی چوب دشتی', title: 'راننده', emp_type: 'تمام وقت', location: 'یزد', salary: 10000000, category: 'حمل و نقل', status: 'active', admin_approved: 1, post_date: '1404-04-02', created_at: '2026-06-23T09:00:00Z' },
];

export const mockApplications: MockApplication[] = [
  { app_id: 1, job_id: 101, job_title: 'کمک حسابدار', seeker_cid: 200001, employer_id: 100001, employer_company: 'بازرگانی چوب دشتی', seeker_name: 'سارا نوری', resume_text: '۳ سال سابقه حسابداری، مسلط به نرم‌افزار پیشرو و اکسل', status: 'pending_admin', sent_date: '1404-04-11', created_at: '2026-07-02T09:00:00Z' },
  { app_id: 2, job_id: 103, job_title: 'راننده بابکت', seeker_cid: 200002, employer_id: 100003, employer_company: 'معدن بافق', seeker_name: 'محمد جوادی', resume_text: '۵ سال سابقه رانندگی ماشین‌آلات سنگین، آشنا به کار در معدن', status: 'pending_admin', sent_date: '1404-04-10', created_at: '2026-07-01T11:00:00Z' },
  { app_id: 3, job_id: 102, job_title: 'حسابدار طلا', seeker_cid: 200003, employer_id: 100004, employer_company: 'گالری طلای فلوریا', seeker_name: 'فاطمه رحیمی', resume_text: '۲ سال سابقه منشی‌گری و حسابداری، آشنا به کار با اکسل', status: 'pending_admin', sent_date: '1404-04-12', created_at: '2026-07-03T10:00:00Z' },
  { app_id: 4, job_id: 104, job_title: 'مکانیک ماشین‌آلات سنگین', seeker_cid: 200004, employer_id: 100003, employer_company: 'معدن بافق', seeker_name: 'امیر حسینی', resume_text: '۷ سال سابقه برق صنعتی و تعمیرات ماشین‌آلات', status: 'pending_admin', sent_date: '1404-04-11', created_at: '2026-07-02T14:00:00Z' },
  { app_id: 5, job_id: 107, job_title: 'بازاریاب', seeker_cid: 200005, employer_id: 100002, employer_company: 'املاک یاس', seeker_name: 'نیلوفر صادقی', resume_text: '۱ سال سابقه فروش و بازاریابی، روابط عمومی بالا', status: 'pending_admin', sent_date: '1404-04-12', created_at: '2026-07-03T08:00:00Z' },
];

export const mockWelcomeText = {
  key: 'welcome_text',
  value: '👋 به ربات همراکار خوش آمدید!\n\n🎯 این ربات پل ارتباطی بین کارفرمایان و کارجویان استان یزد است.\n\n📌 لطفاً نقش خود را انتخاب کنید:',
};

export const mockMessages: MockMessage[] = [
  { msg_id: 1, chat_id: 500001, direction: 'in' as const, text: '/start', created_at: '2026-07-13T10:00:00Z' },
  { msg_id: 2, chat_id: 500001, direction: 'out' as const, text: '👋 به ربات همراکار خوش آمدید!\n\n🎯 این ربات پل ارتباطی بین کارفرمایان و کارجویان استان یزد است.\n\n📌 لطفاً نقش خود را انتخاب کنید:', created_at: '2026-07-13T10:00:01Z' },
  { msg_id: 3, chat_id: 500001, direction: 'in' as const, text: 'کارفرما', created_at: '2026-07-13T10:00:05Z' },
  { msg_id: 4, chat_id: 500001, direction: 'out' as const, text: '🏢 لطفاً نام شرکت/سازمان خود را وارد کنید:', created_at: '2026-07-13T10:00:06Z' },
];
