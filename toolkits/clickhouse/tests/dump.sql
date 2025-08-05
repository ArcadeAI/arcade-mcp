-- ClickHouse test database setup
-- This file contains sample data for testing the ClickHouse toolkit
-- Create users table
CREATE TABLE IF NOT EXISTS default.users (
    id UInt32,
    name String,
    email String,
    password_hash String,
    created_at DateTime,
    updated_at DateTime,
    status String
) ENGINE = MergeTree()
ORDER BY (id, created_at);
-- Create messages table
CREATE TABLE IF NOT EXISTS default.messages (
    id UInt32,
    body String,
    user_id UInt32,
    created_at DateTime,
    updated_at DateTime
) ENGINE = MergeTree()
ORDER BY (id, created_at);
-- Insert sample data into users table
INSERT INTO default.users (
        id,
        name,
        email,
        password_hash,
        created_at,
        updated_at,
        status
    )
VALUES (
        1,
        'Alice',
        'alice@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$tMg1Rd3IEDnp3iFKrqsF4Dsbw6/Cbf6seRB/H5bhaPg$zZj5yn4x3D3O3mDHcW2aczQNiYfAs3cw21XMEIgkF0E',
        '2024-09-01 20:49:38',
        '2024-09-02 03:49:39',
        'active'
    ),
    (
        2,
        'Bob',
        'bob@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$CvOMK1WUd99R7kYXpiBPNYw4OQP53pYIgeMnwz92mrE$HPthId4phMoPT1TWuCRHHCr9BSQA8XoUkQuB1HZsqTY',
        '2024-09-02 17:49:23',
        '2024-09-02 17:49:23',
        'active'
    ),
    (
        3,
        'Charlie',
        'charlie@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$paCAAD1HVZkncP/WvecuUO6zFXp2/8BISpgr5rXRxps$M5kBFc9JHHGNw9SXnPu2ggpJY0mFFCska7TXMrllndo',
        '2024-09-03 10:30:15',
        '2024-09-03 10:30:15',
        'active'
    ),
    (
        4,
        'Diana',
        'diana@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$xyz123ABC456DEF789GHI$SampleHashForDiana123',
        '2024-09-04 14:20:30',
        '2024-09-04 14:20:30',
        'active'
    ),
    (
        5,
        'Evan',
        'evan@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$evanHash123$EvanPasswordHash456',
        '2024-09-05 09:15:45',
        '2024-09-05 09:15:45',
        'active'
    ),
    (
        6,
        'Fiona',
        'fiona@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$fionaHash456$FionaPasswordHash789',
        '2024-09-06 16:45:12',
        '2024-09-06 16:45:12',
        'active'
    ),
    (
        7,
        'George',
        'george@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$georgeHash789$GeorgePasswordHash012',
        '2024-09-07 11:30:25',
        '2024-09-07 11:30:25',
        'active'
    ),
    (
        8,
        'Helen',
        'helen@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$helenHash012$HelenPasswordHash345',
        '2024-09-08 13:25:40',
        '2024-09-08 13:25:40',
        'active'
    ),
    (
        9,
        'Ian',
        'ian@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$ianHash345$IanPasswordHash678',
        '2024-09-09 08:40:55',
        '2024-09-09 08:40:55',
        'active'
    ),
    (
        10,
        'Julia',
        'julia@example.com',
        '$argon2id$v=19$m=65536,t=2,p=1$juliaHash678$JuliaPasswordHash901',
        '2024-09-10 15:55:18',
        '2024-09-10 15:55:18',
        'active'
    );
-- Insert sample data into messages table
INSERT INTO default.messages (id, body, user_id, created_at, updated_at)
VALUES (
        1,
        'Hello everyone!',
        1,
        '2025-01-10 10:00:00',
        '2025-01-10 10:00:00'
    ),
    (
        2,
        'How is everyone doing today?',
        1,
        '2025-01-10 11:30:00',
        '2025-01-10 11:30:00'
    ),
    (
        3,
        'Great to see you all here!',
        1,
        '2025-01-10 14:15:00',
        '2025-01-10 14:15:00'
    ),
    (
        4,
        'Hi Alice! Doing well, thanks for asking.',
        2,
        '2025-01-10 11:35:00',
        '2025-01-10 11:35:00'
    ),
    (
        5,
        'Anyone up for a game later?',
        2,
        '2025-01-10 16:20:00',
        '2025-01-10 16:20:00'
    ),
    (
        6,
        'Count me in for the game!',
        3,
        '2025-01-10 16:25:00',
        '2025-01-10 16:25:00'
    ),
    (
        7,
        'What time works for everyone?',
        3,
        '2025-01-10 16:30:00',
        '2025-01-10 16:30:00'
    ),
    (
        8,
        'I can play around 8 PM',
        3,
        '2025-01-10 17:00:00',
        '2025-01-10 17:00:00'
    ),
    (
        9,
        '8 PM works for me too!',
        4,
        '2025-01-10 17:05:00',
        '2025-01-10 17:05:00'
    ),
    (
        10,
        'What game should we play?',
        4,
        '2025-01-10 17:10:00',
        '2025-01-10 17:10:00'
    ),
    (
        11,
        'I suggest we try the new arcade game!',
        5,
        '2025-01-10 17:15:00',
        '2025-01-10 17:15:00'
    ),
    (
        12,
        'It has great multiplayer features',
        5,
        '2025-01-10 17:20:00',
        '2025-01-10 17:20:00'
    ),
    (
        13,
        'Perfect timing for a weekend session',
        5,
        '2025-01-10 18:00:00',
        '2025-01-10 18:00:00'
    ),
    (
        26,
        'Just finished setting up the game server!',
        5,
        '2025-01-10 20:00:00',
        '2025-01-10 20:00:00'
    ),
    (
        27,
        'Everyone should be able to connect now',
        5,
        '2025-01-10 20:05:00',
        '2025-01-10 20:05:00'
    ),
    (
        28,
        'I added some custom maps too',
        5,
        '2025-01-10 20:10:00',
        '2025-01-10 20:10:00'
    ),
    (
        29,
        'The graphics look amazing on this new version',
        5,
        '2025-01-10 20:15:00',
        '2025-01-10 20:15:00'
    ),
    (
        30,
        'Hope you all enjoy the new features',
        5,
        '2025-01-10 20:20:00',
        '2025-01-10 20:20:00'
    ),
    (
        31,
        'I also set up a leaderboard system',
        5,
        '2025-01-10 20:25:00',
        '2025-01-10 20:25:00'
    ),
    (
        32,
        'We can track high scores now',
        5,
        '2025-01-10 20:30:00',
        '2025-01-10 20:30:00'
    ),
    (
        33,
        'The game supports up to 8 players simultaneously',
        5,
        '2025-01-10 20:35:00',
        '2025-01-10 20:35:00'
    ),
    (
        34,
        'I tested it earlier and it runs smoothly',
        5,
        '2025-01-10 20:40:00',
        '2025-01-10 20:40:00'
    ),
    (
        35,
        'Cannot wait to see everyone online tonight!',
        5,
        '2025-01-10 20:45:00',
        '2025-01-10 20:45:00'
    ),
    (
        14,
        'Sounds like fun! I love arcade games.',
        6,
        '2025-01-10 18:05:00',
        '2025-01-10 18:05:00'
    ),
    (
        15,
        'Should I bring snacks?',
        6,
        '2025-01-10 18:10:00',
        '2025-01-10 18:10:00'
    ),
    (
        16,
        'Snacks are always welcome!',
        7,
        '2025-01-10 18:15:00',
        '2025-01-10 18:15:00'
    ),
    (
        17,
        'I can bring some drinks',
        7,
        '2025-01-10 18:20:00',
        '2025-01-10 18:20:00'
    ),
    (
        18,
        'This is going to be awesome',
        7,
        '2025-01-10 19:00:00',
        '2025-01-10 19:00:00'
    ),
    (
        19,
        'I agree! Cannot wait for the game night.',
        8,
        '2025-01-10 19:05:00',
        '2025-01-10 19:05:00'
    ),
    (
        20,
        'Should we set up a Discord call?',
        8,
        '2025-01-10 19:10:00',
        '2025-01-10 19:10:00'
    ),
    (
        21,
        'Discord would be perfect for voice chat',
        9,
        '2025-01-10 19:15:00',
        '2025-01-10 19:15:00'
    ),
    (
        22,
        'I will create a server for us',
        9,
        '2025-01-10 19:20:00',
        '2025-01-10 19:20:00'
    ),
    (
        23,
        'Link will be shared in a few minutes',
        9,
        '2025-01-10 19:25:00',
        '2025-01-10 19:25:00'
    ),
    (
        24,
        'Thanks Ian! You are the best.',
        10,
        '2025-01-10 19:30:00',
        '2025-01-10 19:30:00'
    ),
    (
        25,
        'See you all at 8 PM!',
        10,
        '2025-01-10 19:35:00',
        '2025-01-10 19:35:00'
    );
