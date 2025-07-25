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
VALUES -- User 1 (Alice) - 3 messages
    (
        1,
        'Hello everyone!',
        1,
        '2025-01-10 10:00:00.000000',
        '2025-01-10 10:00:00.000000'
    ),
    (
        2,
        'How is everyone doing today?',
        1,
        '2025-01-10 11:30:00.000000',
        '2025-01-10 11:30:00.000000'
    ),
    (
        3,
        'Great to see you all here!',
        1,
        '2025-01-10 14:15:00.000000',
        '2025-01-10 14:15:00.000000'
    ),
    -- User 2 (Bob) - 2 messages
    (
        4,
        'Hi Alice! Doing well, thanks for asking.',
        2,
        '2025-01-10 11:35:00.000000',
        '2025-01-10 11:35:00.000000'
    ),
    (
        5,
        'Anyone up for a game later?',
        2,
        '2025-01-10 16:20:00.000000',
        '2025-01-10 16:20:00.000000'
    ),
    -- User 3 (Charlie) - 3 messages
    (
        6,
        'Count me in for the game!',
        3,
        '2025-01-10 16:25:00.000000',
        '2025-01-10 16:25:00.000000'
    ),
    (
        7,
        'What time works for everyone?',
        3,
        '2025-01-10 16:30:00.000000',
        '2025-01-10 16:30:00.000000'
    ),
    (
        8,
        'I can play around 8 PM',
        3,
        '2025-01-10 17:00:00.000000',
        '2025-01-10 17:00:00.000000'
    ),
    -- User 4 (Diana) - 2 messages
    (
        9,
        '8 PM works for me too!',
        4,
        '2025-01-10 17:05:00.000000',
        '2025-01-10 17:05:00.000000'
    ),
    (
        10,
        'What game should we play?',
        4,
        '2025-01-10 17:10:00.000000',
        '2025-01-10 17:10:00.000000'
    ),
    -- User 5 (Evan) - 3 messages
    (
        11,
        'I suggest we try the new arcade game!',
        5,
        '2025-01-10 17:15:00.000000',
        '2025-01-10 17:15:00.000000'
    ),
    (
        12,
        'It has great multiplayer features',
        5,
        '2025-01-10 17:20:00.000000',
        '2025-01-10 17:20:00.000000'
    ),
    (
        13,
        'Perfect timing for a weekend session',
        5,
        '2025-01-10 18:00:00.000000',
        '2025-01-10 18:00:00.000000'
    ),
    -- User 6 (Fiona) - 2 messages
    (
        14,
        'Sounds like fun! I love arcade games.',
        6,
        '2025-01-10 18:05:00.000000',
        '2025-01-10 18:05:00.000000'
    ),
    (
        15,
        'Should I bring snacks?',
        6,
        '2025-01-10 18:10:00.000000',
        '2025-01-10 18:10:00.000000'
    ),
    -- User 7 (George) - 3 messages
    (
        16,
        'Snacks are always welcome!',
        7,
        '2025-01-10 18:15:00.000000',
        '2025-01-10 18:15:00.000000'
    ),
    (
        17,
        'I can bring some drinks',
        7,
        '2025-01-10 18:20:00.000000',
        '2025-01-10 18:20:00.000000'
    ),
    (
        18,
        'This is going to be awesome',
        7,
        '2025-01-10 19:00:00.000000',
        '2025-01-10 19:00:00.000000'
    ),
    -- User 8 (Helen) - 2 messages
    (
        19,
        'I agree! Cannot wait for the game night.',
        8,
        '2025-01-10 19:05:00.000000',
        '2025-01-10 19:05:00.000000'
    ),
    (
        20,
        'Should we set up a Discord call?',
        8,
        '2025-01-10 19:10:00.000000',
        '2025-01-10 19:10:00.000000'
    ),
    -- User 9 (Ian) - 3 messages
    (
        21,
        'Discord would be perfect for voice chat',
        9,
        '2025-01-10 19:15:00.000000',
        '2025-01-10 19:15:00.000000'
    ),
    (
        22,
        'I will create a server for us',
        9,
        '2025-01-10 19:20:00.000000',
        '2025-01-10 19:20:00.000000'
    ),
    (
        23,
        'Link will be shared in a few minutes',
        9,
        '2025-01-10 19:25:00.000000',
        '2025-01-10 19:25:00.000000'
    ),
    -- User 10 (Julia) - 2 messages
    (
        24,
        'Thanks Ian! You are the best.',
        10,
        '2025-01-10 19:30:00.000000',
        '2025-01-10 19:30:00.000000'
    ),
    (
        25,
        'See you all at 8 PM!',
        10,
        '2025-01-10 19:35:00.000000',
        '2025-01-10 19:35:00.000000'
    ),
    -- Additional messages for Evan (user_id 5) - 10 more messages
    (
        26,
        'Just finished setting up the game server!',
        5,
        '2025-01-10 20:00:00.000000',
        '2025-01-10 20:00:00.000000'
    ),
    (
        27,
        'Everyone should be able to connect now',
        5,
        '2025-01-10 20:05:00.000000',
        '2025-01-10 20:05:00.000000'
    ),
    (
        28,
        'I added some custom maps too',
        5,
        '2025-01-10 20:10:00.000000',
        '2025-01-10 20:10:00.000000'
    ),
    (
        29,
        'The graphics look amazing on this new version',
        5,
        '2025-01-10 20:15:00.000000',
        '2025-01-10 20:15:00.000000'
    ),
    (
        30,
        'Hope you all enjoy the new features',
        5,
        '2025-01-10 20:20:00.000000',
        '2025-01-10 20:20:00.000000'
    ),
    (
        31,
        'I also set up a leaderboard system',
        5,
        '2025-01-10 20:25:00.000000',
        '2025-01-10 20:25:00.000000'
    ),
    (
        32,
        'We can track high scores now',
        5,
        '2025-01-10 20:30:00.000000',
        '2025-01-10 20:30:00.000000'
    ),
    (
        33,
        'The game supports up to 8 players simultaneously',
        5,
        '2025-01-10 20:35:00.000000',
        '2025-01-10 20:35:00.000000'
    ),
    (
        34,
        'I tested it earlier and it runs smoothly',
        5,
        '2025-01-10 20:40:00.000000',
        '2025-01-10 20:40:00.000000'
    ),
    (
        35,
        'Cannot wait to see everyone online tonight!',
        5,
        '2025-01-10 20:45:00.000000',
        '2025-01-10 20:45:00.000000'
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
        'Alice',
        'alice@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$tMg1Rd3IEDnp3iFKrqsF4Dsbw6/Cbf6seRB/H5bhaPg$zZj5yn4x3D3O3mDHcW2aczQNiYfAs3cw21XMEIgkF0E',
        '2024-09-01 20:49:38.759432',
        '2024-09-02 03:49:39.927',
        'active'
    ),
    (
        2,
        'Bob',
        'bob@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$CvOMK1WUd99R7kYXpiBPNYw4OQP53pYIgeMnwz92mrE$HPthId4phMoPT1TWuCRHHCr9BSQA8XoUkQuB1HZsqTY',
        '2024-09-02 17:49:23.377425',
        '2024-09-02 17:49:23.377425',
        'active'
    ),
    (
        3,
        'Charlie',
        'charlie@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$paCAAD1HVZkncP/WvecuUO6zFXp2/8BISpgr5rXRxps$M5kBFc9JHHGNw9SXnPu2ggpJY0mFFCska7TXMrllndo',
        '2024-09-03 10:30:15.123456',
        '2024-09-03 10:30:15.123456',
        'active'
    ),
    (
        4,
        'Diana',
        'diana@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$xyz123ABC456DEF789GHI$SampleHashForDiana123',
        '2024-09-04 14:20:30.654321',
        '2024-09-04 14:20:30.654321',
        'active'
    ),
    (
        5,
        'Evan',
        'evan@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$evanHash123$EvanPasswordHash456',
        '2024-09-05 09:15:45.987654',
        '2024-09-05 09:15:45.987654',
        'active'
    ),
    (
        6,
        'Fiona',
        'fiona@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$fionaHash456$FionaPasswordHash789',
        '2024-09-06 16:45:12.345678',
        '2024-09-06 16:45:12.345678',
        'active'
    ),
    (
        7,
        'George',
        'george@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$georgeHash789$GeorgePasswordHash012',
        '2024-09-07 11:30:25.876543',
        '2024-09-07 11:30:25.876543',
        'active'
    ),
    (
        8,
        'Helen',
        'helen@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$helenHash012$HelenPasswordHash345',
        '2024-09-08 13:25:40.234567',
        '2024-09-08 13:25:40.234567',
        'active'
    ),
    (
        9,
        'Ian',
        'ian@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$ianHash345$IanPasswordHash678',
        '2024-09-09 08:40:55.765432',
        '2024-09-09 08:40:55.765432',
        'active'
    ),
    (
        10,
        'Julia',
        'julia@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$juliaHash678$JuliaPasswordHash901',
        '2024-09-10 15:55:18.123456',
        '2024-09-10 15:55:18.123456',
        'active'
    );
ALTER TABLE "public"."messages"
ADD FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");
-- set pk to 11
ALTER SEQUENCE users_id_seq RESTART WITH 11;
-- Indices
CREATE UNIQUE INDEX name_idx ON public.users USING btree (name);
CREATE UNIQUE INDEX email_idx ON public.users USING btree (email);
DROP INDEX IF EXISTS users_email_unique;
CREATE UNIQUE INDEX users_email_unique ON public.users USING btree (email);
