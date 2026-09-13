'use client';
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { 
  fetchUserSettings, 
  updateUserSettings, 
  fetchPortfolioSummary,
  saveLiveCredentials,
  fetchLiveCredentials,
  fetchLiveExecutionState,
  getLiveOrderStateLabel,
  LiveExecutionState,
  testLiveConnection,
  setAuthToken,
  formatUtcDate,
  fetchSessionSetup,
  prepareSession,
  verifySession,
  disableSession,
  fetchSessionOperations,
  prepareSessionOperation,
  submitSessionSignature,
  initializeLiveAccount,
  fetchCopyPolicy,
  saveCopyPolicy,
  fetchPaperRuns,
  fetchPaperRunTrades,
  LiveSessionSetup,
  SessionOperation,
  LiveAccountInitialization,
  LiveCopyPolicy,
  CopyPolicyRequest,
  PaperRun,
  PaperRunTrade
} from '@/lib/api-client';
import { signSessionOperation } from '@/lib/session-wallet-approval';
import { User, PortfolioSummary, TestConnectionResult } from '@/types';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { Modal } from '@/components/ui/Modal';
import { ResetSandboxModal } from '@/components/dashboard/ResetSandboxModal';
import { 
  ArrowLeft, 
  Save, 
  Moon, 
  Sun, 
  Key, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Lock,
  Download,
  FileSpreadsheet,
  Layers,
  StopCircle,
  FileText,
  Shield,
  HelpCircle,
  Check
} from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import Link from 'next/link';

export default function SettingsPage() {
  const { data: session, status: sessionStatus } = useSession();
  const { theme, toggleTheme } = useTheme();

  // User Preferences State
  const [user, setUser] = useState<User | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [isResetOpen, setIsResetOpen] = useState(false);
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [savedPreferencesSuccess, setSavedPreferencesSuccess] = useState(false);
  const [riskProfile, setRiskProfile] = useState<'Conservative' | 'Balanced' | 'Aggressive'>('Balanced');
  const [dailyDigest, setDailyDigest] = useState(true);

  // L2 API Credentials State
  const [proxyAddress, setProxyAddress] = useState('');
  const [signerAddress, setSignerAddress] = useState('');
  const [signatureType, setSignatureType] = useState<number>(0);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [isConfigured, setIsConfigured] = useState(false);
  const [liveBalanceUsdc, setLiveBalanceUsdc] = useState<number | null>(null);
  const [lastVerifiedAt, setLastVerifiedAt] = useState<string | null>(null);
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [credentialsSavedSuccess, setCredentialsSavedSuccess] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<TestConnectionResult | null>(null);
  const [credentialError, setCredentialError] = useState<string | null>(null);

  // Read-only Execution State
  const [executionState, setExecutionState] = useState<LiveExecutionState | null>(null);
  const [executionStateLoaded, setExecutionStateLoaded] = useState(false);
  const [refreshingExecutionState, setRefreshingExecutionState] = useState(false);

  // Session Setup State
  const [sessionSetup, setSessionSetup] = useState<LiveSessionSetup | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [sessionSuccess, setSessionSuccess] = useState<string | null>(null);
  const [sessionOperations, setSessionOperations] = useState<SessionOperation[]>([]);
  const [activePreparedOperation, setActivePreparedOperation] = useState<SessionOperation | null>(null);
  const [preparingOpKind, setPreparingOpKind] = useState<'AUTHORIZE' | 'REVOKE' | null>(null);
  const [signingOpId, setSigningOpId] = useState<string | null>(null);
  const [walletApprovalError, setWalletApprovalError] = useState<string | null>(null);

  // Baseline Initialization State
  const [initResult, setInitResult] = useState<LiveAccountInitialization | null>(null);
  const [initLoading, setInitLoading] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [initSuccess, setInitSuccess] = useState<string | null>(null);

  // Copy Policy State
  const [copyPolicy, setCopyPolicy] = useState<LiveCopyPolicy | null>(null);
  const [policyLoaded, setPolicyLoaded] = useState(false);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [policySaving, setPolicySaving] = useState(false);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [policySuccess, setPolicySuccess] = useState<string | null>(null);

  // Policy Form Inputs (Retained on error; empty when unset)
  const [policySourceWallets, setPolicySourceWallets] = useState('');
  const [policyCopyRatio, setPolicyCopyRatio] = useState('');
  const [policyMaxOrderCash, setPolicyMaxOrderCash] = useState('');
  const [policyMaxTotalExposure, setPolicyMaxTotalExposure] = useState('');
  const [policyMaxTokenExposure, setPolicyMaxTokenExposure] = useState('');
  const [policyMaxDailyLoss, setPolicyMaxDailyLoss] = useState('');
  const [policyMaxOpenOrders, setPolicyMaxOpenOrders] = useState('');
  const [policyMaxSlippageBps, setPolicyMaxSlippageBps] = useState('');
  const [policyMaxFeeBps, setPolicyMaxFeeBps] = useState('');
  const [policyMaxQuoteAgeMs, setPolicyMaxQuoteAgeMs] = useState('');
  const [policyMaxSourceAgeMs, setPolicyMaxSourceAgeMs] = useState('');

  // Paper Run Archives State
  const [paperRuns, setPaperRuns] = useState<PaperRun[]>([]);
  const [loadingPaperRuns, setLoadingPaperRuns] = useState(false);
  const [paperRunsError, setPaperRunsError] = useState<string | null>(null);
  const [selectedRunTrades, setSelectedRunTrades] = useState<PaperRunTrade[] | null>(null);
  const [tradesModalRunId, setTradesModalRunId] = useState<string | null>(null);
  const [loadingTrades, setLoadingTrades] = useState(false);

  const clearPrivateState = () => {
    setUser(null);
    setPortfolio(null);
    setIsConfigured(false);
    setLiveBalanceUsdc(null);
    setLastVerifiedAt(null);
    setProxyAddress('');
    setSignerAddress('');
    setSignatureType(0);
    setApiKey('');
    setApiSecret('');
    setPassphrase('');
    setCredentialError(null);
    setCredentialsSavedSuccess(false);
    setTestResult(null);
    setExecutionState(null);
    setExecutionStateLoaded(false);
    setSessionSetup(null);
    setSessionLoading(false);
    setSessionError(null);
    setSessionSuccess(null);
    setSessionOperations([]);
    setActivePreparedOperation(null);
    setPreparingOpKind(null);
    setSigningOpId(null);
    setWalletApprovalError(null);
    setInitResult(null);
    setInitLoading(false);
    setInitError(null);
    setInitSuccess(null);
    setCopyPolicy(null);
    setPolicyLoaded(false);
    setPolicyLoading(false);
    setPolicySaving(false);
    setPolicyError(null);
    setPolicySuccess(null);
    setPolicySourceWallets('');
    setPolicyCopyRatio('');
    setPolicyMaxOrderCash('');
    setPolicyMaxTotalExposure('');
    setPolicyMaxTokenExposure('');
    setPolicyMaxDailyLoss('');
    setPolicyMaxOpenOrders('');
    setPolicyMaxSlippageBps('');
    setPolicyMaxFeeBps('');
    setPolicyMaxQuoteAgeMs('');
    setPolicyMaxSourceAgeMs('');
    setPaperRuns([]);
    setLoadingPaperRuns(false);
    setPaperRunsError(null);
    setSelectedRunTrades(null);
    setTradesModalRunId(null);
  };

  const loadSessionData = async () => {
    setSessionLoading(true);
    setSessionError(null);
    try {
      const [setup, ops] = await Promise.all([
        fetchSessionSetup(),
        fetchSessionOperations()
      ]);
      setSessionSetup(setup);
      setSessionOperations(ops);
      const prepared = ops.find(o => o.state === 'PREPARED');
      if (prepared) {
        setActivePreparedOperation(prepared);
      }
    } catch (err: unknown) {
      setSessionError(err instanceof Error ? err.message : 'Failed to load session setup');
    } finally {
      setSessionLoading(false);
    }
  };

  const loadPolicyData = async () => {
    setPolicyLoading(true);
    setPolicyError(null);
    try {
      const policy = await fetchCopyPolicy();
      setCopyPolicy(policy);
      setPolicyLoaded(true);
      if (policy) {
        setPolicySourceWallets(policy.source_wallets.join('\n'));
        setPolicyCopyRatio(policy.copy_ratio);
        setPolicyMaxOrderCash(policy.limits.max_order_cash);
        setPolicyMaxTotalExposure(policy.limits.max_total_exposure);
        setPolicyMaxTokenExposure(policy.limits.max_token_exposure);
        setPolicyMaxDailyLoss(policy.limits.max_daily_loss);
        setPolicyMaxOpenOrders(String(policy.limits.max_open_orders));
        setPolicyMaxSlippageBps(policy.limits.max_slippage_bps);
        setPolicyMaxFeeBps(policy.limits.max_fee_bps);
        setPolicyMaxQuoteAgeMs(String(policy.limits.max_quote_age_ms));
        setPolicyMaxSourceAgeMs(String(policy.limits.max_source_age_ms));
      } else {
        setPolicySourceWallets('');
        setPolicyCopyRatio('');
        setPolicyMaxOrderCash('');
        setPolicyMaxTotalExposure('');
        setPolicyMaxTokenExposure('');
        setPolicyMaxDailyLoss('');
        setPolicyMaxOpenOrders('');
        setPolicyMaxSlippageBps('');
        setPolicyMaxFeeBps('');
        setPolicyMaxQuoteAgeMs('');
        setPolicyMaxSourceAgeMs('');
      }
    } catch (err: unknown) {
      setPolicyError(err instanceof Error ? err.message : 'Failed to load copy policy');
    } finally {
      setPolicyLoading(false);
    }
  };

  const loadPaperRuns = async () => {
    if (!session?.user?.id) return;
    setLoadingPaperRuns(true);
    setPaperRunsError(null);
    try {
      const runs = await fetchPaperRuns(session.user.id);
      setPaperRuns(runs);
    } catch (err: unknown) {
      setPaperRunsError(err instanceof Error ? err.message : 'Failed to load paper run archives');
    } finally {
      setLoadingPaperRuns(false);
    }
  };

  const refreshExecutionState = async () => {
    setRefreshingExecutionState(true);
    const result = await fetchLiveExecutionState();
    setExecutionState(result);
    setExecutionStateLoaded(true);
    setRefreshingExecutionState(false);
  };

  const reloadAllUserData = () => {
    if (!session?.user?.id) return;
    const userId = session.user.id;
    Promise.all([
      fetchUserSettings(userId),
      fetchPortfolioSummary(userId),
      fetchLiveCredentials(userId),
      fetchLiveExecutionState(),
      fetchSessionSetup().catch(() => null),
      fetchSessionOperations().catch(() => []),
      fetchCopyPolicy().catch(() => null),
      fetchPaperRuns(userId).catch(() => []),
    ]).then(([userData, portfolioData, liveCreds, stateData, sessionData, opsData, policyData, runsData]) => {
      if (userData) {
        setUser(userData);
        setRiskProfile(userData.riskProfile || 'Balanced');
        setDailyDigest(userData.dailyDigestOptIn);
      }
      if (portfolioData) setPortfolio(portfolioData);
      if (liveCreds) {
        setIsConfigured(liveCreds.is_configured);
        setLiveBalanceUsdc(liveCreds.live_balance_usdc ?? null);
        setLastVerifiedAt(liveCreds.last_verified_at);
        setSignerAddress(liveCreds.signer_address || '');
        setSignatureType(liveCreds.signature_type ?? 0);
        if (liveCreds.polymarket_wallet_address) setProxyAddress(liveCreds.polymarket_wallet_address);
        if (liveCreds.clob_api_key_masked) setApiKey(liveCreds.clob_api_key_masked);
      }
      setExecutionState(stateData);
      setExecutionStateLoaded(true);

      if (sessionData) setSessionSetup(sessionData);
      if (opsData) {
        setSessionOperations(opsData);
        const prepared = opsData.find(o => o.state === 'PREPARED');
        if (prepared) setActivePreparedOperation(prepared);
      }
      setCopyPolicy(policyData);
      setPolicyLoaded(true);
      if (policyData) {
        setPolicySourceWallets(policyData.source_wallets.join('\n'));
        setPolicyCopyRatio(policyData.copy_ratio);
        setPolicyMaxOrderCash(policyData.limits.max_order_cash);
        setPolicyMaxTotalExposure(policyData.limits.max_total_exposure);
        setPolicyMaxTokenExposure(policyData.limits.max_token_exposure);
        setPolicyMaxDailyLoss(policyData.limits.max_daily_loss);
        setPolicyMaxOpenOrders(String(policyData.limits.max_open_orders));
        setPolicyMaxSlippageBps(policyData.limits.max_slippage_bps);
        setPolicyMaxFeeBps(policyData.limits.max_fee_bps);
        setPolicyMaxQuoteAgeMs(String(policyData.limits.max_quote_age_ms));
        setPolicyMaxSourceAgeMs(String(policyData.limits.max_source_age_ms));
      } else {
        setPolicySourceWallets('');
        setPolicyCopyRatio('');
        setPolicyMaxOrderCash('');
        setPolicyMaxTotalExposure('');
        setPolicyMaxTokenExposure('');
        setPolicyMaxDailyLoss('');
        setPolicyMaxOpenOrders('');
        setPolicyMaxSlippageBps('');
        setPolicyMaxFeeBps('');
        setPolicyMaxQuoteAgeMs('');
        setPolicyMaxSourceAgeMs('');
      }
      setPaperRuns(runsData);
    });
  };

  useEffect(() => {
    let ignore = false;
    const token = session?.user?.accessToken || (session as { accessToken?: string })?.accessToken;
    if (token) {
      setAuthToken(token);
    }
    Promise.resolve().then(() => {
      if (!ignore) clearPrivateState();
    });
    if (!session?.user?.id) {
      return () => { ignore = true; };
    }
    const userId = session.user.id;

    Promise.all([
      fetchUserSettings(userId),
      fetchPortfolioSummary(userId),
      fetchLiveCredentials(userId),
      fetchLiveExecutionState(),
      fetchSessionSetup().catch(() => null),
      fetchSessionOperations().catch(() => []),
      fetchCopyPolicy().catch(() => null),
      fetchPaperRuns(userId).catch(() => []),
    ]).then(([userData, portfolioData, liveCreds, stateData, sessionData, opsData, policyData, runsData]) => {
      if (ignore) return;
      if (userData) {
        setUser(userData);
        setRiskProfile(userData.riskProfile || 'Balanced');
        setDailyDigest(userData.dailyDigestOptIn);
      }
      if (portfolioData) setPortfolio(portfolioData);
      if (liveCreds) {
        setIsConfigured(liveCreds.is_configured);
        setLiveBalanceUsdc(liveCreds.live_balance_usdc ?? null);
        setLastVerifiedAt(liveCreds.last_verified_at);
        setSignerAddress(liveCreds.signer_address || '');
        setSignatureType(liveCreds.signature_type ?? 0);
        if (liveCreds.polymarket_wallet_address) setProxyAddress(liveCreds.polymarket_wallet_address);
        if (liveCreds.clob_api_key_masked) setApiKey(liveCreds.clob_api_key_masked);
      }
      setExecutionState(stateData);
      setExecutionStateLoaded(true);

      if (sessionData) setSessionSetup(sessionData);
      if (opsData) {
        setSessionOperations(opsData);
        const prepared = opsData.find(o => o.state === 'PREPARED');
        if (prepared) setActivePreparedOperation(prepared);
      }
      setCopyPolicy(policyData);
      setPolicyLoaded(true);
      if (policyData) {
        setPolicySourceWallets(policyData.source_wallets.join('\n'));
        setPolicyCopyRatio(policyData.copy_ratio);
        setPolicyMaxOrderCash(policyData.limits.max_order_cash);
        setPolicyMaxTotalExposure(policyData.limits.max_total_exposure);
        setPolicyMaxTokenExposure(policyData.limits.max_token_exposure);
        setPolicyMaxDailyLoss(policyData.limits.max_daily_loss);
        setPolicyMaxOpenOrders(String(policyData.limits.max_open_orders));
        setPolicyMaxSlippageBps(policyData.limits.max_slippage_bps);
        setPolicyMaxFeeBps(policyData.limits.max_fee_bps);
        setPolicyMaxQuoteAgeMs(String(policyData.limits.max_quote_age_ms));
        setPolicyMaxSourceAgeMs(String(policyData.limits.max_source_age_ms));
      } else {
        setPolicySourceWallets('');
        setPolicyCopyRatio('');
        setPolicyMaxOrderCash('');
        setPolicyMaxTotalExposure('');
        setPolicyMaxTokenExposure('');
        setPolicyMaxDailyLoss('');
        setPolicyMaxOpenOrders('');
        setPolicyMaxSlippageBps('');
        setPolicyMaxFeeBps('');
        setPolicyMaxQuoteAgeMs('');
        setPolicyMaxSourceAgeMs('');
      }
      setPaperRuns(runsData);
    });

    return () => { ignore = true; };
  }, [session]);

  useEffect(() => {
    const onExpired = () => {
      clearPrivateState();
    };
    if (typeof window !== 'undefined') {
      window.addEventListener('baleen:session-expired', onExpired);
      return () => window.removeEventListener('baleen:session-expired', onExpired);
    }
  }, []);

  async function handleSavePreferences() {
    if (!session?.user?.id) return;
    setSavingPreferences(true);
    setSavedPreferencesSuccess(false);
    const updated = await updateUserSettings(session.user.id, {
      riskProfile,
      dailyDigestOptIn: dailyDigest
    });
    if (updated) {
      setUser(updated);
      setSavedPreferencesSuccess(true);
      setTimeout(() => setSavedPreferencesSuccess(false), 3000);
    }
    setSavingPreferences(false);
  }

  async function handleSaveCredentials() {
    if (!proxyAddress.trim() || !apiKey.trim() || !apiSecret.trim() || !passphrase.trim()) {
      setCredentialError("All four fields (Deposit Proxy Wallet Address, CLOB API Key, Secret, and Passphrase) are required.");
      return;
    }
    setSavingCredentials(true);
    setCredentialError(null);
    setCredentialsSavedSuccess(false);
    try {
      const res = await saveLiveCredentials({
        userId: session?.user?.id,
        polymarketWalletAddress: proxyAddress.trim(),
        clobApiKey: apiKey.trim(),
        clobApiSecret: apiSecret.trim(),
        clobApiPassphrase: passphrase.trim(),
        signerAddress: signerAddress.trim() || undefined,
        signatureType
      });
      if (res) {
        setIsConfigured(res.is_configured);
        setCredentialsSavedSuccess(true);
        setTimeout(() => setCredentialsSavedSuccess(false), 4000);
        await loadSessionData();
        await refreshExecutionState();
      }
    } catch (err: unknown) {
      setCredentialError(err instanceof Error ? err.message : "Failed to save live trading credentials.");
    } finally {
      setSavingCredentials(false);
    }
  }

  async function handleTestConnection() {
    if (!proxyAddress.trim() || !signerAddress.trim()) {
      setCredentialError("Deposit proxy wallet address and order signer address are required to test CLOB reachability.");
      return;
    }
    setTestingConnection(true);
    setCredentialError(null);
    setTestResult(null);
    try {
      const res = await testLiveConnection({
        userId: session?.user?.id,
        polymarketWalletAddress: proxyAddress.trim() || undefined,
        clobApiKey: apiKey.trim() || undefined,
        clobApiSecret: apiSecret.trim() || undefined,
        clobApiPassphrase: passphrase.trim() || undefined,
        signerAddress: signerAddress.trim() || undefined,
        signatureType
      });
      setTestResult(res);
      if (res.balance_usdc !== undefined) {
        setLiveBalanceUsdc(res.balance_usdc);
      }
      if (res.verified_at) {
        setLastVerifiedAt(res.verified_at);
      }
    } catch (err: unknown) {
      setCredentialError(err instanceof Error ? err.message : "Connection test failed. Please verify your CLOB keys and Deposit Proxy Wallet Address.");
    } finally {
      setTestingConnection(false);
    }
  }

  // Session Handlers
  async function handlePrepareSession() {
    setSessionLoading(true);
    setSessionError(null);
    setSessionSuccess(null);
    try {
      const setup = await prepareSession();
      setSessionSetup(setup);
      setSessionSuccess('Deposit Wallet session key prepared on backend. Request and sign an owner authorization challenge to observe on-chain grant.');
      await loadSessionData();
    } catch (err: unknown) {
      setSessionError(err instanceof Error ? err.message : 'Failed to prepare signing session key');
    } finally {
      setSessionLoading(false);
    }
  }

  async function handleVerifySession() {
    setSessionLoading(true);
    setSessionError(null);
    setSessionSuccess(null);
    try {
      const setup = await verifySession();
      setSessionSetup(setup);
      setSessionSuccess('Session authorization grant verified on-chain. Note: Live execution activation remains gated.');
      await loadSessionData();
    } catch (err: unknown) {
      setSessionError(err instanceof Error ? err.message : 'CLOB session authorization is not verified on-chain');
    } finally {
      setSessionLoading(false);
    }
  }

  async function handleDisableSession() {
    setSessionLoading(true);
    setSessionError(null);
    setSessionSuccess(null);
    try {
      const res = await disableSession();
      setSessionSuccess(res.message);
      await loadSessionData();
      await refreshExecutionState();
    } catch (err: unknown) {
      setSessionError(err instanceof Error ? err.message : 'Failed to stop local signing');
    } finally {
      setSessionLoading(false);
    }
  }

  async function handlePrepareOperation(kind: 'AUTHORIZE' | 'REVOKE') {
    setPreparingOpKind(kind);
    setWalletApprovalError(null);
    setSessionError(null);
    try {
      const op = await prepareSessionOperation(kind);
      setActivePreparedOperation(op);
      await loadSessionData();
    } catch (err: unknown) {
      setWalletApprovalError(err instanceof Error ? err.message : 'Failed to prepare owner approval challenge');
    } finally {
      setPreparingOpKind(null);
    }
  }

  async function handleApproveOperation(op: SessionOperation) {
    setSigningOpId(op.id);
    setWalletApprovalError(null);
    setSessionSuccess(null);
    try {
      if (typeof window === 'undefined' || !(window as unknown as { ethereum?: unknown }).ethereum) {
        throw new Error('Owner wallet provider (EIP-1193) not detected. Please connect your Deposit Wallet owner (e.g. MetaMask).');
      }
      const provider = (window as unknown as { ethereum: { request: (args: { method: string; params?: unknown[] }) => Promise<unknown> } }).ethereum;
      const signature = await signSessionOperation(op, provider);
      const res = await submitSessionSignature(op.id, signature);
      setSessionSuccess(`Owner signature submitted to relayer for ${op.kind} (relayer status: ${res.state}). Refresh to observe on-chain confirmation.`);
      setActivePreparedOperation(null);
      await loadSessionData();
    } catch (err: unknown) {
      setWalletApprovalError(err instanceof Error ? err.message : 'Wallet approval failed.');
    } finally {
      setSigningOpId(null);
    }
  }

  async function handleInitializeAccount() {
    setInitLoading(true);
    setInitError(null);
    setInitSuccess(null);
    try {
      const res = await initializeLiveAccount();
      setInitResult(res);
      setInitSuccess(`Baseline established: confirmed starting cash $${res.startingCash} pUSD at block #${res.blockNumber}. Live execution remains disabled.`);
      await refreshExecutionState();
    } catch (err: unknown) {
      setInitError(err instanceof Error ? err.message : 'Live account initialization failed.');
    } finally {
      setInitLoading(false);
    }
  }

  async function handleSavePolicy() {
    setPolicySaving(true);
    setPolicyError(null);
    setPolicySuccess(null);

    const sources = policySourceWallets
      .split(/[\n,]+/)
      .map(s => s.trim().toLowerCase())
      .filter(Boolean);

    if (sources.length === 0) {
      setPolicyError('At least one source wallet address is required.');
      setPolicySaving(false);
      return;
    }
    if (sources.length > 20) {
      setPolicyError('At most 20 source wallets may be specified.');
      setPolicySaving(false);
      return;
    }
    if (new Set(sources).size !== sources.length) {
      setPolicyError('Source wallet addresses must be unique.');
      setPolicySaving(false);
      return;
    }
    if (sources.some(s => !/^0x[0-9a-f]{40}$/.test(s))) {
      setPolicyError('All source wallet addresses must be valid 0x addresses (40 hex characters).');
      setPolicySaving(false);
      return;
    }

    const isPositiveDecimal = (v: string) => {
      const s = v.trim();
      return /^\d+(\.\d+)?$/.test(s) && parseFloat(s) > 0 && isFinite(Number(s));
    };
    const isBpsDecimal = (v: string) => {
      const s = v.trim();
      return /^\d+(\.\d+)?$/.test(s) && parseFloat(s) >= 0 && parseFloat(s) <= 10000 && isFinite(Number(s));
    };
    const isStrictInt = (v: string, min: number, max: number) => {
      const s = v.trim();
      if (!/^\d+$/.test(s)) return false;
      const n = parseInt(s, 10);
      return n >= min && n <= max;
    };

    const copyRatioTrim = policyCopyRatio.trim();
    if (!/^\d+(\.\d+)?$/.test(copyRatioTrim) || parseFloat(copyRatioTrim) <= 0 || parseFloat(copyRatioTrim) > 1) {
      setPolicyError('Copy ratio must be a decimal greater than 0 and at most 1 (e.g. 0.10 copies 10% of source shares).');
      setPolicySaving(false);
      return;
    }

    if (!isPositiveDecimal(policyMaxOrderCash)) {
      setPolicyError('Max order cash must be a positive decimal limit in pUSD.');
      setPolicySaving(false);
      return;
    }

    if (!isPositiveDecimal(policyMaxTotalExposure)) {
      setPolicyError('Max total exposure must be a positive decimal limit in pUSD.');
      setPolicySaving(false);
      return;
    }

    if (!isPositiveDecimal(policyMaxTokenExposure)) {
      setPolicyError('Max token exposure must be a positive decimal limit in pUSD.');
      setPolicySaving(false);
      return;
    }

    if (!isPositiveDecimal(policyMaxDailyLoss)) {
      setPolicyError('Max daily loss must be a positive decimal limit in pUSD.');
      setPolicySaving(false);
      return;
    }

    if (!isStrictInt(policyMaxOpenOrders, 1, 100)) {
      setPolicyError('Max open orders must be an integer between 1 and 100.');
      setPolicySaving(false);
      return;
    }

    if (!isBpsDecimal(policyMaxSlippageBps)) {
      setPolicyError('Max slippage must be a decimal between 0 and 10,000 basis points (100 bps = 1%).');
      setPolicySaving(false);
      return;
    }

    if (!isBpsDecimal(policyMaxFeeBps)) {
      setPolicyError('Max fee bound must be a decimal between 0 and 10,000 basis points (100 bps = 1%).');
      setPolicySaving(false);
      return;
    }

    if (!isStrictInt(policyMaxQuoteAgeMs, 1, 60000)) {
      setPolicyError('Max quote age must be an integer between 1 and 60,000 ms.');
      setPolicySaving(false);
      return;
    }

    if (!isStrictInt(policyMaxSourceAgeMs, 1, 3600000)) {
      setPolicyError('Max source age must be an integer between 1 and 3,600,000 ms (source age includes Polygon confirmation delay).');
      setPolicySaving(false);
      return;
    }

    const req: CopyPolicyRequest = {
      source_wallets: sources,
      copy_ratio: copyRatioTrim,
      max_order_cash: policyMaxOrderCash.trim(),
      max_total_exposure: policyMaxTotalExposure.trim(),
      max_token_exposure: policyMaxTokenExposure.trim(),
      max_daily_loss: policyMaxDailyLoss.trim(),
      max_open_orders: parseInt(policyMaxOpenOrders.trim(), 10),
      max_slippage_bps: policyMaxSlippageBps.trim(),
      max_fee_bps: policyMaxFeeBps.trim(),
      max_quote_age_ms: parseInt(policyMaxQuoteAgeMs.trim(), 10),
      max_source_age_ms: parseInt(policyMaxSourceAgeMs.trim(), 10),
    };

    try {
      const saved = await saveCopyPolicy(req);
      setCopyPolicy(saved);
      setPolicySuccess(`Policy Revision #${saved.revision} saved. Live execution was stopped and pending orders requested for cancellation; reactivation is required. Saving is never an activation action.`);
      await refreshExecutionState();
    } catch (err: unknown) {
      setPolicyError(err instanceof Error ? err.message : 'Failed to save copy policy');
    } finally {
      setPolicySaving(false);
    }
  }

  async function handleViewTrades(runId: string) {
    if (!session?.user?.id) return;
    setLoadingTrades(true);
    setTradesModalRunId(runId);
    try {
      const trades = await fetchPaperRunTrades(session.user.id, runId);
      setSelectedRunTrades(trades);
    } catch (err: unknown) {
      setPaperRunsError(err instanceof Error ? err.message : 'Failed to load trades for run');
    } finally {
      setLoadingTrades(false);
    }
  }

  function handleExportTradesJson(runId: string, trades: PaperRunTrade[]) {
    const jsonStr = JSON.stringify(trades, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `baleen_paper_run_${runId}_trades.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const profiles = [
    { id: 'Conservative', desc: 'Lower position sizing (5% max), strictest slippage tolerances. Prioritizes capital preservation.' },
    { id: 'Balanced', desc: 'Pure proportional sleeve sizing scaled dynamically by whale position fractions.' },
    { id: 'Aggressive', desc: 'Higher leverage allocation, looser slippage window. Maximizes upside volatility.' }
  ] as const;

  const showExactValue = (value?: string | null, suffix = '') =>
    value == null || value.trim() === '' ? 'Unavailable' : `${value}${suffix}`;

  const formatUsd = (val?: number | null) =>
    val == null ? 'Unavailable' : `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  if (sessionStatus === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-[#00D09C] border-t-transparent animate-spin" />
          <span className="text-xs font-mono text-[#8E8F99]">Loading account settings...</span>
        </div>
      </div>
    );
  }

  if (sessionStatus === 'unauthenticated') {
    return (
      <div className="min-h-screen bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-md p-8 rounded-2xl bg-white dark:bg-[#16171B] border border-black/10 dark:border-white/10 shadow-xl text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 flex items-center justify-center text-rose-600 dark:text-rose-400">
            <Lock size={24} />
          </div>
          <h2 className="text-lg font-bold">Authentication Required</h2>
          <p className="text-xs text-slate-500 dark:text-[#8E8F99]">
            Please sign in to view and manage your account settings, trading preferences, and live credentials.
          </p>
          <Link
            href="/auth/login"
            className="inline-block w-full py-3 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-all cursor-pointer"
          >
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white p-6 lg:p-12 selection:bg-[#00D09C] selection:text-black transition-colors duration-150">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <BrandLogo size="sm" />
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-[#8E8F99] hover:text-slate-950 dark:hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back to Dashboard
            </Link>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            className="w-9 h-9 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all cursor-pointer shadow-2xs"
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          >
            {theme === 'light' ? <Moon size={15} /> : <Sun size={15} className="text-amber-400" />}
          </button>
        </div>
        
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white mb-2">Engine Settings</h1>
          <p className="text-slate-600 dark:text-[#8E8F99] text-sm">
            Manage your paper trading balance, execution risk regime, Deposit Wallet session keys, and explicit copy policy.
          </p>
        </div>

        <div className="space-y-6">
          {/* Card 1: Owner L2 API Credentials */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-black/[0.06] dark:border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                  <Key size={18} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-950 dark:text-white flex items-center gap-2">
                    Polymarket CLOB L2 Credentials
                    {isConfigured && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-600 dark:text-[#00D09C] border border-emerald-200 dark:border-[#00D09C]/20 font-mono">
                        Configured
                      </span>
                    )}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                    Connect your Polymarket Layer 2 CLOB API credentials. These credentials are distinct from your owner private key (which Baleen never requests, stores, or displays).
                  </p>
                </div>
              </div>

              {/* Server Live Execution Gated Status */}
              <div className="flex items-center gap-2 self-end sm:self-auto px-3 py-1.5 rounded-full bg-slate-100 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10">
                <div className="w-2 h-2 rounded-full bg-amber-500" />
                <div className="text-[11px] font-bold text-slate-800 dark:text-white">
                  Live Trading · Unavailable (Gated)
                </div>
              </div>
            </div>

            {credentialError && (
              <div role="alert" aria-live="polite" className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-xs text-rose-700 dark:text-rose-400 flex items-start gap-2.5">
                <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                <span>{credentialError}</span>
              </div>
            )}

            {credentialsSavedSuccess && (
              <div role="status" aria-live="polite" className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-[#00D09C]/10 border border-emerald-200 dark:border-[#00D09C]/20 text-xs text-emerald-700 dark:text-[#00D09C] flex items-center gap-2.5">
                <CheckCircle2 size={15} />
                <span>L2 credentials securely saved. Test reachability to verify private API transport.</span>
              </div>
            )}

            {testResult && (
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-white">
                    <ShieldCheck size={16} className="text-[#00D09C]" />
                    <span>
                      CLOB Reachability: {testResult.connected ? 'Verified' : 'Unavailable'} · Credentials: {testResult.credentials_verified ? 'Verified' : 'Unverified'} · Live execution: Unavailable (Gated)
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500 dark:text-[#8E8F99]">
                    {formatUtcDate(testResult.verified_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-xs text-slate-500 dark:text-[#8E8F99]">Reported pUSD Collateral Balance:</span>
                  <span className="text-lg font-bold font-mono text-[#00D09C]">
                    {testResult.balance_usdc === null ? 'Unavailable' : `${formatUsd(testResult.balance_usdc)} pUSD`}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-[#8E8F99]">{testResult.status_message}</p>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label htmlFor="proxy-wallet-address" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                  Deposit Proxy Wallet Address (0x...)
                </label>
                <input
                  id="proxy-wallet-address"
                  type="text"
                  placeholder="0x1234...abcd"
                  aria-label="Deposit Proxy Wallet Address"
                  value={proxyAddress}
                  onChange={(e) => setProxyAddress(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                />
                <p className="text-[10px] text-slate-500 dark:text-[#8E8F99] mt-1">
                  Your deposit proxy wallet shown in Polymarket Profile &gt; Deposit &gt; Copy Address.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="signer-address" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Order Signer Address (0x...)
                  </label>
                  <input
                    id="signer-address"
                    type="text"
                    placeholder="0x1234...abcd"
                    aria-label="Order Signer Address"
                    value={signerAddress}
                    onChange={(e) => setSignerAddress(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                  <p className="text-[10px] text-slate-500 dark:text-[#8E8F99] mt-1">
                    The wallet authorized to sign CLOB orders; it may differ from the deposit proxy wallet.
                  </p>
                </div>
                <div>
                  <label htmlFor="signature-type" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Wallet Signature Type
                  </label>
                  <select
                    id="signature-type"
                    aria-label="Wallet Signature Type"
                    value={signatureType}
                    onChange={(e) => setSignatureType(Number(e.target.value))}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  >
                    <option value={0}>0 · EOA</option>
                    <option value={1}>1 · POLY_PROXY</option>
                    <option value={2}>2 · POLY_GNOSIS_SAFE</option>
                    <option value={3}>3 · POLY_CREATE2</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label htmlFor="clob-api-key" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    CLOB API Key
                  </label>
                  <input
                    id="clob-api-key"
                    type="text"
                    placeholder="API Key"
                    aria-label="CLOB API Key"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>

                <div>
                  <label htmlFor="clob-api-secret" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    CLOB API Secret
                  </label>
                  <input
                    id="clob-api-secret"
                    type="password"
                    placeholder="••••••••••••••••"
                    aria-label="CLOB API Secret"
                    value={apiSecret}
                    onChange={(e) => setApiSecret(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>

                <div>
                  <label htmlFor="clob-passphrase" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    CLOB Passphrase
                  </label>
                  <input
                    id="clob-passphrase"
                    type="password"
                    placeholder="••••••••"
                    aria-label="CLOB Passphrase"
                    value={passphrase}
                    onChange={(e) => setPassphrase(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
              <div className="text-[11px] text-slate-500 dark:text-[#8E8F99] flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5">
                  <Lock size={12} />
                  <span>Credentials are encrypted server-side; owner private keys are never accepted or stored.</span>
                </div>
                {(lastVerifiedAt || liveBalanceUsdc != null) && (
                  <div className="text-[10px] text-slate-400">
                    Last Verified: {formatUtcDate(lastVerifiedAt)} · Balance: {formatUsd(liveBalanceUsdc)} pUSD
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testingConnection || (!proxyAddress && !isConfigured)}
                  className="px-4 py-2.5 rounded-full bg-slate-100 dark:bg-[#1C1D22] hover:bg-slate-200 dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-xs font-bold text-slate-800 dark:text-white transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw size={13} className={testingConnection ? 'animate-spin' : ''} />
                  <span>{testingConnection ? 'Pinging CLOB...' : 'Test Connection & Fetch L2 Balance'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleSaveCredentials}
                  disabled={savingCredentials}
                  className="px-5 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Save size={13} />
                  <span>{savingCredentials ? 'Saving...' : 'Save Credentials'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Card 2: Deposit Wallet Signing Session Panel */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-black/[0.06] dark:border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                  <Shield size={18} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-950 dark:text-white flex items-center gap-2">
                    Deposit Wallet Signing Session
                    {sessionSetup?.status === 'authorization_observed' && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-600 dark:text-[#00D09C] border border-emerald-200 dark:border-[#00D09C]/20 font-mono">
                        Grant Observed
                      </span>
                    )}
                    {sessionSetup?.status === 'locally_disabled' && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20 font-mono">
                        Locally Disabled
                      </span>
                    )}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                    Account-bound session signer with CLOB-only order scope. Creating a key does not authorize it on-chain; owner approval challenge is required.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end sm:self-auto">
                <button
                  type="button"
                  onClick={loadSessionData}
                  disabled={sessionLoading}
                  className="px-3.5 py-1.5 rounded-full bg-slate-100 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-bold text-slate-800 dark:text-white flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                  aria-label="Refresh signing session status"
                >
                  <RefreshCw size={12} className={sessionLoading ? 'animate-spin' : ''} />
                  <span>{sessionLoading ? 'Refreshing...' : 'Refresh session'}</span>
                </button>
              </div>
            </div>

            {sessionError && (
              <div role="alert" aria-live="polite" className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-xs text-rose-700 dark:text-rose-400 flex items-start gap-2.5">
                <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                <span>{sessionError}</span>
              </div>
            )}

            {sessionSuccess && (
              <div role="status" aria-live="polite" className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-[#00D09C]/10 border border-emerald-200 dark:border-[#00D09C]/20 text-xs text-emerald-700 dark:text-[#00D09C] flex items-center gap-2.5">
                <CheckCircle2 size={15} />
                <span>{sessionSuccess}</span>
              </div>
            )}

            {/* Explanatory Invariants Box */}
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5 space-y-2.5 text-xs text-slate-600 dark:text-[#8E8F99]">
              <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-white">
                <HelpCircle size={15} className="text-indigo-500 shrink-0" />
                <span>Session Security Invariants &amp; Warnings Explained:</span>
              </div>
              <ul className="space-y-2 text-xs pl-1">
                <li className="flex items-start gap-2">
                  <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold shrink-0">1. Key Creation ≠ Authorization:</span>
                  <span>Creating an encrypted session key only prepares the keypair on the backend; it does <em>not</em> authorize it on Polymarket until granted on-chain by the wallet owner.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-mono text-[#00D09C] font-bold shrink-0">2. Grant Observed ≠ Live Trading:</span>
                  <span><code className="font-mono px-1 py-0.5 rounded bg-slate-200 dark:bg-white/10 text-slate-900 dark:text-white">authorization_observed</code> means a previous check detected the owner grant, but live execution remains safety-gated on the server (<code className="font-mono text-[11px]">LIVE_EXECUTION_ENABLED=false</code>).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-mono text-amber-600 dark:text-amber-400 font-bold shrink-0">3. Locally Disabled ≠ On-chain Revoked:</span>
                  <span><code className="font-mono px-1 py-0.5 rounded bg-slate-200 dark:bg-white/10 text-slate-900 dark:text-white">locally_disabled</code> ceases local signing on the Baleen server, but does <em>not</em> prove on-chain revocation; owner revocation must be signed and submitted to the exchange relayer to cancel smart contract permissions.</span>
                </li>
              </ul>
            </div>

            {/* Session Metadata Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                ['Deposit Wallet', showExactValue(sessionSetup?.walletAddress)],
                ['Session Address', showExactValue(sessionSetup?.sessionAddress)],
                ['Scope', showExactValue(sessionSetup?.scope || 'CLOB')],
                ['Status', showExactValue(sessionSetup?.status)],
                ['Verified at (UTC)', formatUtcDate(sessionSetup?.verifiedAt)],
                ['Valid until (UTC)', formatUtcDate(sessionSetup?.validUntil)],
                ['Revoked at (UTC)', formatUtcDate(sessionSetup?.revokedAt)],
                ['Live Execution Readiness', 'Unavailable (Gated)'],
              ].map(([label, value]) => (
                <div key={label} className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5">
                  <div className="text-[10px] uppercase tracking-wide text-slate-500 dark:text-[#8E8F99]">{label}</div>
                  <div className="mt-1 text-xs font-mono font-semibold text-slate-900 dark:text-white break-all">{value}</div>
                </div>
              ))}
            </div>

            {/* Session Setup Action Buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-1 border-t border-black/[0.06] dark:border-white/5">
              {(!sessionSetup || sessionSetup.status === 'not_configured') ? (
                <button
                  type="button"
                  onClick={handlePrepareSession}
                  disabled={sessionLoading}
                  className="px-5 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-xs font-bold transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  <Key size={13} />
                  <span>{sessionLoading ? 'Preparing session key...' : 'Prepare Session Key'}</span>
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={handleVerifySession}
                    disabled={sessionLoading}
                    className="px-4 py-2.5 rounded-full bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-100 dark:hover:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20 text-xs font-bold transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    <ShieldCheck size={14} />
                    <span>{sessionLoading ? 'Verifying grant...' : 'Verify Actual Owner Grant'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleDisableSession}
                    disabled={sessionLoading}
                    className="px-4 py-2.5 rounded-full bg-rose-50 dark:bg-rose-500/10 hover:bg-rose-100 dark:hover:bg-rose-500/20 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20 text-xs font-bold transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    <StopCircle size={14} />
                    <span>Stop Local Signing</span>
                  </button>
                </>
              )}
            </div>

            {/* Owner EIP-712 Approvals Workflow */}
            <div className="pt-4 border-t border-black/[0.06] dark:border-white/5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Owner Approvals &amp; Revocations (EIP-712)
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                    Prepare a fixed-purpose challenge, review contract call and expiry, then approve with your connected EIP-1193 owner wallet.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handlePrepareOperation('AUTHORIZE')}
                    disabled={preparingOpKind !== null || !sessionSetup?.sessionAddress}
                    className="px-3.5 py-2 rounded-full bg-slate-100 dark:bg-[#1C1D22] hover:bg-slate-200 dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-xs font-bold text-slate-800 dark:text-white transition-all cursor-pointer disabled:opacity-50"
                  >
                    {preparingOpKind === 'AUTHORIZE' ? 'Preparing...' : 'Prepare Authorization'}
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePrepareOperation('REVOKE')}
                    disabled={preparingOpKind !== null || !sessionSetup?.sessionAddress}
                    className="px-3.5 py-2 rounded-full bg-slate-100 dark:bg-[#1C1D22] hover:bg-slate-200 dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-xs font-bold text-slate-800 dark:text-white transition-all cursor-pointer disabled:opacity-50"
                  >
                    {preparingOpKind === 'REVOKE' ? 'Preparing...' : 'Prepare Revocation'}
                  </button>
                </div>
              </div>

              {walletApprovalError && (
                <div role="alert" aria-live="polite" className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-xs text-rose-700 dark:text-rose-400 flex items-start gap-2.5">
                  <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                  <span>{walletApprovalError}</span>
                </div>
              )}

              {/* Active Prepared Challenge Card */}
              {activePreparedOperation && (
                <div className="p-4 rounded-2xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800/40 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-900 dark:text-indigo-200">
                      Prepared Challenge for Review: {activePreparedOperation.kind}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300">
                      State: {activePreparedOperation.state}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                    <div className="p-2.5 rounded-xl bg-white/80 dark:bg-[#16171B]/80 border border-indigo-100 dark:border-indigo-900/20">
                      <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Owner Address</div>
                      <div className="text-slate-900 dark:text-white break-all">{activePreparedOperation.ownerAddress}</div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-white/80 dark:bg-[#16171B]/80 border border-indigo-100 dark:border-indigo-900/20">
                      <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Deposit Wallet</div>
                      <div className="text-slate-900 dark:text-white break-all">{activePreparedOperation.walletAddress}</div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-white/80 dark:bg-[#16171B]/80 border border-indigo-100 dark:border-indigo-900/20">
                      <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Session Address</div>
                      <div className="text-slate-900 dark:text-white break-all">{activePreparedOperation.sessionAddress}</div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-white/80 dark:bg-[#16171B]/80 border border-indigo-100 dark:border-indigo-900/20">
                      <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Scopes &amp; Nonce</div>
                      <div className="text-slate-900 dark:text-white break-all">
                        Scopes: {activePreparedOperation.scopes.join(', ') || 'None'} · Nonce: {activePreparedOperation.typedData?.message?.nonce || 'Unavailable'}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-white/80 dark:bg-[#16171B]/80 border border-indigo-100 dark:border-indigo-900/20">
                      <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Signing Deadline (UTC)</div>
                      <div className="text-slate-900 dark:text-white">{formatUtcDate(activePreparedOperation.deadline)}</div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-white/80 dark:bg-[#16171B]/80 border border-indigo-100 dark:border-indigo-900/20">
                      <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Valid Until (UTC)</div>
                      <div className="text-slate-900 dark:text-white">{formatUtcDate(activePreparedOperation.validUntil)}</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2.5 pt-1">
                    <button
                      type="button"
                      onClick={() => setActivePreparedOperation(null)}
                      className="px-3.5 py-1.5 rounded-full border border-black/10 dark:border-white/10 text-xs font-semibold text-slate-700 dark:text-white hover:bg-slate-100 dark:hover:bg-[#1C1D22] transition-colors cursor-pointer"
                    >
                      Dismiss
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApproveOperation(activePreparedOperation)}
                      disabled={signingOpId !== null}
                      className="px-5 py-2 rounded-full bg-[#00D09C] hover:bg-[#00b084] text-black text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      <Check size={14} />
                      <span>{signingOpId ? 'Signing with Wallet...' : 'Approve & Sign with Connected Wallet'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Operations History List */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-slate-700 dark:text-[#8E8F99]">Recent Owner Operations</div>
                  <button
                    type="button"
                    onClick={loadSessionData}
                    disabled={sessionLoading}
                    className="px-2.5 py-1 rounded-full bg-slate-100 dark:bg-[#1C1D22] hover:bg-slate-200 dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-[11px] font-bold text-slate-800 dark:text-white flex items-center gap-1 cursor-pointer disabled:opacity-50"
                    aria-label="Refresh session operations"
                  >
                    <RefreshCw size={10} className={sessionLoading ? 'animate-spin' : ''} />
                    <span>Refresh Operations</span>
                  </button>
                </div>
                {sessionOperations.length === 0 ? (
                  <p className="text-xs text-slate-500 dark:text-[#8E8F99]">No session operations recorded.</p>
                ) : (
                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {sessionOperations.map((op) => {
                      const isUnresolved = ['PENDING', 'UNKNOWN', 'SUBMITTING'].includes(op.state);
                      return (
                        <div key={op.id} className="p-3 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5 space-y-1">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                            <span className="text-xs font-mono font-bold text-slate-900 dark:text-white">
                              {op.kind} · <span className="text-[11px] font-normal text-slate-500">ID: {op.id.slice(0, 8)}...</span>
                            </span>
                            <div className="flex items-center gap-2">
                              {op.state === 'PREPARED' && (!activePreparedOperation || activePreparedOperation.id !== op.id) && (
                                <button
                                  type="button"
                                  onClick={() => setActivePreparedOperation(op)}
                                  className="px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-100 dark:hover:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20 text-[10px] font-bold transition-all cursor-pointer"
                                >
                                  Review Challenge
                                </button>
                              )}
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                op.state === 'GRANT_OBSERVED' 
                                  ? 'bg-emerald-100 dark:bg-[#00D09C]/10 text-emerald-700 dark:text-[#00D09C]' 
                                  : isUnresolved
                                  ? 'bg-amber-100 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300'
                                  : 'bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-slate-300'
                              }`}>
                                {op.state}
                              </span>
                            </div>
                          </div>
                          <div className="text-[11px] font-mono text-slate-600 dark:text-[#8E8F99] flex flex-wrap gap-x-4">
                            <span>Deadline: {formatUtcDate(op.deadline)}</span>
                            {op.transactionId && <span>Tx ID: {op.transactionId}</span>}
                          </div>
                          {isUnresolved && (
                            <div className="text-[10px] text-amber-700 dark:text-amber-400">
                              ⚠️ Submission unresolved ({op.state}). Check status with your relayer/RPC; do not auto-resubmit.
                            </div>
                          )}
                          {op.kind === 'REVOKE' && op.state === 'PENDING' && (
                            <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">
                              Note: Revocation is pending relayer confirmation; not yet confirmed revoked on-chain.
                            </div>
                          )}
                          {op.state === 'GRANT_OBSERVED' && (
                            <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">
                              Note: Grant observed on-chain; does not enable live trading.
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Baseline Initialization Section */}
            <div className="pt-4 border-t border-black/[0.06] dark:border-white/5 space-y-3">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                  Read &amp; Initialize Wallet Account
                </h3>
                <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                  After on-chain grant verification, establish an immutable live account baseline with live execution disabled. Requires verified session grant, complete RPC wallet history, no existing venue orders, and no positions needing cost-basis import.
                </p>
              </div>

              {initError && (
                <div role="alert" aria-live="polite" className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-xs text-rose-700 dark:text-rose-400 flex items-start gap-2.5">
                  <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                  <span>{initError}</span>
                </div>
              )}

              {initSuccess && (
                <div role="status" aria-live="polite" className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-[#00D09C]/10 border border-emerald-200 dark:border-[#00D09C]/20 text-xs text-emerald-700 dark:text-[#00D09C] flex items-center gap-2.5">
                  <CheckCircle2 size={15} />
                  <span>{initSuccess}</span>
                </div>
              )}

              {sessionSetup?.status !== 'authorization_observed' && (
                <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-xs text-amber-800 dark:text-amber-300">
                  ⚠️ Grant verification required: You must verify your Deposit Wallet session authorization grant on-chain before initializing an account baseline.
                </div>
              )}

              {initResult && (
                <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5 grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <div className="text-[10px] uppercase text-slate-500 dark:text-[#8E8F99]">Confirmed Starting Cash</div>
                    <div className="text-sm font-bold font-mono text-[#00D09C] mt-0.5">
                      ${initResult.startingCash} pUSD
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase text-slate-500 dark:text-[#8E8F99]">Baseline Block</div>
                    <div className="text-sm font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                      #{initResult.blockNumber}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase text-slate-500 dark:text-[#8E8F99]">Execution Readiness</div>
                    <div className="text-sm font-bold font-mono text-amber-500 mt-0.5">
                      Unavailable (Gated)
                    </div>
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={handleInitializeAccount}
                disabled={initLoading || sessionLoading || sessionSetup?.status !== 'authorization_observed'}
                className="px-5 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-xs font-bold transition-all shadow-sm flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <Layers size={14} />
                <span>{initLoading ? 'Reading & Initializing Account...' : 'Read and Initialize Wallet Account'}</span>
              </button>
            </div>
          </div>

          {/* Card 3: Explicit Copy Policy & Deterministic Risk Limits */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-black/[0.06] dark:border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                  <FileSpreadsheet size={18} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-950 dark:text-white flex items-center gap-2">
                    Live Copy Policy &amp; Risk Limits
                    {copyPolicy && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20 font-mono">
                        Revision #{copyPolicy.revision}
                      </span>
                    )}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                    Configure strictly enforced risk limits for live execution. Unset policy renders an empty form. Saving policy stops execution and requests cancellation of pending orders; reactivation is required.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end sm:self-auto">
                <button
                  type="button"
                  onClick={loadPolicyData}
                  disabled={policyLoading}
                  className="px-3.5 py-1.5 rounded-full bg-slate-100 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-bold text-slate-800 dark:text-white flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                  aria-label="Refresh copy policy"
                >
                  <RefreshCw size={12} className={policyLoading ? 'animate-spin' : ''} />
                  <span>{policyLoading ? 'Refreshing...' : 'Refresh policy'}</span>
                </button>
              </div>
            </div>

            {policyLoaded && copyPolicy === null && (
              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5 text-xs text-slate-600 dark:text-[#8E8F99]">
                ℹ️ No copy policy is currently configured. Complete all required fields below to establish your live copy policy.
              </div>
            )}

            {copyPolicy && (
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900 dark:text-white">
                    Confirmed Policy Revision #{copyPolicy.revision} Limits
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20">
                    Active on Server
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                  <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.04] dark:border-white/5">
                    <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Copy Ratio</div>
                    <div className="text-slate-900 dark:text-white font-semibold">
                      {copyPolicy.copy_ratio} ({(parseFloat(copyPolicy.copy_ratio) * 100).toFixed(0)}%)
                    </div>
                  </div>
                  <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.04] dark:border-white/5">
                    <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Max Order Cash</div>
                    <div className="text-slate-900 dark:text-white font-semibold">${copyPolicy.limits.max_order_cash} pUSD</div>
                  </div>
                  <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.04] dark:border-white/5">
                    <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Max Total Exposure</div>
                    <div className="text-slate-900 dark:text-white font-semibold">${copyPolicy.limits.max_total_exposure} pUSD</div>
                  </div>
                  <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.04] dark:border-white/5">
                    <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Max Token Exposure</div>
                    <div className="text-slate-900 dark:text-white font-semibold">${copyPolicy.limits.max_token_exposure} pUSD</div>
                  </div>
                  <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.04] dark:border-white/5">
                    <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Max Daily Loss</div>
                    <div className="text-slate-900 dark:text-white font-semibold">${copyPolicy.limits.max_daily_loss} pUSD</div>
                  </div>
                  <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.04] dark:border-white/5">
                    <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Max Open Orders</div>
                    <div className="text-slate-900 dark:text-white font-semibold">{copyPolicy.limits.max_open_orders}</div>
                  </div>
                  <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.04] dark:border-white/5">
                    <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Max Slippage / Fee</div>
                    <div className="text-slate-900 dark:text-white font-semibold">
                      {copyPolicy.limits.max_slippage_bps} bps / {copyPolicy.limits.max_fee_bps} bps
                    </div>
                  </div>
                  <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.04] dark:border-white/5">
                    <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">Max Quote / Source Age</div>
                    <div className="text-slate-900 dark:text-white font-semibold">
                      {copyPolicy.limits.max_quote_age_ms} ms / {copyPolicy.limits.max_source_age_ms} ms
                    </div>
                  </div>
                </div>
                <div className="text-[11px] font-mono text-slate-500 dark:text-[#8E8F99]">
                  Sources ({copyPolicy.source_wallets.length}): {copyPolicy.source_wallets.join(', ')}
                </div>
              </div>
            )}

            {policyError && (
              <div role="alert" aria-live="polite" className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-xs text-rose-700 dark:text-rose-400 flex items-start gap-2.5">
                <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                <span>{policyError}</span>
              </div>
            )}

            {policySuccess && (
              <div role="status" aria-live="polite" className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-[#00D09C]/10 border border-emerald-200 dark:border-[#00D09C]/20 text-xs text-emerald-700 dark:text-[#00D09C] flex items-center gap-2.5">
                <CheckCircle2 size={15} />
                <span>{policySuccess}</span>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label htmlFor="policy-source-wallets" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                  Source Wallet Addresses (1–20 unique 0x addresses, comma or newline separated)
                </label>
                <textarea
                  id="policy-source-wallets"
                  rows={3}
                  placeholder="0x1234...5678&#10;0xabcd...ef01"
                  aria-label="Source Wallet Addresses"
                  value={policySourceWallets}
                  onChange={(e) => setPolicySourceWallets(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="policy-copy-ratio" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Copy Ratio (0.01 to 1.00)
                  </label>
                  <input
                    id="policy-copy-ratio"
                    type="text"
                    placeholder="0.10"
                    aria-label="Copy Ratio"
                    value={policyCopyRatio}
                    onChange={(e) => setPolicyCopyRatio(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                  <p className="text-[10px] text-slate-500 dark:text-[#8E8F99] mt-1">
                    Decimal greater than 0 and at most 1. Example: 0.10 copies 10% of source shares.
                  </p>
                </div>
                <div>
                  <label htmlFor="policy-max-open-orders" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Max Open Orders (1–100)
                  </label>
                  <input
                    id="policy-max-open-orders"
                    type="number"
                    min={1}
                    max={100}
                    aria-label="Max Open Orders"
                    value={policyMaxOpenOrders}
                    onChange={(e) => setPolicyMaxOpenOrders(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label htmlFor="policy-max-order-cash" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Max Order Cash (pUSD)
                  </label>
                  <input
                    id="policy-max-order-cash"
                    type="text"
                    placeholder="100.00"
                    aria-label="Max Order Cash"
                    value={policyMaxOrderCash}
                    onChange={(e) => setPolicyMaxOrderCash(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
                <div>
                  <label htmlFor="policy-max-total-exposure" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Max Total Exposure (pUSD)
                  </label>
                  <input
                    id="policy-max-total-exposure"
                    type="text"
                    placeholder="1000.00"
                    aria-label="Max Total Exposure"
                    value={policyMaxTotalExposure}
                    onChange={(e) => setPolicyMaxTotalExposure(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
                <div>
                  <label htmlFor="policy-max-token-exposure" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Max Token Exposure (pUSD)
                  </label>
                  <input
                    id="policy-max-token-exposure"
                    type="text"
                    placeholder="500.00"
                    aria-label="Max Token Exposure"
                    value={policyMaxTokenExposure}
                    onChange={(e) => setPolicyMaxTokenExposure(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
                <div>
                  <label htmlFor="policy-max-daily-loss" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Max Daily Loss (pUSD)
                  </label>
                  <input
                    id="policy-max-daily-loss"
                    type="text"
                    placeholder="50.00"
                    aria-label="Max Daily Loss"
                    value={policyMaxDailyLoss}
                    onChange={(e) => setPolicyMaxDailyLoss(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="policy-max-slippage-bps" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Max Slippage (basis points: 100 bps = 1%)
                  </label>
                  <input
                    id="policy-max-slippage-bps"
                    type="text"
                    placeholder="100"
                    aria-label="Max Slippage in basis points"
                    value={policyMaxSlippageBps}
                    onChange={(e) => setPolicyMaxSlippageBps(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
                <div>
                  <label htmlFor="policy-max-fee-bps" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Max Fee Bound (basis points: 100 bps = 1%)
                  </label>
                  <input
                    id="policy-max-fee-bps"
                    type="text"
                    placeholder="100"
                    aria-label="Max Fee Bound in basis points"
                    value={policyMaxFeeBps}
                    onChange={(e) => setPolicyMaxFeeBps(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="policy-max-quote-age-ms" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Max Quote Age (milliseconds, 1–60,000 ms)
                  </label>
                  <input
                    id="policy-max-quote-age-ms"
                    type="number"
                    min={1}
                    max={60000}
                    aria-label="Max Quote Age in milliseconds"
                    value={policyMaxQuoteAgeMs}
                    onChange={(e) => setPolicyMaxQuoteAgeMs(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
                <div>
                  <label htmlFor="policy-max-source-age-ms" className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    Max Source Age (milliseconds, 1–3,600,000 ms)
                  </label>
                  <input
                    id="policy-max-source-age-ms"
                    type="number"
                    min={1}
                    max={3600000}
                    aria-label="Max Source Age in milliseconds"
                    value={policyMaxSourceAgeMs}
                    onChange={(e) => setPolicyMaxSourceAgeMs(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                  <p className="text-[10px] text-slate-500 dark:text-[#8E8F99] mt-1">
                    Source age includes Polygon confirmation delay; setting this too low can exclude every confirmed event.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
              <div className="text-[11px] text-slate-500 dark:text-[#8E8F99]">
                Saving policy stops current live execution and requests cancellation of pending orders; reactivation is required.
              </div>

              <button
                type="button"
                onClick={handleSavePolicy}
                disabled={policySaving}
                className="px-6 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <Save size={13} />
                <span>{policySaving ? 'Saving policy...' : 'Save Copy Policy'}</span>
              </button>
            </div>
          </div>

          {/* Card 4: Read-only Reconciled Execution State */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-black/[0.06] dark:border-white/5 pb-4">
              <div>
                <h2 className="text-sm font-bold text-slate-950 dark:text-white">Read-only Execution State</h2>
                <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-1">
                  Persisted account reconciliation and order journal state. Viewing this does not enable live execution.
                </p>
              </div>
              <button
                type="button"
                onClick={refreshExecutionState}
                disabled={refreshingExecutionState}
                className="px-3.5 py-2 rounded-full bg-slate-100 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-bold text-slate-800 dark:text-white flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <RefreshCw size={13} className={refreshingExecutionState ? 'animate-spin' : ''} />
                <span>{refreshingExecutionState ? 'Refreshing...' : 'Refresh state'}</span>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                ['Account state', executionState?.status === 'available' ? 'Available' : 'Unavailable'],
                ['Live execution readiness', 'Unavailable (Gated)'],
                ['Reconciliation status', executionState?.reconciliation?.status === 'WAITING' 
                  ? 'WAITING (Confirmation pending; submissions paused)' 
                  : executionState?.reconciliation?.status === 'BLOCKED'
                  ? 'BLOCKED (Discrepancy detected; live halted)'
                  : (executionState?.reconciliation?.status ?? 'Unavailable')],
                ['Last account reconciliation', formatUtcDate(executionState?.reconciledAt)],
                ['Cash', showExactValue(executionState?.cash, executionState?.collateralCurrency ? ` ${executionState.collateralCurrency}` : '')],
                ['Reserved cash', showExactValue(executionState?.reservedCash, executionState?.collateralCurrency ? ` ${executionState.collateralCurrency}` : '')],
                ['Available cash', showExactValue(executionState?.availableCash, executionState?.collateralCurrency ? ` ${executionState.collateralCurrency}` : '')],
                ['Reconciliation completed', formatUtcDate(executionState?.reconciliation?.finishedAt)],
              ].map(([label, value]) => (
                <div key={label} className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5">
                  <div className="text-[10px] uppercase tracking-wide text-slate-500 dark:text-[#8E8F99]">{label}</div>
                  <div className="mt-1 text-xs font-mono font-semibold text-slate-900 dark:text-white break-all">{value}</div>
                </div>
              ))}
            </div>

            <div className="text-xs text-slate-600 dark:text-[#8E8F99]">
              Reconciliation detail: {showExactValue(executionState?.reconciliation?.detail ?? executionState?.reason)}
              {!executionStateLoaded && <span> · Loading state</span>}
            </div>

            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-900 dark:text-white">Persisted Order Intents</h3>
              {executionState?.orders == null ? (
                <p className="text-xs text-slate-500 dark:text-[#8E8F99]">Unavailable</p>
              ) : executionState.orders.length === 0 ? (
                <p className="text-xs text-slate-500 dark:text-[#8E8F99]">No persisted order intents.</p>
              ) : (
                <div className="space-y-2">
                  {executionState.orders.map((order, index) => (
                    <div key={order.id ?? `${order.tokenId ?? 'order'}-${index}`} className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5">
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                        <div className="min-w-0 space-y-1">
                          <div className="text-xs font-mono text-slate-900 dark:text-white break-all">
                            Token: {showExactValue(order.tokenId)} · Side: {showExactValue(order.side)}
                          </div>
                          <div className="text-[11px] font-mono text-slate-600 dark:text-[#8E8F99]">
                            Quantity: {showExactValue(order.quantity)} · Filled: {showExactValue(order.filledQuantity)} · Limit: {showExactValue(order.limitPrice)}
                          </div>
                        </div>
                        <span className={`shrink-0 text-[10px] font-bold px-2 py-1 rounded-full ${order.cancelRequestedAt && getLiveOrderStateLabel(order) === 'Pending cancellation' ? 'bg-amber-100 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300' : 'bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-slate-300'}`}>
                          {getLiveOrderStateLabel(order)}
                        </span>
                      </div>
                      <div className="mt-2 text-[10px] font-mono text-slate-500 dark:text-[#8E8F99]">
                        Cancel requested at: {formatUtcDate(order.cancelRequestedAt)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Card 5: Sandbox Capital Allocation & Paper Run Archives */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-950 dark:text-white">Sandbox Capital Allocation</h2>
                <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                  Simulated paper trading capital allocated to your account.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsResetOpen(true)}
                className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 bg-indigo-50 dark:bg-indigo-500/10 px-3.5 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-500/20 transition-colors cursor-pointer"
              >
                Start New Paper Run
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
                <div className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-medium mb-1">Starting Allocation</div>
                <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
                  {user?.startingBalance != null ? `${formatUsd(user.startingBalance)} pUSD` : 'Unavailable'}
                </div>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
                <div className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-medium mb-1">Current Mark-to-Market</div>
                <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-[#00D09C]">
                  {(portfolio?.currentBalance ?? user?.currentBalance) != null 
                    ? `${formatUsd(portfolio?.currentBalance ?? user?.currentBalance)} pUSD` 
                    : 'Unavailable'}
                </div>
              </div>
            </div>

            {/* Paper Run Archives Section */}
            <div className="pt-4 border-t border-black/[0.06] dark:border-white/5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Paper Run History &amp; Retained Archives
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                    Account-owned past paper runs and trade journals retained in database. Never trigger a reset to test this screen.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={loadPaperRuns}
                  disabled={loadingPaperRuns}
                  className="px-3 py-1.5 rounded-full bg-slate-100 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-bold text-slate-800 dark:text-white flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                  aria-label="Refresh paper run archives"
                >
                  <RefreshCw size={12} className={loadingPaperRuns ? 'animate-spin' : ''} />
                  <span>{loadingPaperRuns ? 'Loading...' : 'Refresh archives'}</span>
                </button>
              </div>

              {paperRunsError && (
                <div role="alert" aria-live="polite" className="p-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-xs text-rose-700 dark:text-rose-400">
                  {paperRunsError}
                </div>
              )}

              {paperRuns.length === 0 ? (
                <p className="text-xs text-slate-500 dark:text-[#8E8F99]">No archived paper runs found for this account.</p>
              ) : (
                <div className="space-y-2">
                  {paperRuns.map((run) => (
                    <div key={run.id} className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="space-y-1 font-mono text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 dark:text-white">Run ID: {run.id.slice(0, 13)}...</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${run.status === 'ACTIVE' ? 'bg-emerald-100 dark:bg-[#00D09C]/10 text-emerald-700 dark:text-[#00D09C]' : 'bg-slate-200 dark:bg-white/10 text-slate-600 dark:text-[#8E8F99]'}`}>
                            {run.status}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-600 dark:text-[#8E8F99] flex flex-wrap gap-x-3">
                          <span>Started: {formatUtcDate(run.startedAt)}</span>
                          <span>Ended: {formatUtcDate(run.endedAt)}</span>
                          <span>Starting: {formatUsd(run.startingBalance)} pUSD</span>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleViewTrades(run.id)}
                        disabled={loadingTrades && tradesModalRunId === run.id}
                        className="px-3.5 py-1.5 rounded-full bg-slate-100 dark:bg-[#2C2D35] hover:bg-slate-200 dark:hover:bg-[#383944] text-xs font-bold text-slate-800 dark:text-white transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50 shrink-0"
                        aria-label={`View or export trades for paper run ${run.id}`}
                      >
                        <FileText size={13} />
                        <span>{loadingTrades && tradesModalRunId === run.id ? 'Loading...' : 'View Trades'}</span>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Card 6: Risk Profile Selector */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-4">
            <div>
              <h2 className="text-sm font-bold text-slate-950 dark:text-white mb-1">Risk Regime</h2>
              <p className="text-xs text-slate-500 dark:text-[#8E8F99]">Controls maximum capital committed per mirrored trade event in paper simulation.</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {profiles.map(p => {
                const isSelected = riskProfile === p.id;
                return (
                  <div 
                    key={p.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => setRiskProfile(p.id)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setRiskProfile(p.id); }}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                      isSelected 
                        ? 'border-indigo-600 dark:border-[#00D09C] bg-indigo-50/50 dark:bg-[#00D09C]/10 shadow-sm' 
                        : 'border-black/[0.06] dark:border-white/5 bg-slate-50 dark:bg-[#1C1D22] hover:border-black/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-slate-900 dark:text-white">{p.id}</span>
                      <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${isSelected ? 'border-indigo-600 dark:border-[#00D09C] bg-indigo-600 dark:bg-[#00D09C]' : 'border-slate-300 dark:border-slate-600'}`}>
                        {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white dark:bg-black" />}
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-[#8E8F99] leading-relaxed">{p.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Card 7: Daily Digest Toggle & Save Preferences */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-950 dark:text-white">Daily Digest Alerts</h2>
              <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">Receive daily performance digest summaries of all copy-trade executions.</p>
            </div>
            <button
              type="button"
              onClick={() => setDailyDigest(!dailyDigest)}
              className={`w-12 h-6 rounded-full p-0.5 transition-colors cursor-pointer ${dailyDigest ? 'bg-[#00D09C]' : 'bg-slate-300 dark:bg-[#2C2D35]'}`}
              aria-label="Toggle Daily Digest Alerts"
            >
              <div className={`w-5 h-5 rounded-full bg-white dark:bg-black shadow-xs transform transition-transform ${dailyDigest ? 'translate-x-6' : 'translate-x-0'}`} />
            </button>
          </div>

          {/* Preferences Save Button */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleSavePreferences}
              disabled={savingPreferences}
              className="flex items-center gap-2 px-8 py-3.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-xs font-bold transition-all shadow-md active:scale-[0.98] cursor-pointer disabled:opacity-50"
            >
              <Save size={14} />
              <span>{savingPreferences ? 'Saving...' : savedPreferencesSuccess ? '✓ Preferences Saved' : 'Save Preferences'}</span>
            </button>
          </div>
        </div>

        {/* Paper Run Trades Archive Modal */}
        <Modal
          isOpen={tradesModalRunId !== null}
          onClose={() => { setTradesModalRunId(null); setSelectedRunTrades(null); }}
          title="Paper Run Trade Journal"
          subtitle={tradesModalRunId ? `Run ID: ${tradesModalRunId}` : ''}
          maxWidth="max-w-2xl"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500 dark:text-[#8E8F99]">
                {selectedRunTrades ? `${selectedRunTrades.length} trades recorded in this run` : 'Loading trades...'}
              </span>
              {selectedRunTrades && selectedRunTrades.length > 0 && (
                <button
                  type="button"
                  onClick={() => handleExportTradesJson(tradesModalRunId || 'archive', selectedRunTrades)}
                  className="px-3.5 py-1.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
                  aria-label="Download trades JSON export"
                >
                  <Download size={13} />
                  <span>Download JSON</span>
                </button>
              )}
            </div>

            <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
              {!selectedRunTrades ? (
                <div className="p-8 text-center text-xs text-slate-500 dark:text-[#8E8F99]">Loading trade journal...</div>
              ) : selectedRunTrades.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500 dark:text-[#8E8F99]">No trades recorded during this run.</div>
              ) : (
                selectedRunTrades.map((t) => (
                  <div key={t.id} className="p-3 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.05] dark:border-white/5 font-mono text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 dark:text-white">
                        {t.side} {t.tokenId ? `${t.tokenId.slice(0, 10)}...` : 'Unknown Token'} <span className="text-[10px] font-normal text-slate-400">(Simulated)</span>
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-slate-300 font-bold">{t.status}</span>
                    </div>
                    <div className="text-[11px] text-slate-600 dark:text-[#8E8F99] flex flex-wrap gap-x-4">
                      <span>Fill Price: {t.fillPrice != null ? `$${t.fillPrice.toFixed(4)}` : 'Unavailable'}</span>
                      <span>Notional: {t.notionalUsd != null ? `$${t.notionalUsd.toFixed(2)} pUSD` : 'Unavailable'}</span>
                      <span>Fee: {t.feeUsd != null ? `$${t.feeUsd.toFixed(4)} pUSD` : 'Unavailable'}</span>
                      <span>PnL: {t.realizedPnlUsd != null ? `$${t.realizedPnlUsd.toFixed(2)} pUSD` : 'Unavailable'}</span>
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Executed at: {formatUtcDate(t.executedAt)} · Source: {t.sourceWallet ? `${t.sourceWallet.slice(0, 10)}...` : 'Unavailable'}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => { setTradesModalRunId(null); setSelectedRunTrades(null); }}
                className="px-5 py-2 rounded-full border border-black/10 dark:border-white/10 text-xs font-semibold text-slate-700 dark:text-white hover:bg-slate-100 dark:hover:bg-[#1C1D22] transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>

        {/* Reset Sandbox Modal */}
        <ResetSandboxModal
          isOpen={isResetOpen}
          onClose={() => setIsResetOpen(false)}
          userId={session?.user?.id}
          currentBalance={portfolio?.currentBalance ?? user?.currentBalance ?? null}
          onResetComplete={reloadAllUserData}
        />
      </div>
    </div>
  );
}
