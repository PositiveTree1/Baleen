import { NextResponse } from 'next/server';

export async function GET() {
  let backendUrl = (
    process.env.BACKEND_URL || 
    process.env.NEXT_PUBLIC_BACKEND_URL || 
    process.env.NEXT_PUBLIC_API_URL || 
    'NONE_SET'
  ).trim().replace(/\/$/, '');

  if (backendUrl && backendUrl !== 'NONE_SET' && !backendUrl.startsWith('http://') && !backendUrl.startsWith('https://')) {
    backendUrl = `https://${backendUrl}`;
  }

  // Test if we can actually reach the backend
  let backendReachable = false;
  let backendError = '';
  try {
    const res = await fetch(`${backendUrl}/health`, { 
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
