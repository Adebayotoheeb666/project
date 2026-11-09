import { FormEvent, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import {
  ApprovalItem,
  AttendanceSummary,
  AuditItem,
  Broadsheet,
  ConflictItem,
  Device,
  EnrollmentPayload,
  SchoolClass,
  Student,
  StudentReport,
  Subject,
  Teacher,
  api,
  getToken,
  setToken,
} from "./api";

function useSession() {
  const [teacher, setTeacher] = useState<Teacher | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api
      .me()
      .then(setTeacher)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);
  return { teacher, setTeacher, ready };
}

function Gate({ onAuthed }: { onAuthed: (teacher: Teacher) => void }) {
  const [needsBootstrap, setNeedsBootstrap] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    api.bootstrapStatus().then((r) => setNeedsBootstrap(r.needs_bootstrap));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError("");
    try {
      const result = needsBootstrap
        ? await api.bootstrap({
            name: String(form.get("name") || ""),
            password: String(form.get("password") || ""),
            school_name: String(form.get("school_name") || ""),
          })
        : await api.login(String(form.get("username") || ""), String(form.get("password") || ""));
      setToken(result.token);
      onAuthed(result.teacher);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="gate">
      <form className="ledger" onSubmit={submit}>
        <header>
          <h1>{needsBootstrap ? "Open the register" : "School computer"}</h1>
          <p className="muted">
            {needsBootstrap
              ? "Create the first administrator. This computer keeps every student record on the school premises."
              : "Sign in to the local school register. No internet required."}
          </p>
        </header>
        {error ? <div className="banner">{error}</div> : null}
        {needsBootstrap ? (
          <>
            <label className="field">
              <span>School name</span>
              <input name="school_name" required defaultValue="Greenfield College" />
            </label>
            <label className="field">
              <span>Administrator name</span>
              <input name="name" required autoComplete="name" />
            </label>
            <label className="field">
              <span>Password</span>
              <input name="password" type="password" required minLength={8} autoComplete="new-password" />
            </label>
          </>
        ) : (
          <>
            <label className="field">
              <span>Account id</span>
              <input name="username" required autoComplete="username" defaultValue="admin" />
            </label>
            <label className="field">
              <span>Password</span>
              <input name="password" type="password" required autoComplete="current-password" />
            </label>
          </>
        )}
        <button className="btn" disabled={pending || needsBootstrap === null}>
          {pending ? "Working…" : needsBootstrap ? "Create administrator" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

function Shell({ teacher, onSignOut }: { teacher: Teacher; onSignOut: () => void }) {
  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <strong>LSIA</strong>
          <small>Local school register</small>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Desk
          </NavLink>
          <NavLink to="/students">Students</NavLink>
          <NavLink to="/classes">Classes</NavLink>
          <NavLink to="/subjects">Subjects</NavLink>
          <NavLink to="/teachers">Teachers</NavLink>
          <NavLink to="/devices">Phones</NavLink>
          <NavLink to="/attendance">Attendance</NavLink>
          <NavLink to="/scores">Scores</NavLink>
          <NavLink to="/broadsheet">Broadsheet & Reports</NavLink>
          <NavLink to="/approvals">Approvals & Conflicts</NavLink>
          <NavLink to="/audit">Audit Desk</NavLink>
        </nav>
        <div className="who">
          <div>{teacher.name}</div>
          <small>{teacher.id}</small>
          <button className="btn ghost" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      </aside>
      <main>
        <Routes>
          <Route path="/" element={<Desk />} />
          <Route path="/students" element={<Students />} />
          <Route path="/students/:id" element={<StudentPage />} />
          <Route path="/classes" element={<Classes />} />
          <Route path="/subjects" element={<Subjects />} />
          <Route path="/teachers" element={<Teachers />} />
          <Route path="/devices" element={<Devices />} />
          <Route path="/attendance" element={<AttendanceView />} />
          <Route path="/scores" element={<ScoresView />} />
          <Route path="/broadsheet" element={<BroadsheetView />} />
          <Route path="/reports/:studentId" element={<ReportCardView />} />
          <Route path="/approvals" element={<ApprovalsView />} />
          <Route path="/audit" element={<AuditView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function Desk() {
  const [school, setSchool] = useState("");
  const [overview, setOverview] = useState<Awaited<ReturnType<typeof api.overview>> | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([api.school(), api.overview()])
      .then(([s, o]) => {
        setSchool(s.name);
        setOverview(o);
      })
      .catch((err) => setError(err.message));
  }, []);
  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>{school || "School desk"}</h1>
          <p className="muted">Today’s register lives on this computer. Issue a phone enrollment code from Phones so teachers can work offline.</p>
        </div>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      {overview ? (
        <div className="desk">
          <div className="panel">
            <h2>Recent events</h2>
            {overview.recent.length === 0 ? <p className="muted">No events yet.</p> : null}
            {overview.recent.map((row) => (
              <div className="row" key={row.id}>
                <span>{row.operation.replaceAll("_", " ")}</span>
                <span>{row.entity_id}</span>
                <span className="muted">{row.user_id}</span>
              </div>
            ))}
          </div>
          <div className="panel">
            <h2>School Status</h2>
            <p>
              <strong>{overview.students}</strong> students · <strong>{overview.teachers}</strong> staff accounts
            </p>
            <p>
              <strong>{overview.events}</strong> signed events
            </p>
            {overview.pending_approvals > 0 ? (
              <div className="banner" style={{ background: "#fef3c7", color: "#92400e" }}>
                ⚠️ {overview.pending_approvals} pending approval requests
              </div>
            ) : null}
            {overview.pending_conflicts > 0 ? (
              <div className="banner" style={{ background: "#fee2e2", color: "#991b1b" }}>
                ⚡ {overview.pending_conflicts} concurrent edit conflicts to resolve
              </div>
            ) : null}
            <p className="muted">Every mutation produces an append-only signed cryptographic event. The school computer is the ultimate authority.</p>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Students() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Student[]>([]);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [q, setQ] = useState("");
  const [classId, setClassId] = useState("");
  const [error, setError] = useState("");

  async function refresh(query = q, klass = classId) {
    const [students, classRows] = await Promise.all([api.students(query, klass || undefined), api.classes()]);
    setRows(students);
    setClasses(classRows);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    try {
      await api.createStudent({
        id: String(form.get("id")),
        class_id: String(form.get("class_id") || "") || null,
        data: {
          first_name: String(form.get("first_name")),
          last_name: String(form.get("last_name")),
          admission_number: String(form.get("admission_number")),
          gender: String(form.get("gender")),
        },
      });
      event.currentTarget.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save student.");
    }
  }

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Students</h1>
          <p className="muted">Search the local directory. Records stay on this machine.</p>
        </div>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      <form className="panel" onSubmit={create} style={{ marginBottom: 24 }}>
        <h2>Admit a student</h2>
        <div className="form-grid">
          <label className="field">
            <span>Student id</span>
            <input name="id" required placeholder="FUTA/SS2A/042" />
          </label>
          <label className="field">
            <span>Class</span>
            <select name="class_id" defaultValue="">
              <option value="">Unassigned</option>
              {classes.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>First name</span>
            <input name="first_name" required />
          </label>
          <label className="field">
            <span>Last name</span>
            <input name="last_name" required />
          </label>
          <label className="field">
            <span>Admission number</span>
            <input name="admission_number" />
          </label>
          <label className="field">
            <span>Gender</span>
            <input name="gender" />
          </label>
        </div>
        <button className="btn">Save to register</button>
      </form>
      <div className="toolbar">
        <input
          placeholder="Search name or id"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") refresh().catch((err) => setError(err.message));
          }}
        />
        <select
          value={classId}
          onChange={(e) => {
            setClassId(e.target.value);
            refresh(q, e.target.value).catch((err) => setError(err.message));
          }}
        >
          <option value="">All classes</option>
          {classes.map((row) => (
            <option key={row.id} value={row.id}>
              {row.name}
            </option>
          ))}
        </select>
        <button className="btn ghost" type="button" onClick={() => refresh().catch((err) => setError(err.message))}>
          Search
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Id</th>
            <th>Name</th>
            <th>Class</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.id}</td>
              <td>
                {row.data.first_name} {row.data.last_name}
              </td>
              <td>{row.class_id || "—"}</td>
              <td>
                <button className="btn ghost" onClick={() => navigate(`/students/${encodeURIComponent(row.id)}`)}>
                  Open
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function StudentPage() {
  const { id = "" } = useParams();
  const decoded = decodeURIComponent(id);
  const [student, setStudent] = useState<Student | null>(null);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.student(decoded), api.classes()])
      .then(([s, c]) => {
        setStudent(s);
        setClasses(c);
      })
      .catch((err) => setError(err.message));
  }, [decoded]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!student) return;
    const form = new FormData(event.currentTarget);
    setError("");
    try {
      const updated = await api.patchStudent(student.id, {
        expected_version: student.version,
        class_id: String(form.get("class_id") || "") || null,
        data: {
          first_name: String(form.get("first_name")),
          last_name: String(form.get("last_name")),
          admission_number: String(form.get("admission_number")),
          gender: String(form.get("gender")),
          date_of_birth: String(form.get("date_of_birth")),
          guardian_name: String(form.get("guardian_name")),
          guardian_phone: String(form.get("guardian_phone")),
          address: String(form.get("address")),
        },
      });
      setStudent(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update student.");
    }
  }

  if (!student && !error) return <section className="page">Loading…</section>;
  if (!student) return <section className="page"><div className="banner">{error}</div></section>;

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>
            {student.data.first_name} {student.data.last_name}
          </h1>
          <p className="muted">
            {student.id} · version {student.version}
          </p>
        </div>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      <form className="panel" onSubmit={save}>
        <div className="form-grid">
          <label className="field">
            <span>First name</span>
            <input name="first_name" defaultValue={student.data.first_name} required />
          </label>
          <label className="field">
            <span>Last name</span>
            <input name="last_name" defaultValue={student.data.last_name} required />
          </label>
          <label className="field">
            <span>Class</span>
            <select name="class_id" defaultValue={student.class_id ?? ""}>
              <option value="">Unassigned</option>
              {classes.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Admission number</span>
            <input name="admission_number" defaultValue={student.data.admission_number} />
          </label>
          <label className="field">
            <span>Gender</span>
            <input name="gender" defaultValue={student.data.gender} />
          </label>
          <label className="field">
            <span>Date of birth</span>
            <input name="date_of_birth" defaultValue={student.data.date_of_birth} />
          </label>
          <label className="field">
            <span>Guardian</span>
            <input name="guardian_name" defaultValue={student.data.guardian_name} />
          </label>
          <label className="field">
            <span>Guardian phone</span>
            <input name="guardian_phone" defaultValue={student.data.guardian_phone} />
          </label>
          <label className="field wide">
            <span>Address</span>
            <textarea name="address" defaultValue={student.data.address} />
          </label>
        </div>
        <button className="btn">Save changes</button>
      </form>
    </section>
  );
}

function Classes() {
  const [rows, setRows] = useState<SchoolClass[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api.classes().then(setRows).catch((err) => setError(err.message));
  }, []);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const row = await api.createClass({
        id: String(form.get("id")),
        name: String(form.get("name")),
        academic_year: String(form.get("academic_year")),
      });
      setRows((current) => [...current, row]);
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create class.");
    }
  }
  return (
    <section className="page">
      <div className="page-head">
        <h1>Classes</h1>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      <form className="form-grid panel" onSubmit={create}>
        <label className="field">
          <span>Id</span>
          <input name="id" required placeholder="SS2A" />
        </label>
        <label className="field">
          <span>Name</span>
          <input name="name" required placeholder="SS2 A" />
        </label>
        <label className="field">
          <span>Academic year</span>
          <input name="academic_year" required placeholder="2025/2026" />
        </label>
        <div className="field">
          <span>&nbsp;</span>
          <button className="btn">Add class</button>
        </div>
      </form>
      <table>
        <thead>
          <tr>
            <th>Id</th>
            <th>Name</th>
            <th>Year</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.id}</td>
              <td>{row.name}</td>
              <td>{row.academic_year}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Subjects() {
  const [rows, setRows] = useState<Subject[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api.subjects().then(setRows).catch((err) => setError(err.message));
  }, []);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const row = await api.createSubject({
        id: String(form.get("id")),
        name: String(form.get("name")),
        code: String(form.get("code")),
      });
      setRows((current) => [...current, row]);
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create subject.");
    }
  }
  return (
    <section className="page">
      <div className="page-head">
        <h1>Subjects</h1>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      <form className="form-grid panel" onSubmit={create}>
        <label className="field">
          <span>Id</span>
          <input name="id" required placeholder="MATH" />
        </label>
        <label className="field">
          <span>Name</span>
          <input name="name" required placeholder="Mathematics" />
        </label>
        <label className="field">
          <span>Code</span>
          <input name="code" required placeholder="MATH" />
        </label>
        <div className="field">
          <span>&nbsp;</span>
          <button className="btn">Add subject</button>
        </div>
      </form>
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.code}</td>
              <td>{row.name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Devices() {
  const [rows, setRows] = useState<Device[]>([]);
  const [ticket, setTicket] = useState<EnrollmentPayload | null>(null);
  const [baseUrl, setBaseUrl] = useState("http://192.168.0.10:8080");
  const [error, setError] = useState("");

  async function refresh() {
    setRows(await api.devices());
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  async function issue(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      const payload = await api.createEnrollmentTicket(baseUrl);
      setTicket(payload);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not issue enrollment code.");
    }
  }

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Teacher phones</h1>
          <p className="muted">Generate a QR enrollment code. The teacher scans it on the school Wi-Fi, then the phone keeps records locally until it can sync.</p>
        </div>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      <form className="panel" onSubmit={issue} style={{ marginBottom: 24 }}>
        <h2>New enrollment code</h2>
        <label className="field">
          <span>School computer address on the LAN</span>
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} required />
        </label>
        <button className="btn">Issue QR code</button>
        <p className="muted">The code is valid for 15 minutes and can enroll one phone.</p>
      </form>
      {ticket ? (
        <div className="panel" style={{ marginBottom: 24 }}>
          <h2>Scan this on the teacher phone</h2>
          <img
            className="qr"
            alt="Enrollment QR code"
            src={`/api/v1/devices/enrollment-tickets/${ticket.ticket}/qr.png`}
          />
          <p className="muted">
            {ticket.school_name} · {ticket.base_url}
          </p>
          <pre className="json">{JSON.stringify(ticket, null, 2)}</pre>
          <button
            className="btn ghost"
            type="button"
            onClick={() => navigator.clipboard.writeText(JSON.stringify(ticket))}
          >
            Copy enrollment JSON
          </button>
        </div>
      ) : null}
      <table>
        <thead>
          <tr>
            <th>Device</th>
            <th>Teacher</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>
                {row.device_name}
                <div className="muted">{row.id}</div>
              </td>
              <td>{row.teacher_id}</td>
              <td>
                {row.status === "revoked" ? <span className="chip warn">revoked</span> : row.status}
              </td>
              <td>
                {row.status === "revoked" ? null : (
                  <button
                    className="btn danger"
                    onClick={async () => {
                      try {
                        const updated = await api.revokeDevice(row.id);
                        setRows((current) => current.map((item) => (item.id === updated.id ? updated : item)));
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Could not revoke device.");
                      }
                    }}
                  >
                    Revoke
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Teachers() {
  const [rows, setRows] = useState<Teacher[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api.teachers().then(setRows).catch((err) => setError(err.message));
  }, []);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const row = await api.createTeacher({
        id: String(form.get("id")),
        name: String(form.get("name")),
        password: String(form.get("password")),
        role: {
          role: "teacher",
          classes: String(form.get("classes") || "")
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          subjects: String(form.get("subjects") || "")
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        },
      });
      setRows((current) => [...current, row]);
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create teacher.");
    }
  }
  return (
    <section className="page">
      <div className="page-head">
        <h1>Teachers</h1>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      <form className="panel" onSubmit={create} style={{ marginBottom: 24 }}>
        <h2>Enroll staff</h2>
        <div className="form-grid">
          <label className="field">
            <span>Account id</span>
            <input name="id" required placeholder="teacher_ade" />
          </label>
          <label className="field">
            <span>Name</span>
            <input name="name" required />
          </label>
          <label className="field">
            <span>Password</span>
            <input name="password" type="password" minLength={8} />
          </label>
          <label className="field">
            <span>Classes (comma separated)</span>
            <input name="classes" placeholder="SS1A, SS2A" />
          </label>
          <label className="field wide">
            <span>Subjects (comma separated)</span>
            <input name="subjects" placeholder="MATHEMATICS" />
          </label>
        </div>
        <button className="btn">Save teacher</button>
      </form>
      <table>
        <thead>
          <tr>
            <th>Id</th>
            <th>Name</th>
            <th>Role</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.id}</td>
              <td>{row.name}</td>
              <td>
                {row.role.role}
                {row.revoked ? <span className="chip warn"> revoked</span> : null}
              </td>
              <td>
                {row.revoked ? null : (
                  <button
                    className="btn danger"
                    onClick={async () => {
                      try {
                        const updated = await api.revokeTeacher(row.id);
                        setRows((current) => current.map((item) => (item.id === updated.id ? updated : item)));
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Could not revoke.");
                      }
                    }}
                  >
                    Revoke
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function AttendanceView() {
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [selectedClass, setSelectedClass] = useState("");
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [students, setStudents] = useState<Student[]>([]);
  const [statusMap, setStatusMap] = useState<Record<string, "present" | "absent" | "late" | "excused">>({});
  const [summary, setSummary] = useState<AttendanceSummary | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    api.classes().then((c) => {
      setClasses(c);
      if (c.length > 0 && !selectedClass) setSelectedClass(c[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedClass) return;
    Promise.all([
      api.students(undefined, selectedClass),
      api.attendance(selectedClass, undefined, selectedDate),
      api.attendanceSummary(selectedClass),
    ])
      .then(([stu, att, sum]) => {
        setStudents(stu);
        setSummary(sum);
        const map: Record<string, "present" | "absent" | "late" | "excused"> = {};
        for (const s of stu) {
          const rec = att.find((a) => a.student_id === s.id);
          map[s.id] = rec ? rec.status : "present";
        }
        setStatusMap(map);
      })
      .catch((err) => setError(err.message));
  }, [selectedClass, selectedDate]);

  async function save() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const records = Object.entries(statusMap).map(([student_id, status]) => ({ student_id, status }));
      await api.recordAttendance({
        class_id: selectedClass,
        date: selectedDate,
        records,
      });
      setSuccess("Attendance saved successfully.");
      const sum = await api.attendanceSummary(selectedClass);
      setSummary(sum);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save attendance.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Attendance</h1>
          <p className="muted">Record and verify daily attendance for each class. Works offline.</p>
        </div>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      {success ? <div className="banner" style={{ background: "#dcfce7", color: "#166534" }}>{success}</div> : null}
      <div className="toolbar">
        <select value={selectedClass} onChange={(e) => setSelectedClass(e.target.value)}>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
      </div>

      {summary ? (
        <div className="panel" style={{ marginBottom: 20 }}>
          <p>
            <strong>Class Attendance Summary:</strong> {summary.percentage}% present · {summary.present} Present · {summary.absent} Absent · {summary.late} Late
          </p>
        </div>
      ) : null}

      <table>
        <thead>
          <tr>
            <th>Student</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {students.map((s) => (
            <tr key={s.id}>
              <td>
                <strong>{s.data.first_name} {s.data.last_name}</strong>
                <div className="muted">{s.id}</div>
              </td>
              <td>
                <select
                  value={statusMap[s.id] || "present"}
                  onChange={(e) =>
                    setStatusMap((prev) => ({
                      ...prev,
                      [s.id]: e.target.value as "present" | "absent" | "late" | "excused",
                    }))
                  }
                >
                  <option value="present">Present</option>
                  <option value="absent">Absent</option>
                  <option value="late">Late</option>
                  <option value="excused">Excused</option>
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 20 }}>
        <button className="btn" disabled={saving || students.length === 0} onClick={save}>
          {saving ? "Saving…" : "Save Attendance"}
        </button>
      </div>
    </section>
  );
}

function ScoresView() {
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedClass, setSelectedClass] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedTerm, setSelectedTerm] = useState("2025/2026-Term1");
  const [students, setStudents] = useState<Student[]>([]);
  const [scoresMap, setScoresMap] = useState<Record<string, { ca: string; exam: string }>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    Promise.all([api.classes(), api.subjects()]).then(([c, sub]) => {
      setClasses(c);
      setSubjects(sub);
      if (c.length > 0 && !selectedClass) setSelectedClass(c[0].id);
      if (sub.length > 0 && !selectedSubject) setSelectedSubject(sub[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedClass || !selectedSubject) return;
    Promise.all([
      api.students(undefined, selectedClass),
      api.scores(selectedClass, selectedSubject, selectedTerm),
    ])
      .then(([stu, scs]) => {
        setStudents(stu);
        const map: Record<string, { ca: string; exam: string }> = {};
        for (const s of stu) {
          const rec = scs.find((item) => item.student_id === s.id);
          map[s.id] = {
            ca: rec && rec.ca_score !== null ? String(rec.ca_score) : "",
            exam: rec && rec.exam_score !== null ? String(rec.exam_score) : "",
          };
        }
        setScoresMap(map);
      })
      .catch((err) => setError(err.message));
  }, [selectedClass, selectedSubject, selectedTerm]);

  async function save() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const records = Object.entries(scoresMap).map(([student_id, val]) => ({
        student_id,
        subject_id: selectedSubject,
        term: selectedTerm,
        ca_score: val.ca !== "" ? parseFloat(val.ca) : undefined,
        exam_score: val.exam !== "" ? parseFloat(val.exam) : undefined,
      }));
      await api.recordScores(records);
      setSuccess("Scores recorded successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save scores.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Academic Scores</h1>
          <p className="muted">Enter Continuous Assessment (max 40) and Examination (max 60) scores.</p>
        </div>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      {success ? <div className="banner" style={{ background: "#dcfce7", color: "#166534" }}>{success}</div> : null}
      <div className="toolbar">
        <select value={selectedClass} onChange={(e) => setSelectedClass(e.target.value)}>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select value={selectedSubject} onChange={(e) => setSelectedSubject(e.target.value)}>
          {subjects.map((sub) => (
            <option key={sub.id} value={sub.id}>
              {sub.name} ({sub.code})
            </option>
          ))}
        </select>
        <input
          value={selectedTerm}
          onChange={(e) => setSelectedTerm(e.target.value)}
          placeholder="Term (e.g. 2025/2026-Term1)"
        />
      </div>

      <table>
        <thead>
          <tr>
            <th>Student</th>
            <th>CA Score (40)</th>
            <th>Exam Score (60)</th>
            <th>Total (100)</th>
          </tr>
        </thead>
        <tbody>
          {students.map((s) => {
            const entry = scoresMap[s.id] || { ca: "", exam: "" };
            const caNum = parseFloat(entry.ca) || 0;
            const examNum = parseFloat(entry.exam) || 0;
            const hasScore = entry.ca !== "" || entry.exam !== "";
            const total = hasScore ? caNum + examNum : null;

            return (
              <tr key={s.id}>
                <td>
                  <strong>{s.data.first_name} {s.data.last_name}</strong>
                  <div className="muted">{s.id}</div>
                </td>
                <td>
                  <input
                    type="number"
                    min="0"
                    max="40"
                    step="0.5"
                    style={{ width: 80 }}
                    value={entry.ca}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScoresMap((prev) => ({
                        ...prev,
                        [s.id]: { ...prev[s.id], ca: val },
                      }));
                    }}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min="0"
                    max="60"
                    step="0.5"
                    style={{ width: 80 }}
                    value={entry.exam}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScoresMap((prev) => ({
                        ...prev,
                        [s.id]: { ...prev[s.id], exam: val },
                      }));
                    }}
                  />
                </td>
                <td>
                  <strong>{total !== null ? total : "—"}</strong>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div style={{ marginTop: 20 }}>
        <button className="btn" disabled={saving || students.length === 0} onClick={save}>
          {saving ? "Saving…" : "Save Scores"}
        </button>
      </div>
    </section>
  );
}

function BroadsheetView() {
  const navigate = useNavigate();
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [selectedClass, setSelectedClass] = useState("");
  const [selectedTerm, setSelectedTerm] = useState("2025/2026-Term1");
  const [broadsheet, setBroadsheet] = useState<Broadsheet | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.classes().then((c) => {
      setClasses(c);
      if (c.length > 0 && !selectedClass) setSelectedClass(c[0].id);
    });
  }, []);

  async function loadBroadsheet() {
    if (!selectedClass) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.broadsheet(selectedClass, selectedTerm);
      setBroadsheet(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load broadsheet.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (selectedClass) loadBroadsheet();
  }, [selectedClass, selectedTerm]);

  return (
    <section className="page" style={{ maxWidth: 1400 }}>
      <div className="page-head">
        <div>
          <h1>Class Broadsheet</h1>
          <p className="muted">Master ranking matrix with deterministic calculations for totals, averages, positions, and grades.</p>
        </div>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      <div className="toolbar">
        <select value={selectedClass} onChange={(e) => setSelectedClass(e.target.value)}>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input value={selectedTerm} onChange={(e) => setSelectedTerm(e.target.value)} />
        <button className="btn ghost" onClick={loadBroadsheet}>
          Refresh
        </button>
        <button className="btn" onClick={() => window.print()}>
          Print Broadsheet
        </button>
      </div>

      {broadsheet ? (
        <>
          <div className="panel" style={{ marginBottom: 16 }}>
            <h2>{broadsheet.class_name} · {broadsheet.term}</h2>
            <p>
              Class Average: <strong>{broadsheet.class_average}%</strong> · Total Students: <strong>{broadsheet.total_students}</strong>
            </p>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Student</th>
                  {broadsheet.subjects.map((s) => (
                    <th key={s.id} title={s.name}>
                      {s.code}
                    </th>
                  ))}
                  <th>Total</th>
                  <th>Average</th>
                  <th>Report</th>
                </tr>
              </thead>
              <tbody>
                {broadsheet.rows.map((row) => (
                  <tr key={row.student_id}>
                    <td>
                      <strong>{row.position}</strong>
                    </td>
                    <td>
                      <strong>{row.name}</strong>
                      <div className="muted">{row.student_id}</div>
                    </td>
                    {broadsheet.subjects.map((s) => {
                      const entry = row.subjects[s.id];
                      return (
                        <td key={s.id}>
                          {entry ? (
                            <div>
                              <span>{entry.total_score}</span> <small className="muted">({entry.grade})</small>
                            </div>
                          ) : (
                            <span className="muted">—</span>
                          )}
                        </td>
                      );
                    })}
                    <td>
                      <strong>{row.total_marks}</strong>
                    </td>
                    <td>
                      <strong>{row.average_score}%</strong>
                    </td>
                    <td>
                      <button
                        className="btn ghost"
                        onClick={() => navigate(`/reports/${encodeURIComponent(row.student_id)}?term=${encodeURIComponent(selectedTerm)}`)}
                      >
                        Report Card
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : loading ? (
        <p>Loading broadsheet…</p>
      ) : null}
    </section>
  );
}

function ReportCardView() {
  const { studentId = "" } = useParams();
  const searchParams = new URLSearchParams(window.location.search);
  const term = searchParams.get("term") || "2025/2026-Term1";
  const decoded = decodeURIComponent(studentId);
  const [report, setReport] = useState<StudentReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .studentReport(decoded, term)
      .then(setReport)
      .catch((err) => setError(err.message));
  }, [decoded, term]);

  if (error) return <section className="page"><div className="banner">{error}</div></section>;
  if (!report) return <section className="page">Generating student report card…</section>;

  return (
    <section className="page" style={{ maxWidth: 900 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
        <button className="btn ghost" onClick={() => window.history.back()}>
          Back
        </button>
        <button className="btn" onClick={() => window.print()}>
          Print Report Card (PDF)
        </button>
      </div>

      <div className="panel" style={{ background: "#fff", padding: 36, boxShadow: "var(--shadow)" }}>
        <div style={{ textAlign: "center", borderBottom: "2px solid #1b1712", paddingBottom: 16, marginBottom: 24 }}>
          <h1 style={{ fontSize: "1.8rem", margin: 0 }}>{report.school_name.toUpperCase()}</h1>
          <p style={{ margin: "4px 0" }}>TERMLY ACADEMIC PROGRESS REPORT</p>
          <small className="muted">{report.class.academic_year} · {report.class.term}</small>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginBottom: 24, fontSize: "0.95rem" }}>
          <div><strong>Student Name:</strong> {report.student.name}</div>
          <div><strong>Admission No:</strong> {report.student.admission_number || report.student.id}</div>
          <div><strong>Class:</strong> {report.class.name}</div>
          <div><strong>Total Students in Class:</strong> {report.class.total_students}</div>
          <div><strong>Position in Class:</strong> <span style={{ fontSize: "1.1rem", fontWeight: 700 }}>{report.performance.position}</span></div>
          <div><strong>Overall Average:</strong> {report.performance.average_score}%</div>
        </div>

        <h3>Academic Performance</h3>
        <table style={{ marginBottom: 24 }}>
          <thead>
            <tr>
              <th>Subject</th>
              <th>CA (40)</th>
              <th>Exam (60)</th>
              <th>Total</th>
              <th>Grade</th>
              <th>Rank</th>
              <th>Remark</th>
            </tr>
          </thead>
          <tbody>
            {report.performance.subjects.map((sub) => (
              <tr key={sub.subject_id}>
                <td>{sub.subject_name}</td>
                <td>{sub.ca_score ?? "—"}</td>
                <td>{sub.exam_score ?? "—"}</td>
                <td><strong>{sub.total_score ?? "—"}</strong></td>
                <td><strong>{sub.grade}</strong></td>
                <td>{sub.position}</td>
                <td>{sub.remark}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h3>Attendance & Conduct</h3>
        <p>
          Total School Days: <strong>{report.attendance.total_days}</strong> · Days Present: <strong>{report.attendance.present}</strong> · Attendance Rate: <strong>{report.attendance.percentage}%</strong>
        </p>

        <div style={{ borderTop: "1px solid var(--rule)", paddingTop: 16, marginTop: 24, display: "grid", gap: 14 }}>
          <div>
            <strong>Class Teacher's Remark:</strong>
            <p style={{ margin: "4px 0", fontStyle: "italic" }}>"{report.comments.teacher_comment}"</p>
          </div>
          <div>
            <strong>Principal's Remark:</strong>
            <p style={{ margin: "4px 0", fontStyle: "italic" }}>"{report.comments.principal_comment}"</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function ApprovalsView() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    try {
      const [app, conf] = await Promise.all([api.approvals(), api.conflicts()]);
      setApprovals(app);
      setConflicts(conf);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fetch items.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleApprove(id: string) {
    try {
      await api.approve(id);
      setMessage("Request approved.");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve.");
    }
  }

  async function handleReject(id: string) {
    try {
      await api.reject(id, "Rejected by administrator.");
      setMessage("Request rejected.");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject.");
    }
  }

  async function handleResolve(id: string, choice: string) {
    try {
      await api.resolveConflict(id, choice);
      setMessage("Conflict resolved.");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve conflict.");
    }
  }

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Approvals & Conflicts</h1>
          <p className="muted">Review sensitive operations requiring administrative approval and resolve concurrent edit conflicts.</p>
        </div>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      {message ? <div className="banner" style={{ background: "#dcfce7", color: "#166534" }}>{message}</div> : null}

      <h2>Pending Approvals</h2>
      {approvals.filter((a) => a.status === "PENDING_APPROVAL").length === 0 ? (
        <p className="muted">No pending approvals at this time.</p>
      ) : null}
      <table>
        <thead>
          <tr>
            <th>Event / Operation</th>
            <th>Requested By</th>
            <th>Student</th>
            <th>Details</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {approvals
            .filter((a) => a.status === "PENDING_APPROVAL")
            .map((app) => (
              <tr key={app.id}>
                <td>{app.event?.operation || "—"}</td>
                <td>{app.requested_by}</td>
                <td>{app.event?.student_id || "—"}</td>
                <td>
                  <pre className="json" style={{ maxHeight: 80 }}>{JSON.stringify(app.event?.payload, null, 2)}</pre>
                </td>
                <td>
                  <button className="btn" style={{ marginRight: 8 }} onClick={() => handleApprove(app.id)}>
                    Approve
                  </button>
                  <button className="btn danger" onClick={() => handleReject(app.id)}>
                    Reject
                  </button>
                </td>
              </tr>
            ))}
        </tbody>
      </table>

      <h2 style={{ marginTop: 40 }}>Concurrent Edit Conflicts</h2>
      {conflicts.length === 0 ? <p className="muted">No unresolved conflicts.</p> : null}
      <table>
        <thead>
          <tr>
            <th>Operation</th>
            <th>Student</th>
            <th>Current Value</th>
            <th>Incoming Value</th>
            <th>Resolution</th>
          </tr>
        </thead>
        <tbody>
          {conflicts.map((conf) => (
            <tr key={conf.id}>
              <td>{conf.operation}</td>
              <td>{conf.student_id}</td>
              <td>
                <pre className="json" style={{ maxHeight: 100 }}>{JSON.stringify(conf.current_state, null, 2)}</pre>
              </td>
              <td>
                <pre className="json" style={{ maxHeight: 100 }}>{JSON.stringify(conf.incoming_payload, null, 2)}</pre>
                <small className="muted">By {conf.incoming_teacher_id} via {conf.incoming_device_id}</small>
              </td>
              <td>
                <button className="btn ghost" style={{ marginRight: 8, marginBottom: 4 }} onClick={() => handleResolve(conf.id, "keep_current")}>
                  Keep Current
                </button>
                <button className="btn" onClick={() => handleResolve(conf.id, "use_incoming")}>
                  Use Incoming
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function AuditView() {
  const [logs, setLogs] = useState<AuditItem[]>([]);
  const [backups, setBackups] = useState<{ filename: string; size_bytes: number; created_at: string }[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [backingUp, setBackingUp] = useState(false);

  async function refresh() {
    try {
      const [l, b] = await Promise.all([api.audit(100), api.backups()]);
      setLogs(l);
      setBackups(b);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit or backup data.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleBackup() {
    setBackingUp(true);
    setError("");
    setNotice("");
    try {
      const res = await api.triggerBackup();
      setNotice(`Backup ${res.filename} created successfully (${Math.round(res.size_bytes / 1024)} KB).`);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backup failed.");
    } finally {
      setBackingUp(false);
    }
  }

  async function handleRestore(filename: string) {
    if (!window.confirm(`Are you sure you want to restore from ${filename}? Existing records will be overwritten.`)) {
      return;
    }
    setError("");
    setNotice("");
    try {
      const res = await api.restoreBackup(filename);
      setNotice(res.message);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Restore failed.");
    }
  }

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Audit & System Desk</h1>
          <p className="muted">Permanent cryptographic ledger of all mutations, device syncs, and administrative actions.</p>
        </div>
      </div>
      {error ? <div className="banner">{error}</div> : null}
      {notice ? <div className="banner" style={{ background: "#dcfce7", color: "#166534" }}>{notice}</div> : null}

      <div className="panel" style={{ marginBottom: 28 }}>
        <h2>Database Backups & Recovery</h2>
        <p className="muted">Create self-contained, signed system archives including database records and cryptographic keys.</p>
        <button className="btn" disabled={backingUp} onClick={handleBackup}>
          {backingUp ? "Creating backup…" : "Create Full System Backup Now"}
        </button>

        {backups.length > 0 ? (
          <div style={{ marginTop: 20 }}>
            <table>
              <thead>
                <tr>
                  <th>Backup File</th>
                  <th>Size</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {backups.map((b) => (
                  <tr key={b.filename}>
                    <td>
                      <strong>{b.filename}</strong>
                    </td>
                    <td>{Math.round(b.size_bytes / 1024)} KB</td>
                    <td>{new Date(b.created_at).toLocaleString()}</td>
                    <td>
                      <a
                        href={`/api/v1/system/backups/${encodeURIComponent(b.filename)}/download`}
                        className="btn ghost"
                        style={{ marginRight: 8, textDecoration: "none" }}
                        download
                      >
                        Download
                      </a>
                      <button className="btn danger" onClick={() => handleRestore(b.filename)}>
                        Restore
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <h2>Cryptographic Event Log</h2>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Operation</th>
            <th>User</th>
            <th>Entity</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td style={{ whiteSpace: "nowrap" }}>{log.timestamp ? new Date(log.timestamp).toLocaleString() : "—"}</td>
              <td>
                <strong>{log.operation}</strong>
              </td>
              <td>{log.user_id}</td>
              <td>
                {log.entity_type}: {log.entity_id}
              </td>
              <td>
                <pre className="json" style={{ maxHeight: 80, margin: 0 }}>{JSON.stringify(log.details, null, 2)}</pre>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function App() {
  const session = useSession();
  const signedIn = useMemo(() => Boolean(session.teacher), [session.teacher]);
  if (!session.ready) return null;
  if (!signedIn) {
    return (
      <Gate
        onAuthed={(teacher) => {
          session.setTeacher(teacher);
        }}
      />
    );
  }
  return (
    <Shell
      teacher={session.teacher!}
      onSignOut={() => {
        setToken(null);
        session.setTeacher(null);
      }}
    />
  );
}
