// MongoDB test data dump - equivalent to PostgreSQL dump.sql
// This script sets up test data for the MongoDB toolkit

// Switch to test database
use('test_database');

// Clear existing data
db.users.drop();
db.messages.drop();

// Create users collection with data
db.users.insertMany([
  {
    _id: 1,
    name: 'Alice',
    email: 'alice@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$tMg1Rd3IEDnp3iFKrqsF4Dsbw6/Cbf6seRB/H5bhaPg$zZj5yn4x3D3O3mDHcW2aczQNiYfAs3cw21XMEIgkF0E',
    created_at: new Date('2024-09-01T20:49:38.759Z'),
    updated_at: new Date('2024-09-02T03:49:39.927Z'),
    status: 'active'
  },
  {
    _id: 2,
    name: 'Bob',
    email: 'bob@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$CvOMK1WUd99R7kYXpiBPNYw4OQP53pYIgeMnwz92mrE$HPthId4phMoPT1TWuCRHHCr9BSQA8XoUkQuB1HZsqTY',
    created_at: new Date('2024-09-02T17:49:23.377Z'),
    updated_at: new Date('2024-09-02T17:49:23.377Z'),
    status: 'active'
  },
  {
    _id: 3,
    name: 'Charlie',
    email: 'charlie@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$paCAAD1HVZkncP/WvecuUO6zFXp2/8BISpgr5rXRxps$M5kBFc9JHHGNw9SXnPu2ggpJY0mFFCska7TXMrllndo',
    created_at: new Date('2024-09-03T10:30:15.123Z'),
    updated_at: new Date('2024-09-03T10:30:15.123Z'),
    status: 'active'
  },
  {
    _id: 4,
    name: 'Diana',
    email: 'diana@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$xyz123ABC456DEF789GHI$SampleHashForDiana123',
    created_at: new Date('2024-09-04T14:20:30.654Z'),
    updated_at: new Date('2024-09-04T14:20:30.654Z'),
    status: 'active'
  },
  {
    _id: 5,
    name: 'Evan',
    email: 'evan@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$evanHash123$EvanPasswordHash456',
    created_at: new Date('2024-09-05T09:15:45.987Z'),
    updated_at: new Date('2024-09-05T09:15:45.987Z'),
    status: 'active'
  },
  {
    _id: 6,
    name: 'Fiona',
    email: 'fiona@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$fionaHash456$FionaPasswordHash789',
    created_at: new Date('2024-09-06T16:45:12.345Z'),
    updated_at: new Date('2024-09-06T16:45:12.345Z'),
    status: 'active'
  },
  {
    _id: 7,
    name: 'George',
    email: 'george@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$georgeHash789$GeorgePasswordHash012',
    created_at: new Date('2024-09-07T11:30:25.876Z'),
    updated_at: new Date('2024-09-07T11:30:25.876Z'),
    status: 'active'
  },
  {
    _id: 8,
    name: 'Helen',
    email: 'helen@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$helenHash012$HelenPasswordHash345',
    created_at: new Date('2024-09-08T13:25:40.234Z'),
    updated_at: new Date('2024-09-08T13:25:40.234Z'),
    status: 'active'
  },
  {
    _id: 9,
    name: 'Ian',
    email: 'ian@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$ianHash345$IanPasswordHash678',
    created_at: new Date('2024-09-09T08:40:55.765Z'),
    updated_at: new Date('2024-09-09T08:40:55.765Z'),
    status: 'active'
  },
  {
    _id: 10,
    name: 'Julia',
    email: 'julia@example.com',
    password_hash: '$argon2id$v=19$m=65536,t=2,p=1$juliaHash678$JuliaPasswordHash901',
    created_at: new Date('2024-09-10T15:55:18.123Z'),
    updated_at: new Date('2024-09-10T15:55:18.123Z'),
    status: 'active'
  }
]);

// Create messages collection with data
db.messages.insertMany([
  // User 1 (Alice) - 3 messages
  {
    _id: 1,
    body: 'Hello everyone!',
    user_id: 1,
    created_at: new Date('2025-01-10T10:00:00.000Z'),
    updated_at: new Date('2025-01-10T10:00:00.000Z')
  },
  {
    _id: 2,
    body: 'How is everyone doing today?',
    user_id: 1,
    created_at: new Date('2025-01-10T11:30:00.000Z'),
    updated_at: new Date('2025-01-10T11:30:00.000Z')
  },
  {
    _id: 3,
    body: 'Great to see you all here!',
    user_id: 1,
    created_at: new Date('2025-01-10T14:15:00.000Z'),
    updated_at: new Date('2025-01-10T14:15:00.000Z')
  },
  // User 2 (Bob) - 2 messages
  {
    _id: 4,
    body: 'Hi Alice! Doing well, thanks for asking.',
    user_id: 2,
    created_at: new Date('2025-01-10T11:35:00.000Z'),
    updated_at: new Date('2025-01-10T11:35:00.000Z')
  },
  {
    _id: 5,
    body: 'Anyone up for a game later?',
    user_id: 2,
    created_at: new Date('2025-01-10T16:20:00.000Z'),
    updated_at: new Date('2025-01-10T16:20:00.000Z')
  },
  // User 3 (Charlie) - 3 messages
  {
    _id: 6,
    body: 'Count me in for the game!',
    user_id: 3,
    created_at: new Date('2025-01-10T16:25:00.000Z'),
    updated_at: new Date('2025-01-10T16:25:00.000Z')
  },
  {
    _id: 7,
    body: 'What time works for everyone?',
    user_id: 3,
    created_at: new Date('2025-01-10T16:30:00.000Z'),
    updated_at: new Date('2025-01-10T16:30:00.000Z')
  },
  {
    _id: 8,
    body: 'I can play around 8 PM',
    user_id: 3,
    created_at: new Date('2025-01-10T17:00:00.000Z'),
    updated_at: new Date('2025-01-10T17:00:00.000Z')
  },
  // User 4 (Diana) - 2 messages
  {
    _id: 9,
    body: '8 PM works for me too!',
    user_id: 4,
    created_at: new Date('2025-01-10T17:05:00.000Z'),
    updated_at: new Date('2025-01-10T17:05:00.000Z')
  },
  {
    _id: 10,
    body: 'What game should we play?',
    user_id: 4,
    created_at: new Date('2025-01-10T17:10:00.000Z'),
    updated_at: new Date('2025-01-10T17:10:00.000Z')
  },
  // User 5 (Evan) - 13 messages (including 10 additional ones)
  {
    _id: 11,
    body: 'I suggest we try the new arcade game!',
    user_id: 5,
    created_at: new Date('2025-01-10T17:15:00.000Z'),
    updated_at: new Date('2025-01-10T17:15:00.000Z')
  },
  {
    _id: 12,
    body: 'It has great multiplayer features',
    user_id: 5,
    created_at: new Date('2025-01-10T17:20:00.000Z'),
    updated_at: new Date('2025-01-10T17:20:00.000Z')
  },
  {
    _id: 13,
    body: 'Perfect timing for a weekend session',
    user_id: 5,
    created_at: new Date('2025-01-10T18:00:00.000Z'),
    updated_at: new Date('2025-01-10T18:00:00.000Z')
  },
  {
    _id: 26,
    body: 'Just finished setting up the game server!',
    user_id: 5,
    created_at: new Date('2025-01-10T20:00:00.000Z'),
    updated_at: new Date('2025-01-10T20:00:00.000Z')
  },
  {
    _id: 27,
    body: 'Everyone should be able to connect now',
    user_id: 5,
    created_at: new Date('2025-01-10T20:05:00.000Z'),
    updated_at: new Date('2025-01-10T20:05:00.000Z')
  },
  {
    _id: 28,
    body: 'I added some custom maps too',
    user_id: 5,
    created_at: new Date('2025-01-10T20:10:00.000Z'),
    updated_at: new Date('2025-01-10T20:10:00.000Z')
  },
  {
    _id: 29,
    body: 'The graphics look amazing on this new version',
    user_id: 5,
    created_at: new Date('2025-01-10T20:15:00.000Z'),
    updated_at: new Date('2025-01-10T20:15:00.000Z')
  },
  {
    _id: 30,
    body: 'Hope you all enjoy the new features',
    user_id: 5,
    created_at: new Date('2025-01-10T20:20:00.000Z'),
    updated_at: new Date('2025-01-10T20:20:00.000Z')
  },
  {
    _id: 31,
    body: 'I also set up a leaderboard system',
    user_id: 5,
    created_at: new Date('2025-01-10T20:25:00.000Z'),
    updated_at: new Date('2025-01-10T20:25:00.000Z')
  },
  {
    _id: 32,
    body: 'We can track high scores now',
    user_id: 5,
    created_at: new Date('2025-01-10T20:30:00.000Z'),
    updated_at: new Date('2025-01-10T20:30:00.000Z')
  },
  {
    _id: 33,
    body: 'The game supports up to 8 players simultaneously',
    user_id: 5,
    created_at: new Date('2025-01-10T20:35:00.000Z'),
    updated_at: new Date('2025-01-10T20:35:00.000Z')
  },
  {
    _id: 34,
    body: 'I tested it earlier and it runs smoothly',
    user_id: 5,
    created_at: new Date('2025-01-10T20:40:00.000Z'),
    updated_at: new Date('2025-01-10T20:40:00.000Z')
  },
  {
    _id: 35,
    body: 'Cannot wait to see everyone online tonight!',
    user_id: 5,
    created_at: new Date('2025-01-10T20:45:00.000Z'),
    updated_at: new Date('2025-01-10T20:45:00.000Z')
  },
  // User 6 (Fiona) - 2 messages
  {
    _id: 14,
    body: 'Sounds like fun! I love arcade games.',
    user_id: 6,
    created_at: new Date('2025-01-10T18:05:00.000Z'),
    updated_at: new Date('2025-01-10T18:05:00.000Z')
  },
  {
    _id: 15,
    body: 'Should I bring snacks?',
    user_id: 6,
    created_at: new Date('2025-01-10T18:10:00.000Z'),
    updated_at: new Date('2025-01-10T18:10:00.000Z')
  },
  // User 7 (George) - 3 messages
  {
    _id: 16,
    body: 'Snacks are always welcome!',
    user_id: 7,
    created_at: new Date('2025-01-10T18:15:00.000Z'),
    updated_at: new Date('2025-01-10T18:15:00.000Z')
  },
  {
    _id: 17,
    body: 'I can bring some drinks',
    user_id: 7,
    created_at: new Date('2025-01-10T18:20:00.000Z'),
    updated_at: new Date('2025-01-10T18:20:00.000Z')
  },
  {
    _id: 18,
    body: 'This is going to be awesome',
    user_id: 7,
    created_at: new Date('2025-01-10T19:00:00.000Z'),
    updated_at: new Date('2025-01-10T19:00:00.000Z')
  },
  // User 8 (Helen) - 2 messages
  {
    _id: 19,
    body: 'I agree! Cannot wait for the game night.',
    user_id: 8,
    created_at: new Date('2025-01-10T19:05:00.000Z'),
    updated_at: new Date('2025-01-10T19:05:00.000Z')
  },
  {
    _id: 20,
    body: 'Should we set up a Discord call?',
    user_id: 8,
    created_at: new Date('2025-01-10T19:10:00.000Z'),
    updated_at: new Date('2025-01-10T19:10:00.000Z')
  },
  // User 9 (Ian) - 3 messages
  {
    _id: 21,
    body: 'Discord would be perfect for voice chat',
    user_id: 9,
    created_at: new Date('2025-01-10T19:15:00.000Z'),
    updated_at: new Date('2025-01-10T19:15:00.000Z')
  },
  {
    _id: 22,
    body: 'I will create a server for us',
    user_id: 9,
    created_at: new Date('2025-01-10T19:20:00.000Z'),
    updated_at: new Date('2025-01-10T19:20:00.000Z')
  },
  {
    _id: 23,
    body: 'Link will be shared in a few minutes',
    user_id: 9,
    created_at: new Date('2025-01-10T19:25:00.000Z'),
    updated_at: new Date('2025-01-10T19:25:00.000Z')
  },
  // User 10 (Julia) - 2 messages
  {
    _id: 24,
    body: 'Thanks Ian! You are the best.',
    user_id: 10,
    created_at: new Date('2025-01-10T19:30:00.000Z'),
    updated_at: new Date('2025-01-10T19:30:00.000Z')
  },
  {
    _id: 25,
    body: 'See you all at 8 PM!',
    user_id: 10,
    created_at: new Date('2025-01-10T19:35:00.000Z'),
    updated_at: new Date('2025-01-10T19:35:00.000Z')
  },{
    _id: 99,
    body: 'You are a mean jerk, you shithead!',
    user_id: 10,
    created_at: new Date('2025-01-10T19:35:00.000Z'),
    updated_at: new Date('2025-01-10T19:35:00.000Z')
  }
]);

// Create indexes for better performance (equivalent to PostgreSQL indexes)
db.users.createIndex({ "name": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.messages.createIndex({ "user_id": 1 });
db.messages.createIndex({ "created_at": 1 });

print("MongoDB test data setup completed successfully!");
print("Users collection: " + db.users.countDocuments());
print("Messages collection: " + db.messages.countDocuments());
