import 'next-auth';

declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      email?: string | null;
      name?: string | null;
      image?: string | null;
      isAdmin?: boolean;
      accessToken?: string;
    };
    accessToken?: string;
  }

  interface User {
    id: string;
    email?: string | null;
    name?: string | null;
    isAdmin?: boolean;
    accessToken?: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    id?: string;
    isAdmin?: boolean;
    accessToken?: string;
  }
}
