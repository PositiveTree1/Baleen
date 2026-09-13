import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';

const authSecret = process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET || 'baleen_super_secret_sandbox_jwt_key_2026_polymarket';
if (!process.env.AUTH_SECRET && !process.env.NEXTAUTH_SECRET && process.env.NODE_ENV === 'production') {
  throw new Error("AUTH_SECRET or NEXTAUTH_SECRET is required in production");
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  secret: authSecret,
  trustHost: true,
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
        isGuest: { label: 'Is Guest', type: 'text' },
        guestToken: { label: 'Guest Token', type: 'text' },
        guestId: { label: 'Guest ID', type: 'text' },
      },
      async authorize(credentials) {
        let backendUrl = (
          process.env.BACKEND_URL || 
          process.env.NEXT_PUBLIC_BACKEND_URL || 
          process.env.NEXT_PUBLIC_API_URL || 
          'http://localhost:8000'
        ).trim().replace(/\/$/, '');

        if (backendUrl && !backendUrl.startsWith('http://') && !backendUrl.startsWith('https://')) {
          backendUrl = `https://${backendUrl}`;
        }

        // Fast-path: Pre-provisioned guest credentials from client
        if (credentials?.isGuest === 'true' && credentials?.guestToken && credentials?.guestId) {
          return {
            id: String(credentials.guestId),
            email: String(credentials.email || `guest_${String(credentials.guestId).slice(0, 8)}@baleen.local`),
            name: 'Guest Trader',
            isAdmin: false,
            accessToken: String(credentials.guestToken),
          };
        }

        // Direct server-side guest session provisioning
        if (credentials?.isGuest === 'true' || credentials?.email === 'guest') {
          try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000);

            const res = await fetch(`${backendUrl}/api/auth/guest`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              signal: controller.signal,
            });
            clearTimeout(timeoutId);

            if (res.ok) {
              const guest = await res.json();
              return {
                id: guest.id,
                email: guest.email,
                name: 'Guest Trader',
                isAdmin: false,
                accessToken: guest.access_token,
              };
            }
          } catch (e) {
            console.error("NextAuth guest authorization error:", e);
          }
          return null;
        }

        // Standard email/password authentication
        if (!credentials?.email || !credentials?.password) return null;

        const email = String(credentials.email).toLowerCase().trim();
        const password = String(credentials.password);

        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 15000);

          const res = await fetch(
            `${backendUrl}/api/auth/login`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                email,
                password,
              }),
              signal: controller.signal,
            }
          );
          clearTimeout(timeoutId);

          if (res.ok) {
            const user = await res.json();
            return {
              id: user.id,
              email: user.email,
              name: user.name || user.email,
              isAdmin: Boolean(user.is_admin || user.isAdmin),
              accessToken: user.access_token,
            };
          }
        } catch (e) {
          console.error("NextAuth backend authorize error:", e);
        }

        return null;
      },
    }),
  ],
  session: {
    strategy: 'jwt',
    maxAge: 72 * 60 * 60,
  },
  pages: {
    signIn: '/auth/login',
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.isAdmin = (user as { isAdmin?: boolean }).isAdmin;
        token.accessToken = (user as { accessToken?: string }).accessToken;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        const u = session.user as { id?: string; isAdmin?: boolean; accessToken?: string };
        u.id = token.id as string;
        u.isAdmin = Boolean(token.isAdmin);
        u.accessToken = token.accessToken as string;
      }
      (session as { accessToken?: string }).accessToken = token.accessToken as string;
      return session;
    },
  },
});
