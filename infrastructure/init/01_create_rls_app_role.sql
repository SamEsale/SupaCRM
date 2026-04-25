DO
$$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'supacrm_app'
    ) THEN
        CREATE ROLE supacrm_app
            LOGIN
            PASSWORD 'supacrm_app'
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOREPLICATION
            NOBYPASSRLS;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE supacrm TO supacrm_app;
