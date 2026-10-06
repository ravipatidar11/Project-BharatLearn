CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
  phone TEXT, password_hash TEXT NOT NULL, city TEXT, college TEXT, education TEXT,
  skills TEXT[] NOT NULL DEFAULT '{}', avatar_url TEXT, role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student','admin')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS categories (
  id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, slug TEXT UNIQUE NOT NULL, icon TEXT NOT NULL DEFAULT 'Code2'
);
CREATE TABLE IF NOT EXISTS instructors (
  id SERIAL PRIMARY KEY, full_name TEXT NOT NULL, title TEXT, city TEXT, bio TEXT, avatar_url TEXT,
  rating NUMERIC(2,1) NOT NULL DEFAULT 4.8
);
CREATE TABLE IF NOT EXISTS courses (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, subtitle TEXT, description TEXT NOT NULL DEFAULT '', category_id INT REFERENCES categories(id),
  instructor_id INT REFERENCES instructors(id), level TEXT NOT NULL DEFAULT 'Beginner', language TEXT NOT NULL DEFAULT 'English',
  duration_hours INT NOT NULL DEFAULT 8, price_inr INT NOT NULL DEFAULT 0, original_price_inr INT NOT NULL DEFAULT 0,
  thumbnail_url TEXT, accent TEXT NOT NULL DEFAULT 'orange', is_published BOOLEAN NOT NULL DEFAULT true,
  featured BOOLEAN NOT NULL DEFAULT false, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS course_modules (
  id SERIAL PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE, title TEXT NOT NULL, position INT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS lessons (
  id SERIAL PRIMARY KEY, module_id INT NOT NULL REFERENCES course_modules(id) ON DELETE CASCADE, title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '', video_url TEXT, duration_minutes INT NOT NULL DEFAULT 10, position INT NOT NULL DEFAULT 0,
  resources JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE TABLE IF NOT EXISTS course_quizzes (
  id SERIAL PRIMARY KEY, module_id INT NOT NULL REFERENCES course_modules(id) ON DELETE CASCADE, title TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quiz_questions (
  id SERIAL PRIMARY KEY, quiz_id INT NOT NULL REFERENCES course_quizzes(id) ON DELETE CASCADE, prompt TEXT NOT NULL,
  options JSONB NOT NULL, correct_index INT NOT NULL, explanation TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS enrollments (
  id SERIAL PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(), progress_percent INT NOT NULL DEFAULT 0,
  UNIQUE(user_id, course_id)
);
CREATE TABLE IF NOT EXISTS wishlists (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(user_id, course_id)
);
CREATE TABLE IF NOT EXISTS lesson_progress (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, lesson_id INT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
  completed_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(user_id, lesson_id)
);
CREATE TABLE IF NOT EXISTS quiz_attempts (
  id SERIAL PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, quiz_id INT NOT NULL REFERENCES course_quizzes(id) ON DELETE CASCADE,
  score INT NOT NULL DEFAULT 0, total INT NOT NULL DEFAULT 0, submitted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS tests (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', category TEXT NOT NULL,
  duration_minutes INT NOT NULL DEFAULT 30, total_marks NUMERIC(7,2) NOT NULL DEFAULT 30, passing_percent INT NOT NULL DEFAULT 40,
  correct_marks NUMERIC(5,2) NOT NULL DEFAULT 1, wrong_marks NUMERIC(5,2) NOT NULL DEFAULT 0, max_attempts INT NOT NULL DEFAULT 2,
  starts_at TIMESTAMPTZ, ends_at TIMESTAMPTZ, is_published BOOLEAN NOT NULL DEFAULT true,
  leaderboard_enabled BOOLEAN NOT NULL DEFAULT false, question_count INT NOT NULL DEFAULT 12, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS test_questions (
  id SERIAL PRIMARY KEY, test_id TEXT NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
  topic TEXT NOT NULL DEFAULT 'Core concepts', prompt TEXT NOT NULL, options JSONB NOT NULL,
  correct_index INT NOT NULL, explanation TEXT NOT NULL DEFAULT '', position INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT true, seed_key TEXT
);
ALTER TABLE test_questions ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE test_questions ADD COLUMN IF NOT EXISTS seed_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_test_questions_seed_key ON test_questions(test_id,seed_key) WHERE seed_key IS NOT NULL;
CREATE TABLE IF NOT EXISTS test_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  test_id TEXT NOT NULL REFERENCES tests(id) ON DELETE CASCADE, question_ids INT[] NOT NULL, answers JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress','submitted','timed_out')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ NOT NULL,
  submitted_at TIMESTAMPTZ, score NUMERIC(7,2), correct_count INT, wrong_count INT, unanswered_count INT,
  percentage NUMERIC(5,2), passed BOOLEAN, time_taken_seconds INT
);
CREATE TABLE IF NOT EXISTS certificates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), certificate_code TEXT UNIQUE NOT NULL,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(user_id, course_id)
);
CREATE TABLE IF NOT EXISTS payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE, amount_inr INT NOT NULL,
  method TEXT NOT NULL CHECK (method IN ('demo_success','demo_fail','free')), status TEXT NOT NULL CHECK (status IN ('success','failed')),
  reference TEXT NOT NULL UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS reviews (
  id SERIAL PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5), body TEXT NOT NULL, is_approved BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(user_id, course_id)
);
CREATE TABLE IF NOT EXISTS notifications (
  id SERIAL PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, title TEXT NOT NULL, body TEXT NOT NULL,
  href TEXT, read_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS contact_messages (
  id SERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT, subject TEXT NOT NULL, message TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id SERIAL PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL, used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS discussion_posts (
  id SERIAL PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  lesson_id INT REFERENCES lessons(id) ON DELETE SET NULL, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body TEXT NOT NULL CHECK (char_length(body) <= 2000), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_courses_search ON courses USING gin (to_tsvector('english', title || ' ' || coalesce(subtitle,'')));
CREATE INDEX IF NOT EXISTS idx_enrollments_user ON enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user_date ON test_attempts(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_questions_test ON test_questions(test_id);
