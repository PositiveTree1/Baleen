import { Wallet, WalletDetail, ExecutionLog, User, PlatformStats } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchWallets(params?: Record<string, string>): Promise<Wallet[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/wallets`);
    if (params) {
      Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    }
    const res = await fetch(url.toString(), { next: { revalidate: 60 } });
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    return [];
  }
}

export async function fetchWallet(address: string): Promise<WalletDetail | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/wallets/${address}`);
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function fetchExecutionLogs(userId?: string, params?: Record<string, string>): Promise<ExecutionLog[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/executions`);
    if (userId) url.searchParams.append('userId', userId);
    if (params) {
      Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    }
    const res = await fetch(url.toString());
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    return [];
  }
}

export async function fetchUserSettings(userId: string): Promise<User | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/users/${userId}`);
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function updateUserSettings(userId: string, data: Partial<User>): Promise<User | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function signUp(email: string, password: string, startingBalance: number): Promise<User | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, startingBalance }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function fetchPlatformStats(): Promise<PlatformStats | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/stats`, { next: { revalidate: 10 } });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}
