import { NextResponse } from 'next/server';

export async function GET() {
  const backendUrl = (
    process.env.BACKEND_URL || 
    process.env.NEXT_PUBLIC_BACKEND_URL || 
    process.env.NEXT_PUBLIC_API_URL || 
    'NONE_SET'
  );

  // Test if we can actually reach the backend
  let backendReachable = false;
  let backendError = '';
  try {
    const res = await fetch(`${backendUrl.replace(/\/$/, '')}/health`, { 
      signal: AbortSignal.timeout(5000) 
    });
    backendReachable = res.ok;
  } catch (e: any) {
    backendError = e?.message || String(e);
  }

  return NextResponse.json({
    BACKEND_URL: process.env.BACKEND_URL || 'NOT SET',
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'NOT SET',
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'NOT SET',
    AUTH_SECRET_SET: !!(process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET),
    resolvedBackendUrl: backendUrl,
    backendReachable,
    backendError: backendError || undefined,
  });
}
