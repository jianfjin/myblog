-- SQLite
select * from users;

select * from cards;

SELECT name FROM sqlite_master WHERE type='table';

SELECT * FROM article_media;

UPDATE users SET role = 'ADMIN' WHERE id = 1;
UPDATE users SET role = 'DEVELOPER' WHERE id = 2;