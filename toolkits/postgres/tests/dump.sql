DROP TABLE IF EXISTS "public"."messages";
-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.
-- Sequence and defined type
CREATE SEQUENCE IF NOT EXISTS messages_id_seq;
-- Table Definition
CREATE TABLE "public"."messages" (
    "id" int4 NOT NULL DEFAULT nextval('messages_id_seq'::regclass),
    "body" text NOT NULL,
    "user_id" int4 NOT NULL,
    "created_at" timestamp NOT NULL DEFAULT now(),
    "updated_at" timestamp NOT NULL DEFAULT now(),
    PRIMARY KEY ("id")
);
DROP TABLE IF EXISTS "public"."users";
-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.
-- Sequence and defined type
CREATE SEQUENCE IF NOT EXISTS users_id_seq;
-- Table Definition
CREATE TABLE "public"."users" (
    "id" int4 NOT NULL DEFAULT nextval('users_id_seq'::regclass),
    "name" varchar(256) NOT NULL,
    "email" text NOT NULL,
    "password_hash" text NOT NULL,
    "created_at" timestamp NOT NULL DEFAULT now(),
    "updated_at" timestamp NOT NULL DEFAULT now(),
    "status" varchar,
    PRIMARY KEY ("id")
);
INSERT INTO "public"."messages" (
        "id",
        "body",
        "user_id",
        "created_at",
        "updated_at"
    )
VALUES (
        1,
        'Evan says hello',
        3,
        '2025-04-10 17:21:05.504468',
        '2025-04-10 17:21:05.504468'
    ),
    (
        5100,
        'Hello! The current time is 2025-01-13T14:38:39.204Z',
        12,
        '2025-01-13 06:38:39.210897',
        '2025-01-13 06:38:39.210897'
    ),
    (
        5101,
        'Hello! The current time is 2025-01-13T14:55:32.560Z',
        12,
        '2025-01-13 06:55:32.56934',
        '2025-01-13 06:55:32.56934'
    ),
    (
        5102,
        'Hello! The current time is 2025-01-13T15:00:37.250Z',
        12,
        '2025-01-13 07:00:37.261816',
        '2025-01-13 07:00:37.261816'
    ),
    (
        5319,
        'Hello! The current time is 2025-01-14T07:17:07.115Z',
        12,
        '2025-01-13 23:17:07.123393',
        '2025-01-13 23:17:07.123393'
    );
INSERT INTO "public"."users" (
        "id",
        "name",
        "email",
        "password_hash",
        "created_at",
        "updated_at",
        "status"
    )
VALUES (
        1,
        'Mario',
        'mario@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$tMg1Rd3IEDnp3iFKrqsF4Dsbw6/Cbf6seRB/H5bhaPg$zZj5yn4x3D3O3mDHcW2aczQNiYfAs3cw21XMEIgkF0E',
        '2024-09-01 20:49:38.759432',
        '2024-09-02 03:49:39.927',
        'active'
    ),
    (
        3,
        'Evan',
        'evantahler@gmail.com',
        '$argon2id$v=19$m=65536,t=2,p=1$CvOMK1WUd99R7kYXpiBPNYw4OQP53pYIgeMnwz92mrE$HPthId4phMoPT1TWuCRHHCr9BSQA8XoUkQuB1HZsqTY',
        '2024-09-02 17:49:23.377425',
        '2024-09-02 17:49:23.377425',
        'active'
    ),
    (
        12,
        'Admin',
        'admin@arcade.dev',
        '$argon2id$v=19$m=65536,t=2,p=1$paCAAD1HVZkncP/WvecuUO6zFXp2/8BISpgr5rXRxps$M5kBFc9JHHGNw9SXnPu2ggpJY0mFFCska7TXMrllndo',
        '2024-10-13 15:01:30.792909',
        '2024-10-13 15:01:30.792909',
        'inactive'
    );
ALTER TABLE "public"."messages"
ADD FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");
-- set pk to 13
ALTER SEQUENCE users_id_seq RESTART WITH 13;
-- Indices
CREATE UNIQUE INDEX name_idx ON public.users USING btree (name);
CREATE UNIQUE INDEX email_idx ON public.users USING btree (email);
CREATE UNIQUE INDEX users_email_unique ON public.users USING btree (email);
