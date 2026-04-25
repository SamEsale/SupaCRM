## SupaCRM Frontend

This frontend is part of the SupaCRM monorepo. The canonical operator/developer startup instructions live at the repo root and in the runbooks.

## Local Frontend Startup

1. Ensure the backend is available at `http://127.0.0.1:8000`
2. Create `frontend/.env.local` from `frontend/.env.local.example`
3. Start the frontend:

```bash
npm run dev
```

Or use the repo helper from the workspace root:

```bash
bash scripts/dev/start_local_frontend.sh
```

Then open [http://127.0.0.1:3000/login](http://127.0.0.1:3000/login).

## API Base URL

The frontend requires:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

See:

- [`README.md`](/Users/samesale/Desktop/SupaCRM/README.md)
- [`docs/runbooks/local_startup.md`](/Users/samesale/Desktop/SupaCRM/docs/runbooks/local_startup.md)
- [`docs/runbooks/local_login.md`](/Users/samesale/Desktop/SupaCRM/docs/runbooks/local_login.md)

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
