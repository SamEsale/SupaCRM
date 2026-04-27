\set ON_ERROR_STOP on

ALTER DATABASE :"db_name" OWNER TO :"admin_user";

ALTER SCHEMA public OWNER TO :"admin_user";

SELECT format(
    'ALTER TABLE %I.%I OWNER TO %I',
    n.nspname,
    c.relname,
    :'admin_user'
)
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p')
  AND pg_get_userbyid(c.relowner) = current_user;
\gexec

SELECT format(
    'ALTER SEQUENCE %I.%I OWNER TO %I',
    n.nspname,
    c.relname,
    :'admin_user'
)
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'S'
  AND pg_get_userbyid(c.relowner) = current_user;
\gexec

SELECT format(
    'ALTER VIEW %I.%I OWNER TO %I',
    n.nspname,
    c.relname,
    :'admin_user'
)
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind IN ('v', 'm')
  AND pg_get_userbyid(c.relowner) = current_user;
\gexec

SELECT format(
    'ALTER FUNCTION %s OWNER TO %I',
    p.oid::regprocedure,
    :'admin_user'
)
FROM pg_proc AS p
JOIN pg_namespace AS n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND pg_get_userbyid(p.proowner) = current_user;
\gexec
