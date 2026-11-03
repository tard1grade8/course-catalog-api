TRUNCATE enrollments, students, courses RESTART IDENTITY;

INSERT INTO courses (id, title, description, credits, is_elective, likes, level) VALUES
('modern-frontend', 'Modern Frontend: React & Next.js', 'React 19, Server Components, and the App Router.', 5, false, 24, 'intermediate'),
('databases-postgresql', 'Relational Databases: PostgreSQL', 'Schemas, SQLAlchemy, and migrations with Alembic.', 5, false, 15, 'intermediate'),
('backend-fastapi', 'Backend with Python and FastAPI', 'REST APIs, Pydantic, and dependency injection.', 4, false, 21, 'intermediate'),
('api-design', 'API Design: REST vs GraphQL', 'Comparing REST and GraphQL in one hands-on project.', 4, true, 11, 'beginner'),
('ai-integration', 'AI/LLM Integration', 'LLM features in an app via the OpenAI API.', 5, true, 32, 'beginner'),
('web-security', 'Web Security Basics', 'Auth, tokens, OWASP, and safe coding practices.', 3, false, 19, 'intermediate');

INSERT INTO students (name, email) VALUES
('Aigerim Sadykova', 'aigerim@example.com'),
('Miras Ivanov', 'miras@example.com'),
('Dana Kassymova', 'dana@example.com');

INSERT INTO enrollments (course_id, student_id, enrolled_at) VALUES
('modern-frontend', 1, '2026-10-27 12:21:54.331755+05'),
('databases-postgresql', 1, '2026-10-27 12:21:54.331755+05'),
('backend-fastapi', 2, '2026-10-27 12:21:54.331755+05'),
('ai-integration', 3, '2026-10-27 12:21:54.331755+05'),
('modern-frontend', 3, '2026-10-27 12:21:54.331755+05'),
('ai-integration', 1, '2026-10-27 12:21:54.331755+05');