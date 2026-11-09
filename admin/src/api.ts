const TOKEN_KEY = "lsia_token";

export type Teacher = {
  id: string;
  name: string;
  role: {
    role: string;
    classes?: string[];
    subjects?: string[];
    permissions?: Record<string, boolean>;
  };
  revoked: boolean;
  has_password: boolean;
};

export type SchoolClass = {
  id: string;
  name: string;
  academic_year: string;
  class_teacher_id: string | null;
};

export type Subject = { id: string; name: string; code: string };

export type Student = {
  id: string;
  class_id: string | null;
  data: Record<string, string>;
  version: number;
  updated_by: string | null;
};

export type Device = {
  id: string;
  teacher_id: string;
  device_name: string;
  status: string;
  enrolled_at: string | null;
  last_sync_at: string | null;
};

export type EnrollmentPayload = {
  v: number;
  ticket: string;
  school_id: string;
  school_name: string;
  school_public_key: string;
  base_url: string;
  expires_at: number;
};

export type AttendanceRecord = {
  id: string;
  student_id: string;
  class_id: string | null;
  date: string;
  status: "present" | "absent" | "late" | "excused";
  recorded_by: string;
};

export type AttendanceSummary = {
  total_days: number;
  present: number;
  absent: number;
  late: number;
  excused: number;
  percentage: number;
};

export type ScoreRecord = {
  id: string;
  student_id: string;
  subject_id: string;
  term: string;
  ca_score: number | null;
  exam_score: number | null;
  total_score: number | null;
  grade: string;
  remark: string;
  recorded_by: string;
};

export type BroadsheetRow = {
  student_id: string;
  name: string;
  admission_number: string;
  subjects: Record<
    string,
    {
      ca_score: number | null;
      exam_score: number | null;
      total_score: number | null;
      grade: string;
      remark: string;
      position: string;
    } | null
  >;
  total_marks: number;
  subjects_taken: number;
  average_score: number;
  position: string;
};

export type Broadsheet = {
  school_name: string;
  class_id: string;
  class_name: string;
  academic_year: string;
  term: string;
  total_students: number;
  class_average: number;
  subjects: {
    id: string;
    name: string;
    code: string;
    stats: {
      count: number;
      highest: number | null;
      lowest: number | null;
      average: number | null;
    };
  }[];
  rows: BroadsheetRow[];
};

export type StudentReport = {
  school_name: string;
  student: {
    id: string;
    name: string;
    admission_number: string;
    gender: string;
    date_of_birth: string;
  };
  class: {
    id: string;
    name: string;
    academic_year: string;
    term: string;
    total_students: number;
    class_average: number;
  };
  performance: {
    total_marks: number;
    subjects_taken: number;
    average_score: number;
    position: string;
    subjects: {
      subject_id: string;
      subject_name: string;
      subject_code: string;
      ca_score: number | null;
      exam_score: number | null;
      total_score: number | null;
      grade: string;
      remark: string;
      position: string;
      class_average: number | null;
    }[];
  };
  attendance: AttendanceSummary;
  comments: {
    teacher_comment: string;
    principal_comment: string;
  };
};

export type ApprovalItem = {
  id: string;
  event_id: string;
  requested_by: string;
  approved_by: string | null;
  status: string;
  created_at: string | null;
  event: {
    operation: string;
    student_id: string | null;
    payload: any;
    timestamp: number;
  } | null;
};

export type ConflictItem = {
  id: string;
  operation: string;
  student_id: string | null;
  incoming_payload: any;
  incoming_teacher_id: string;
  incoming_device_id: string;
  incoming_timestamp: number;
  current_state: any;
  status: string;
};

export type AuditItem = {
  id: string;
  user_id: string;
  operation: string;
  entity_type: string;
  entity_id: string;
  timestamp: string | null;
  details: any;
};

export type ApiError = { code: string; message: string };

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(path, { ...init, headers });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = (body.error ?? { code: "INTERNAL", message: "Request failed." }) as ApiError;
    throw Object.assign(new Error(error.message), error);
  }
  return body as T;
}

export const api = {
  bootstrapStatus: () => request<{ needs_bootstrap: boolean }>("/api/v1/auth/bootstrap-status"),
  bootstrap: (payload: { name: string; password: string; school_name: string }) =>
    request<{ token: string; teacher: Teacher }>("/api/v1/auth/bootstrap", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (username: string, password: string) =>
    request<{ token: string; teacher: Teacher }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<Teacher>("/api/v1/auth/me"),
  school: () => request<{ id: string; name: string; public_key: string }>("/api/v1/school"),
  overview: () =>
    request<{
      students: number;
      teachers: number;
      events: number;
      pending_approvals: number;
      pending_conflicts: number;
      recent: { id: string; user_id: string; operation: string; entity_id: string; timestamp: string }[];
    }>("/api/v1/overview"),
  teachers: () => request<Teacher[]>("/api/v1/teachers"),
  createTeacher: (payload: object) =>
    request<Teacher>("/api/v1/teachers", { method: "POST", body: JSON.stringify(payload) }),
  patchTeacher: (id: string, payload: object) =>
    request<Teacher>(`/api/v1/teachers/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  revokeTeacher: (id: string) => request<Teacher>(`/api/v1/teachers/${id}/revoke`, { method: "POST" }),
  classes: () => request<SchoolClass[]>("/api/v1/classes"),
  createClass: (payload: object) =>
    request<SchoolClass>("/api/v1/classes", { method: "POST", body: JSON.stringify(payload) }),
  subjects: () => request<Subject[]>("/api/v1/subjects"),
  createSubject: (payload: object) =>
    request<Subject>("/api/v1/subjects", { method: "POST", body: JSON.stringify(payload) }),
  students: (q?: string, classId?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (classId) params.set("class_id", classId);
    const suffix = params.toString() ? `?${params}` : "";
    return request<Student[]>(`/api/v1/students${suffix}`);
  },
  createStudent: (payload: object) =>
    request<Student>("/api/v1/students", { method: "POST", body: JSON.stringify(payload) }),
  student: (id: string) => request<Student>(`/api/v1/students/${encodeURIComponent(id)}`),
  patchStudent: (id: string, payload: object) =>
    request<Student>(`/api/v1/students/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  devices: () => request<Device[]>("/api/v1/devices"),
  createEnrollmentTicket: (base_url?: string) =>
    request<EnrollmentPayload>("/api/v1/devices/enrollment-tickets", {
      method: "POST",
      body: JSON.stringify({ base_url: base_url || undefined }),
    }),
  revokeDevice: (id: string) => request<Device>(`/api/v1/devices/${id}/revoke`, { method: "POST" }),

  // Attendance
  attendance: (class_id?: string, student_id?: string, date?: string) => {
    const params = new URLSearchParams();
    if (class_id) params.set("class_id", class_id);
    if (student_id) params.set("student_id", student_id);
    if (date) params.set("date", date);
    const suffix = params.toString() ? `?${params}` : "";
    return request<AttendanceRecord[]>(`/api/v1/attendance${suffix}`);
  },
  recordAttendance: (payload: { class_id: string; date: string; records: { student_id: string; status: string }[] }) =>
    request<AttendanceRecord[]>("/api/v1/attendance", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  attendanceSummary: (class_id?: string, student_id?: string) => {
    const params = new URLSearchParams();
    if (class_id) params.set("class_id", class_id);
    if (student_id) params.set("student_id", student_id);
    const suffix = params.toString() ? `?${params}` : "";
    return request<AttendanceSummary>(`/api/v1/attendance/summary${suffix}`);
  },

  // Scores
  scores: (class_id?: string, subject_id?: string, term?: string, student_id?: string) => {
    const params = new URLSearchParams();
    if (class_id) params.set("class_id", class_id);
    if (subject_id) params.set("subject_id", subject_id);
    if (term) params.set("term", term);
    if (student_id) params.set("student_id", student_id);
    const suffix = params.toString() ? `?${params}` : "";
    return request<ScoreRecord[]>(`/api/v1/scores${suffix}`);
  },
  recordScores: (scores: { student_id: string; subject_id: string; term: string; ca_score?: number; exam_score?: number }[]) =>
    request<ScoreRecord[]>("/api/v1/scores", {
      method: "POST",
      body: JSON.stringify({ scores }),
    }),

  // Reports & Broadsheets
  broadsheet: (class_id: string, term: string) => {
    const params = new URLSearchParams({ class_id, term });
    return request<Broadsheet>(`/api/v1/reports/broadsheet?${params}`);
  },
  studentReport: (student_id: string, term: string) => {
    const params = new URLSearchParams({ student_id, term });
    return request<StudentReport>(`/api/v1/reports/student?${params}`);
  },

  // Approvals & Conflicts
  approvals: () => request<ApprovalItem[]>("/api/v1/approvals"),
  approve: (id: string) => request<any>(`/api/v1/approvals/${id}/approve`, { method: "POST" }),
  reject: (id: string, reason?: string) =>
    request<any>(`/api/v1/approvals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason: reason || "" }),
    }),
  conflicts: () => request<ConflictItem[]>("/api/v1/conflicts"),
  resolveConflict: (id: string, choice: string, custom_payload?: any) =>
    request<any>(`/api/v1/conflicts/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ choice, custom_payload }),
    }),

  // Audit
  audit: (limit = 50) => request<AuditItem[]>(`/api/v1/audit?limit=${limit}`),

  // System & Backups
  triggerBackup: () =>
    request<{ filename: string; size_bytes: number; created_at: string; signature: string }>(
      "/api/v1/system/backup",
      { method: "POST" }
    ),
  backups: () =>
    request<{ filename: string; size_bytes: number; created_at: string }[]>("/api/v1/system/backups"),
  restoreBackup: (filename: string) =>
    request<{ status: string; message: string }>("/api/v1/system/restore", {
      method: "POST",
      body: JSON.stringify({ filename }),
    }),
};
