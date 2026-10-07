# BharatLearn

**Learn Today. Build India's Tomorrow.**

BharatLearn is an original India-focused learning platform built as a React + Vite client, Python FastAPI REST API, and PostgreSQL database. It includes a course marketplace, student learning space, protected lessons, course quizzes, independent timed tests, simulated checkout, certificates, and an admin studio.

## Project structure

```text
client/                  React + Vite browser app
server/app/              FastAPI routes, authentication and PostgreSQL access
server/src/db/schema.sql PostgreSQL schema
server/requirements.txt  Python dependencies
server/run.py            Local API runner
server/seed.py           Demo data seeder
```

## Technologies

- **Client:** React 18, Vite, React Router, Lucide React, Recharts, responsive CSS.
- **API:** Python 3.11+, FastAPI, Uvicorn, psycopg 3, bcrypt and JWT bearer sessions.
- **Data:** PostgreSQL using `psycopg`; Neon or Supabase work through their connection strings.
- **Authentication:** bcrypt password hashes and seven-day JWT bearer sessions.
- **Certificates:** Print-to-PDF in the browser with public verification codes.
- **Payments:** Simulated INR checkout only. It does not collect card details or move money.

## Requirements

- Python 3.11 or newer.
- Node.js 20 or newer and npm for the React client.
- A PostgreSQL database. For local work use PostgreSQL, or create a Supabase project.

## Local setup

From the `bharatlearn` directory:

```bash
npm install
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r server/requirements.txt
```

Copy `.env.example` to `.env`, then set `DATABASE_URL` and a long random `JWT_SECRET`. `CLIENT_ORIGIN` and `VITE_API_URL` have local defaults.

Initialize the schema and demo data:

```bash
npm run seed
```

Start the API and client together:

```bash
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). The API health route is `http://localhost:4000/api/health`.

You can also run them separately:

```bash
npm run dev:server
npm run dev:client
```

## PostgreSQL setup

1. Create a PostgreSQL database (Neon or Supabase both work).
2. Copy its PostgreSQL connection string. For Neon, use the pooled connection string and keep `sslmode=require` in the query parameters.
3. Put the string in `DATABASE_URL` in `.env`, replacing any password placeholder. Keep the database password private.
4. Run `npm run seed`. The script creates the schema and inserts demo content. It is safe to re-run for the included seed records; do not use it as a production migration tool.

This API connects to PostgreSQL directly with the server-side database credential. `SUPABASE_URL` and `SUPABASE_ANON_KEY` are optional reference values; this implementation does not expose or use the service-role key.

## Environment variables

| Variable | Used by | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | API/seed | PostgreSQL connection string |
| `JWT_SECRET` | API | Sign and verify session tokens; use a long random value |
| `NODE_ENV` | API | Set `development` locally and `production` on the deployed service |
| `PORT` | API | Local HTTP port; defaults to `4000` |
| `CLIENT_ORIGIN` | API | Allowed frontend origin(s), comma-separated |
| `VITE_API_URL` | Client | API origin without `/api`; defaults to `http://localhost:4000` |
| `SEED_ADMIN_EMAIL` | Seed | Development admin email |
| `SEED_ADMIN_PASSWORD` | Seed | Development admin password |
| `SEED_DEMO_USERS` | Seed | Set to `false` to skip predictable demo student accounts; defaults to `true` locally |
| `SUPABASE_URL` | Optional | Supabase project URL for future integrations |
| `SUPABASE_ANON_KEY` | Optional | Public Supabase key; not needed for this API |

Never commit `.env` or use a database service-role key in the browser.

## Seed accounts and content

The seed creates 18 categories, 10 instructors, 20 courses with lessons and module quizzes, 10 independent practice tests with 120 questions, sample enrollments, one approved review, and notifications. With the default local setting `SEED_DEMO_USERS=true`, it also creates 10 demo student accounts. Keep this disabled on public deployments.

- **Local demo student (when enabled):** `student1@bharatlearn.in` / `Student123!`
- **Local demo admin defaults:** `admin@bharatlearn.in` / `ChangeMe123!`

Set `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` before running the seed to use your own admin credentials. The checked-in `.env.example` values are for local development only; never use them on a public deployment. Use a new database for the first public seed, because disabling demo users does not remove demo accounts that already exist.

## Main student flows

1. Browse and filter courses; create an account or sign in.
2. Enrol through demo checkout. Successful/declined demo payments are recorded; no money is charged.
3. Open a protected lesson, save course progress, take module quizzes, and join course discussions.
4. Choose an independent test. Its question order is selected on the server; answers save to the server, and the server enforces the expiry and evaluates the score.
5. Review the score, question explanations and test history. Complete 80% of an enrolled course and pass an independent test to request its certificate.
6. Print a certificate to PDF or verify it with its code at `/verify`.

## API reference

All routes are under `/api`. Protected routes use `Authorization: Bearer <token>`. Admin routes additionally require the `admin` role.

| Area | Routes |
| --- | --- |
| Health & discovery | `GET /health`, `GET /stats`, `GET /categories`, `GET /courses`, `GET /courses/:id`, `GET /search?q=`, `GET /instructors` |
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `PUT /auth/profile`, `POST /auth/forgot-password`, `POST /auth/reset-password` |
| Student space | `GET /me/dashboard`, `GET /me/learning`, `GET /me/test-history`, `GET /me/wishlist`, `POST /me/wishlist`, `DELETE /me/wishlist/:courseId`, `GET /me/notifications`, `POST /me/notifications/:id/read`, `GET /me/certificates`, `GET /me/payments` |
| Enrolment & course learning | `POST /courses/:id/enroll`, `GET /courses/:id/lessons/:lessonId`, `POST /courses/:id/lessons/:lessonId/complete`, `GET/POST /courses/:id/discussions`, `GET /quizzes/:quizId`, `POST /quizzes/:quizId/submit`, `POST /courses/:id/reviews` |
| Independent tests | `GET /tests`, `GET /tests/:id`, `POST /tests/:id/start`, `PUT /tests/attempts/:attemptId/answers`, `POST /tests/:id/submit`, `GET /tests/attempts/:attemptId/result`, `GET /tests/:id/leaderboard` |
| Certificates & contact | `POST /certificates/issue`, `GET /certificates/verify/:code`, `POST /contact` |
| Admin | `GET /admin/overview`, `GET /admin/students`, `GET /admin/courses`, `POST/PUT/DELETE /admin/courses`, course curriculum module/lesson routes under `/admin/courses`, `/admin/modules`, and `/admin/lessons`, test and question management under `/admin/tests` and `/admin/questions`, plus `/admin/categories`, `/admin/reviews`, `/admin/payments`, and `/admin/certificates` |

The authoritative test score is calculated from saved answers on the API. The client never receives correct answers before submission. Attempt submission is locked after grading.

## Manual verification guide

No automated test suite is included in this first build. To check the connected flows locally:

1. Start PostgreSQL, run `npm run seed`, then run `npm run dev`.
2. Open the home page and search/filter the seeded course catalogue.
3. Sign in with the demo student account; enrol in a course with demo success and confirm it appears in **My learning**.
4. Open a lesson, mark it complete, refresh, and confirm the progress remains saved. Submit a module quiz and review feedback.
5. Start a practice test, select answers, refresh once to resume, and submit. Confirm the result and history are available.
6. Try demo failure checkout, a test timeout, a second attempt, and the certificate eligibility message.
7. Sign in as the admin and review the overview, course publishing, test question bank, learner list, and review moderation.
8. Submit a contact message, update a profile, use the development reset token, and verify a certificate code.

## GitHub and deployments

### GitHub

Create your own repository, add the `bharatlearn` directory, and push it to your account. Keep `.env` out of version control. If the workspace is a monorepo, deploy from the `bharatlearn/client` and `bharatlearn/server` app directories independently.

### Neon PostgreSQL database

1. Create a Neon project and database, then copy the pooled connection string from the Neon dashboard.
2. Keep the full connection string private. It will be entered as `DATABASE_URL` in the Render service, not in Vercel or the browser.
3. The API connects with psycopg over TLS; the Neon connection string should include `sslmode=require`.

### Vercel frontend

1. Import your repository as a Vercel project.
2. Set the project **Root Directory** to `client`.
3. Use `npm run build` as the build command and `dist` as the output directory.
4. After the API is deployed, add `VITE_API_URL` with the Render service origin only, for example `https://bharatlearn-api.onrender.com` (no trailing `/api`), then redeploy the Vercel frontend.
5. The included `client/vercel.json` sends client-side routes back to the SPA entry.

### Python backend

1. In Render, create a Blueprint from this repository and apply the root `render.yaml`. It defines the Python web service, health check and required environment variables.
2. Set the prompted `DATABASE_URL` to the Neon pooled connection string, `CLIENT_ORIGIN` to the exact Vercel production origin (for example `https://bharatlearn.vercel.app`), and `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` to credentials you control. Render generates `JWT_SECRET`.
3. Once the Render service is live, copy its `https://...onrender.com` origin into Vercel's `VITE_API_URL` and redeploy the frontend.
4. Run the one-time initial seed from the Render service Shell with `python seed.py`. The Blueprint disables predictable demo student accounts; the seed still creates an admin using the configured seed-admin credentials. Seed only a new database, and do not use this script as a production migration tool.
5. Confirm the backend responds at `https://<your-render-service>.onrender.com/api/health`, then open the Vercel site and test registration/login and the catalog.

The included Render Blueprint uses the free plan, which may sleep or have resource limits. Review current host limitations before relying on a free instance for real learners.

## Production checklist

- Replace demo user passwords; set new secrets and database credentials in the host secret manager.
- Restrict CORS to the deployed site and enable TLS for API/database connections.
- Configure an email provider before promising password reset delivery; development mode exposes a one-time reset token for local use only.
- Replace simulated checkout with a payment provider and signed server-side webhooks before accepting payments.
- Add schema migrations and a backup/restore plan; do not use the seed script to update production data.
- Review course rights, accessibility, privacy/retention policies, Indian tax/payment requirements, and certificate criteria before launch.
- Add monitoring, audit logs, moderation workflows, pagination, and abuse controls appropriate to traffic.
- Replace sample lesson video URLs and connect real course media. Confirm every certificate criterion against the intended course policy.
- Generate a sitemap for the final production domain and set canonical URLs and social preview images.

## Next upgrades

- Add instructor/admin editing for lesson resources, thumbnails, video uploads and quiz explanations.
- Add richer test question types, exam scheduling, random option order, accommodations and deeper topic analytics.
- Add email delivery for password resets and notifications.
- Add payment gateway integration, receipts, refunds and subscription management.
- Add server-side notes sync, richer discussion moderation and learner-to-instructor replies.
- Add course recommendations based on learner goals and consented activity.

## Deployment references

- [Vercel monorepo deployments](https://vercel.com/docs/monorepos)
- [Neon connection strings](https://neon.tech/docs/connect/connect-from-any-app)
- [Supabase PostgreSQL connection options](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Render FastAPI deployment guide](https://render.com/docs/deploy-fastapi)
- [Render free service limitations](https://render.com/docs/free)
