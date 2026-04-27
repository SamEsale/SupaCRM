SELECT conname
FROM pg_constraint
WHERE conname IN (
  'uq_role_permissions',
  'uq_tenant_user_roles',
  'uq_tenant_users_tenant_user'
)
ORDER BY conname;
