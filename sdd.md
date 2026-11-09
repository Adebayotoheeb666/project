LOCAL-FIRST SCHOOL INTELLIGENCE SYSTEM (LSIA)

Complete Software Design and Implementation Specification

Project: Local-First School Intelligence System
Version: 1.0
Architecture: Offline-First, Local-Network, Event-Driven Architecture
Primary Platform: Windows/Linux School Computer and Android Phones

1. PROJECT OVERVIEW

Build a privacy-focused, offline-first school management system that operates primarily from a central computer within the school.

The system manages student records, academic scores, attendance, examination results, report cards, broadsheets, teacher permissions, and administrative operations.

The school computer serves as the central authority and permanent source of truth. Teachers use Android phones to perform their assigned activities, even without an internet connection. Changes made on their phones are stored locally and synchronized directly with the school computer whenever both devices are connected to the same local network.

The system must not depend on an internet connection for its core operations. Student information must remain under the school's control and must not be stored on external cloud infrastructure.

2. SYSTEM ARCHITECTURE

The system consists of two primary components.

2.1 Teacher Android Application

Each teacher's phone operates as an independent offline-first application.

Responsibilities:

- Display assigned classes and subjects.
- View student records.
- Register and update student information within assigned permissions.
- Record continuous assessment scores.
- Enter examination scores.
- Record attendance.
- Preview student academic records.
- Maintain a local database.
- Store pending changes until synchronization is possible.
- Synchronize changes directly with the school computer over the local network.
- Display synchronization status and outstanding conflicts.

Technology:

- Kotlin
- Jetpack Compose
- Room Database / SQLite
- Android Keystore
- WorkManager
- HTTPS for local-network communication

2.2 School Management Computer

The school computer is the central authority and permanent source of truth.

Responsibilities:

- Maintain the master student database.
- Manage teacher accounts and permissions.
- Receive and validate changes from teacher devices.
- Maintain a complete history of changes.
- Resolve conflicting modifications.
- Manage examination and assessment records.
- Generate report cards and broadsheets.
- Provide administrative dashboards.
- Manage approvals for sensitive operations.
- Register and revoke teacher devices.
- Maintain backups and restore system data.

Technology:

- Python
- FastAPI
- PostgreSQL
- Local document storage
- Electron
- React
- Ollama is not required.

The school application must operate as a locally hosted service accessible to authorized devices on the school's network.

3. ARCHITECTURAL LAYERS

Organize the application into the following layers:

Presentation Layer

- Android teacher application.
- School administration dashboard.

Application Layer

- Student management service.
- Academic records service.
- Attendance service.
- Synchronization manager.
- Report generation service.
- Approval management service.
- Notification service.

Domain Layer

- Student records.
- Teacher permissions.
- Academic assessment rules.
- Event management.
- Conflict resolution.
- Examination management.
- Approval policies.

Data and Infrastructure Layer

- SQLite on Android devices.
- PostgreSQL on the school computer.
- Local file storage.
- Device identity management.
- Encryption and authentication.
- Local-network communication.
- Backup and recovery.

4. CORE FUNCTIONAL REQUIREMENTS

F1: Offline-First Student Management

Teachers must be able to access and manage authorized student records without internet connectivity.

The application must support:

- Student registration.
- Student information updates.
- Class assignment.
- Subject assignment.
- Student record viewing.
- Student search.
- Academic history.

All changes must first be saved locally.

F2: Academic Records Management

Teachers must be able to:

- Enter continuous assessment scores.
- Enter examination scores.
- Update permitted academic records.
- View individual student performance.
- View class performance.
- Review previous assessment records.

The system must validate scores against configured maximum values and prevent unauthorized modifications.

F3: Attendance Management

Implement an attendance management module supporting:

- Daily attendance registration.
- Present, absent, late, and excused classifications.
- Class attendance summaries.
- Individual attendance history.
- Attendance percentage calculations.
- Attendance reports.

Attendance records must be stored locally and synchronized when the school computer becomes accessible.

F4: Direct Device Synchronization

Implement direct synchronization between Android devices and the school computer.

The school computer must expose a secure local-network API.

Synchronization workflow:

1. A teacher performs an operation on their phone.
2. The operation is saved in the local database.
3. The synchronization manager checks whether the school computer is reachable.
4. If unavailable, the operation remains in the pending queue.
5. When connectivity becomes available, the phone establishes an authenticated connection to the school computer.
6. Pending operations are transmitted in batches.
7. The school computer validates device identity, signatures, permissions, and submitted data.
8. Valid operations are applied to the central database.
9. The school computer returns synchronization receipts.
10. The phone updates its local records and synchronization status.

Synchronization requirements:

- Maximum 20 operations per batch.
- Maximum 500 KB per batch.
- Exponential retry intervals of 1, 5, and 30 minutes.
- Duplicate operation detection.
- Transactional processing.
- Operation acknowledgement.
- Recovery from interrupted synchronization.
- Clear synchronization status indicators.

The system must support synchronization over school Wi-Fi without requiring internet access.

F5: Event-Based Record Management

Every important modification must produce a permanent event.

Do not silently overwrite historical records.

Each event should contain:

{
  "id": "uuid",
  "student_id": "FUTA/SS2A/042",
  "type": "SCORE_UPDATE",
  "payload": {
    "subject": "MATH",
    "ca": 20,
    "exam": 55
  },
  "teacher_id": "teacher_ade",
  "device_id": "device_001",
  "timestamp": 1726850000000,
  "lamport_clock": 42,
  "signature": "base64_signature"
}

Maintain an event history that makes it possible to identify:

- Who performed an operation.
- Which device performed it.
- What information changed.
- When the change occurred.
- Whether the operation was approved.
- Whether the operation was successfully synchronized.

F6: Conflict Resolution

The system must detect concurrent modifications to the same record.

Implement:

- Operation identifiers.
- Lamport clocks.
- Record version tracking.
- Field-level conflict detection.
- Conflict history.
- Administrative conflict resolution.

When two teachers modify the same field concurrently, preserve both versions and flag the record for review.

Example:

"CONFLICT: Score 60 by Teacher A versus Score 75 by Teacher B."

The administrator must be able to inspect both changes and select the correct value.

Never silently discard conflicting academic records.

F7: Report Generation

Implement a report generation engine capable of producing:

- Individual student report cards.
- Class broadsheets.
- Subject performance reports.
- Attendance reports.
- Academic performance summaries.
- Student progress reports.
- Termly academic reports.

The report generation engine must use validated database records and configurable school templates.

Implement deterministic calculations for:

- Total scores.
- Average scores.
- Subject positions.
- Class positions.
- Grades.
- Attendance percentages.
- Performance classifications.

Provide configurable teacher comment templates based on academic performance, attendance, and other approved school metrics.

Allow administrators to preview, edit, approve, and export reports as PDF documents.

The system must generate 50 student reports within 15 minutes on a computer with an Intel Core i3 processor and 8 GB RAM.

F8: Administrative Approval Workflow

Certain operations must require administrative approval.

Examples include:

- Final examination score modifications.
- Student promotion.
- Permanent student deletion.
- Finalization of academic results.
- Major changes to academic records.

The system must support:

"PENDING_APPROVAL → APPROVED / REJECTED"

Maintain an approval history containing the requesting user, approving administrator, timestamps, and decision.

5. SECURITY ARCHITECTURE

5.1 Device Identity

Each teacher device must have a unique cryptographic identity.

Generate an Ed25519 keypair for each registered device.

Store private keys securely using Android Keystore.

Register the corresponding public key on the school computer.

Use device enrollment through a QR code containing the school identifier, school public key, and local connection information.

5.2 Authentication

Support:

- Teacher login.
- Administrator login.
- Device registration.
- PIN or biometric authentication where supported.
- Session management.
- Device revocation.

5.3 Authorization

Implement role-based access control.

Example permission structure:

{
  "teacher_id": "teacher_ade",
  "classes": ["SS1A", "SS2A"],
  "subjects": ["MATHEMATICS"],
  "permissions": {
    "view_students": true,
    "edit_students": true,
    "enter_ca": true,
    "enter_exam": true,
    "finalize_results": false
  }
}

All permissions must be enforced by the school computer, not merely by the Android application.

5.4 Data Protection

Implement:

- Encrypted local databases where appropriate.
- Secure communication over the local network.
- Signed operations.
- Device revocation.
- Duplicate operation detection.
- Protection against replay attacks.
- Secure authentication.
- Database access restrictions.
- Encrypted backups.
- Audit logging.

Student records must never be accessible to unauthorized teachers or devices.

5.5 Key Management

The school computer generates and securely stores its cryptographic keys.

During teacher enrollment:

1. The school administrator initiates device registration.
2. A QR enrollment code is generated.
3. The teacher scans the code.
4. The application establishes the school's identity.
5. The teacher device generates its cryptographic keypair.
6. The public key is registered with the school computer.
7. The administrator approves the enrollment.

Administrators must be able to revoke registered devices immediately.

6. DATABASE DESIGN

Implement the following core database tables:

teachers

- id
- name
- public_key
- role_json
- enrolled_at
- revoked

students

- id
- class_id
- data_json
- version
- updated_by
- created_at
- updated_at

events

- id
- student_id
- operation
- payload
- teacher_id
- device_id
- signature
- timestamp
- lamport_clock
- status

approvals

- id
- event_id
- requested_by
- approved_by
- status
- created_at
- updated_at

classes

- id
- name
- academic_year
- class_teacher_id

subjects

- id
- name
- code

attendance

- id
- student_id
- class_id
- date
- status
- recorded_by

scores

- id
- student_id
- subject_id
- term
- ca_score
- exam_score
- total_score
- recorded_by

devices

- id
- teacher_id
- public_key
- device_name
- enrolled_at
- last_sync_at
- status

audit_logs

- id
- user_id
- operation
- entity_type
- entity_id
- timestamp
- details

Additional tables should be introduced where necessary without duplicating responsibilities.

7. USER INTERFACE DESIGN

7.1 Android Application

Create a clean, responsive teacher application.

Primary screens:

- Login.
- Device enrollment.
- Dashboard.
- Assigned classes.
- Student directory.
- Student profile.
- Score entry.
- Attendance registration.
- Academic history.
- Report preview.
- Pending synchronization.
- Conflict notifications.
- Account settings.

Display synchronization states clearly:

- Offline.
- Connected.
- Syncing.
- Synced.
- Pending operations.
- Needs approval.
- Conflict detected.
- Synchronization failed.

7.2 School Administration Dashboard

Primary screens:

- Administrator login.
- Overview dashboard.
- Student management.
- Teacher management.
- Class management.
- Subject management.
- Academic records.
- Attendance management.
- Examination management.
- Report generation.
- Broadsheet management.
- Pending approvals.
- Conflict resolution.
- Device management.
- Audit logs.
- Backup and recovery.
- System settings.

The interface must be intuitive and suitable for daily administrative operations.

8. DEPLOYMENT ARCHITECTURE

8.1 School Computer

Provide a single installation package for Windows.

The installer should configure:

- PostgreSQL.
- Python application services.
- FastAPI backend.
- Desktop administration dashboard.
- Local document storage.
- Background services.
- Automatic startup.
- Backup scheduling.

The application must operate without requiring internet access after installation.

The backend should listen on a configurable local-network address and port.

8.2 Android Application

Provide an installable APK.

The first launch should guide teachers through:

- School enrollment.
- Device registration.
- Authentication.
- Local database initialization.
- Assigned class and subject synchronization.

8.3 Network Requirements

The school computer and teacher phones should communicate directly over the school's local Wi-Fi network.

The system must continue operating when:

- Internet access is unavailable.
- The school Wi-Fi temporarily disconnects.
- A teacher leaves the school's network.
- The school computer is temporarily unavailable.

Pending operations must remain safely stored until synchronization becomes possible.

9. OFFLINE OPERATION

Offline functionality is a core requirement, not an optional feature.

The system must support three device categories:

Tier 1: 8 GB RAM or higher

- Full application functionality.
- Local student database.
- Offline academic records.
- Attendance registration.
- Report previews.
- Synchronization.

Tier 2: 4–6 GB RAM

- Full CRUD functionality.
- Local student database.
- Attendance and score entry.
- Basic report previews.
- Synchronization.

Tier 3: 2–3 GB RAM

- Lightweight student directory.
- Basic record viewing.
- Limited data entry where device performance permits.
- Synchronization.

All devices must retain their pending changes when disconnected.

10. PERFORMANCE REQUIREMENTS

Target the following:

Operation| Target
Offline CRUD| <100 ms
Synchronization of 100 operations| <5 seconds under suitable local-network conditions
Generate 50 reports| <15 minutes on i3/8 GB
Event replay| 1,000 events in <2 seconds on i3
Local dashboard access| Responsive under normal school workloads

Performance must be measured on representative hardware.

11. DATA PRIVACY AND COMPLIANCE

The school retains ownership and control of all student information.

Implement appropriate safeguards aligned with the Nigeria Data Protection Act.

Requirements:

- No dependence on external cloud storage.
- No permanent external storage of student information.
- Restricted access to student records.
- Encrypted backups.
- Secure deletion procedures.
- Audit trails.
- Appropriate data retention policies.
- Controlled report distribution.

Provide administrators with tools to manage student record retention and deletion.

12. FAILURE RECOVERY

The application must handle the following situations:

School computer unavailable:
Teacher devices continue operating offline and retain pending changes.

Teacher phone lost:
Administrator revokes the registered device.

Network interruption:
Synchronization pauses and resumes automatically.

Duplicate operations:
The school computer identifies previously processed operation IDs and prevents duplicate application.

Conflicting modifications:
Both versions are preserved for administrative review.

Application crash:
Uncommitted operations remain recoverable.

Database failure:
Provide documented backup and restoration procedures.

Insufficient storage:
Notify the user before operations become impossible.

13. TESTING STRATEGY

Unit Testing

- Database operations.
- Authentication.
- Authorization.
- Cryptographic verification.
- Event creation.
- Conflict detection.
- Score calculations.
- Report generation.

Integration Testing

- Offline student registration.
- Offline score entry.
- Local-network synchronization.
- Interrupted synchronization.
- Duplicate operation handling.
- Approval workflow.
- Report generation.

Security Testing

- Unauthorized teacher access.
- Revoked device access.
- Invalid signatures.
- Replay attacks.
- Unauthorized score modifications.
- Database access restrictions.

Performance Testing

- Large student databases.
- Multiple teacher devices.
- High-volume event synchronization.
- Report generation.
- Database restoration.

14. IMPLEMENTATION PHASES

Phase 1: Core Foundation

- Project structure.
- Database architecture.
- Authentication.
- Teacher and administrator accounts.
- Student management.
- Class and subject management.

Phase 2: Offline-First Android Application

- Android application.
- SQLite database.
- Offline CRUD.
- Local operation queue.
- Device enrollment.

Phase 3: Local-Network Synchronization

- School computer API.
- Direct device communication.
- Signed operations.
- Synchronization receipts.
- Conflict detection.
- Retry mechanisms.

Phase 4: Academic Management

- Continuous assessment.
- Examination records.
- Attendance.
- Academic calculations.
- Student performance history.

Phase 5: Reporting and Administration

- Report cards.
- Broadsheets.
- PDF generation.
- Administrative approvals.
- Audit logs.
- Conflict resolution dashboard.

Phase 6: Deployment and Validation

- Windows installer.
- Android APK.
- Database backup and recovery.
- Security testing.
- Performance testing.
- Pilot deployment in a school.

15. DEVELOPMENT REQUIREMENTS

Before implementation:

1. Establish the complete project structure.
2. Define database schemas and relationships.
3. Define API contracts.
4. Define authentication and authorization.
5. Define synchronization protocols.
6. Define event structures.
7. Define error-handling conventions.
8. Establish testing infrastructure.

During implementation:

- Follow modular architecture.
- Separate presentation, application, domain, and infrastructure logic.
- Maintain consistent naming conventions.
- Use reusable components.
- Validate all incoming data.
- Implement proper error handling.
- Write tests alongside features.
- Document important architectural decisions.
- Avoid unnecessary dependencies.
- Never introduce external infrastructure that is not required by the specification.

Implement one phase at a time. Complete and test each phase before proceeding to the next.

Do not replace existing working functionality without first inspecting its dependencies and understanding its impact.

Do not use placeholder implementations for critical functionality.

16. DEFINITION OF DONE

The system is considered complete when:

- Teachers can manage authorized student records offline.
- Academic scores can be entered without internet connectivity.
- Attendance can be recorded offline.
- Teacher devices synchronize directly with the school computer.
- Synchronization survives network interruptions.
- Unauthorized operations are rejected.
- Conflicting changes are preserved and reviewable.
- Administrators can approve sensitive operations.
- Reports and broadsheets are generated correctly.
- Student records remain under school control.
- The application can be installed and operated without continuous internet access.
- Backup and recovery procedures have been tested.
- All critical functionality has automated or documented tests.
Final Product Principle:
Build a dependable, privacy-focused school management system that works independently of internet connectivity, keeps school data under institutional control, and allows teachers and administrators to manage academic operations reliably across their devices.