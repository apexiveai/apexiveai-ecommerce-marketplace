npm install lucide-react
notepad .env.local

NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1

## Vehicle marketplace accounts

The Buyer and Seller workspaces are available at `/buyer` and `/seller`.
Buyers can be individual or corporate accounts. Sellers can be private owners
or dealers; dealer business profiles support car showrooms, automotive
companies, and authorized dealers.

The account and vehicle marketplace models are stored in the `accounts` and
`sellers` Django apps. They cover buyer and seller profiles, showroom teams,
vehicle listings, favorites, buyer-seller conversations, customer leads,
test-drive bookings, reservations, sales, commissions, and dealer
subscriptions. Apply schema changes with:

```powershell
python manage.py migrate
```

## Sign in and account setup

Start the Django API and the Next.js frontend, then use `/login` to sign in or
register a buyer or seller account. Login accepts either the username or email.
Seller accounts can sign in immediately, but listing products requires seller
approval. Superadmin accounts are not created through public registration; run
`python manage.py createsuperuser` from the backend and use those credentials
to sign in. Browser sessions are kept in session storage and are revoked when
you sign out while the API is reachable.

Run `python manage.py migrate` after enabling the JWT blacklist app so refresh
tokens can be revoked on sign-out.