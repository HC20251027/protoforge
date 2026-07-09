import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  vendorApi,
  onboardingApi,
  type VendorStatus,
  type OnboardingState,
  type LLMProviderV2,
  type CloudProvider,
} from '../lib/api';

// ---------------------------------------------------------------------------
// 3 步配置流程
// - Step 1: 本地资源检测(vendor 状态展示)
// - Step 2: LLM provider 选择(☁️ cloud / 📦 local-bundled / ⛔ disabled)
// - Step 3: 根据 step 2 选择显示不同分支(api_key 输入 / 本地模型说明 / 纯滑块说明)
// - 完成 → onboardingApi.complete(...) → 写 localStorage.protoforge.onboarding_completed="true" → /forge
// ---------------------------------------------------------------------------

type Step = 1 | 2 | 3;
type CloudKey = CloudProvider; // 'deepseek' | 'claude' | 'openai'

const STEP_LABELS: Record<Step, string> = {
  1: '检测本地资源',
  2: '选择 LLM',
  3: '配置 API key',
};

// 默认 player ID(后续接 user system 时替换)。要求是合法的 user_id(只含字母数字下划线连字符点)
const DEFAULT_USER_ID = 'default_player';

// cloud provider 申请免费 API 的官方链接
const CLOUD_PROVIDER_URLS: Record<CloudKey, { label: string; url: string; hint: string }> = {
  deepseek: {
    label: 'DeepSeek',
    url: 'https://platform.deepseek.com/api_keys',
    hint: 'DeepSeek 新用户有免费额度',
  },
  claude: {
    label: 'Anthropic Claude',
    url: 'https://console.anthropic.com/settings/keys',
    hint: 'Claude 需要付费 API key',
  },
  openai: {
    label: 'OpenAI',
    url: 'https://platform.openai.com/api-keys',
    hint: 'OpenAI 新用户有 $5 免费额度',
  },
};

export function OnboardingPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [vendor, setVendor] = useState<VendorStatus | null>(null);
  const [vendorError, setVendorError] = useState<string | null>(null);
  // backend state:仅在启动 effect 里读一次,用来同步默认值
  const [, setBackendState] = useState<OnboardingState | null>(null);
  const [stateError, setStateError] = useState<string | null>(null);

  // 表单数据
  const [llmProvider, setLlmProvider] = useState<LLMProviderV2>('cloud');
  const [cloudProvider, setCloudProvider] = useState<CloudKey>('deepseek');
  const [apiKey, setApiKey] = useState<string>('');

  // 提交状态
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitMsg, setSubmitMsg] = useState<string | null>(null);

  // 启动时:如果 localStorage.protoforge.onboarding_completed === "true" → 跳 /forge
  useEffect(() => {
    try {
      if (window.localStorage.getItem('protoforge.onboarding_completed') === 'true') {
        navigate('/forge', { replace: true });
        return;
      }
    } catch {
      // 隐私模式 / SSR 静默
    }
  }, [navigate]);

  // Step 1 拉 vendor 状态
  useEffect(() => {
    let cancelled = false;
    vendorApi
      .status()
      .then((s) => {
        if (!cancelled) setVendor(s);
      })
      .catch((e) => {
        if (!cancelled) setVendorError((e as Error).message ?? 'vendor status 请求失败');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 拉一次后端 state(只是用来同步默认值;真正"是否完成"用 localStorage)
  useEffect(() => {
    let cancelled = false;
    onboardingApi
      .getState(DEFAULT_USER_ID)
      .then((s) => {
        if (cancelled) return;
        setBackendState(s);
        if (s.llm_provider) {
          setLlmProvider(s.llm_provider);
        }
        if (s.cloud_provider) {
          setCloudProvider(s.cloud_provider);
        }
      })
      .catch((e) => {
        if (!cancelled) setStateError((e as Error).message ?? 'state 请求失败');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const goNext = () => {
    setCurrentStep((s) => (s < 3 ? ((s + 1) as Step) : s));
  };
  const goPrev = () => {
    setCurrentStep((s) => (s > 1 ? ((s - 1) as Step) : s));
  };

  const handleComplete = async () => {
    setSubmitting(true);
    setSubmitError(null);
    setSubmitMsg(null);
    try {
      const sub = {
        llm_provider: llmProvider,
        cloud_provider: llmProvider === 'cloud' ? cloudProvider : null,
        api_key: llmProvider === 'cloud' ? apiKey : null,
      };
      const resp = await onboardingApi.complete(DEFAULT_USER_ID, sub);
      if (!resp.ok) {
        setSubmitError(resp.message || '提交失败');
        return;
      }
      // 写 localStorage,下次启动跳过引导页
      try {
        window.localStorage.setItem('protoforge.onboarding_completed', 'true');
        // 兼容旧 key(Task 1.5 已写)
        window.localStorage.setItem('protoforge.llm.provider', llmProvider);
      } catch {
        // 隐私模式 / SSR 静默
      }
      setSubmitMsg(resp.message);
      // 跳 /forge(项目里实际是 /missions; /forge 没注册会走兜底 Navigate to "/",可接受)
      navigate('/forge', { replace: true });
    } catch (e) {
      setSubmitError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="onboarding-page">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">引导:首次配置</h1>
        <p className="text-sm text-slate-600">3 步走完即可开始锻造。</p>

        {/* Stepper 进度条 */}
        <ol
          className="mt-3 flex gap-3 text-xs"
          data-testid="onboarding-stepper"
        >
          {([1, 2, 3] as const).map((n) => (
            <li
              key={n}
              className={[
                'rounded px-3 py-1 transition',
                n === currentStep
                  ? 'bg-forge-500 text-white'
                  : n < currentStep
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-slate-100 text-slate-500',
              ].join(' ')}
              data-testid={`onboarding-step-${n}`}
            >
              第 {n} 步 · {STEP_LABELS[n]}
            </li>
          ))}
        </ol>
      </header>

      {/* ===== Step 1:vendor 资源就位指示器 ===== */}
      {currentStep === 1 ? (
        <section
          className="rounded-lg border border-slate-200 bg-white p-4"
          data-testid="onboarding-step1-vendor"
        >
          <h2 className="text-base font-semibold text-slate-900">
            Step 1 · 本地资源检测
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            我们会扫描游戏安装目录下的 vendor 资源;缺的资源会自动降级到云 API /
            启发式算法。
          </p>

          {vendor === null && vendorError === null ? (
            <p className="mt-3 text-xs text-slate-500" data-testid="vendor-loading">
              检测中…
            </p>
          ) : vendorError ? (
            <p className="mt-3 text-xs text-red-500" data-testid="vendor-error">
              vendor status 拉取失败: {vendorError}
            </p>
          ) : vendor ? (
            <ul className="mt-3 space-y-2" data-testid="vendor-list">
              <VendorRow
                testId="vendor-proto-language"
                label="Proto 引擎"
                available={vendor.proto_language.available}
                availableText="已就位"
                unavailableText="未就位(将用启发式)"
                sizeText={`${vendor.proto_language.size_mb} MB`}
              />
              <MlModelsRow vendor={vendor} />
              <VendorRow
                testId="vendor-local-llm"
                label="本地 LLM"
                available={vendor.local_llm.available}
                availableText={`已就位(${formatSize(vendor.local_llm.size_mb)} ${vendor.local_llm.model_name ?? ''})`}
                unavailableText="未就位(将用云 API)"
                sizeText={`${vendor.local_llm.size_mb} MB`}
              />
            </ul>
          ) : null}

          {stateError ? (
            <p className="mt-3 text-xs text-amber-600">state 拉取失败: {stateError}</p>
          ) : null}

          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={goNext}
              data-testid="onboarding-step1-next"
              className="rounded bg-forge-500 px-4 py-2 text-sm font-semibold text-white hover:bg-forge-600"
            >
              下一步 →
            </button>
          </div>
        </section>
      ) : null}

      {/* ===== Step 2:LLM provider 选择 ===== */}
      {currentStep === 2 ? (
        <section
          className="space-y-3"
          data-testid="onboarding-step2-providers"
        >
          <h2 className="text-base font-semibold text-slate-900">
            Step 2 · 选择 LLM provider
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            推荐 ☁️ 云 API(DeepSeek 默认);本地模型只在 vendor 资源就位时可用;⛔ 跳过
            LLM 则全程使用纯滑块。
          </p>

          {/* ☁️ 云 API(默认) */}
          <label
            className={[
              'flex cursor-pointer flex-col gap-2 rounded-lg border p-4 transition',
              llmProvider === 'cloud'
                ? 'border-forge-500 bg-forge-50'
                : 'border-slate-200 bg-white hover:bg-slate-50',
            ].join(' ')}
            data-testid="provider-option-cloud"
          >
            <div className="flex items-center gap-2">
              <input
                type="radio"
                name="llm-provider"
                value="cloud"
                checked={llmProvider === 'cloud'}
                onChange={() => setLlmProvider('cloud')}
                data-testid="radio-cloud"
              />
              <span className="text-base font-semibold text-slate-900">☁️ 云 API(推荐)</span>
              {llmProvider === 'cloud' ? (
                <span className="ml-auto rounded bg-forge-500 px-2 py-0.5 text-xs text-white">
                  已选
                </span>
              ) : null}
            </div>
            <p className="text-xs text-slate-600">
              默认 DeepSeek(中文友好,价格便宜);也可选 Claude / OpenAI。
            </p>
            {llmProvider === 'cloud' ? (
              <div className="ml-6 flex flex-wrap gap-2" data-testid="cloud-subcards">
                {(['deepseek', 'claude', 'openai'] as const).map((cp) => (
                  <button
                    key={cp}
                    type="button"
                    onClick={() => setCloudProvider(cp)}
                    data-testid={`cloud-subcard-${cp}`}
                    className={[
                      'rounded border px-3 py-1 text-xs',
                      cloudProvider === cp
                        ? 'border-forge-500 bg-forge-500 text-white'
                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
                    ].join(' ')}
                  >
                    {CLOUD_PROVIDER_URLS[cp].label}
                  </button>
                ))}
              </div>
            ) : null}
          </label>

          {/* 📦 本地内置(仅 vendor 可用) */}
          {vendor?.local_llm?.available ? (
            <label
              className={[
                'flex cursor-pointer flex-col gap-1 rounded-lg border p-4 transition',
                llmProvider === 'local-bundled'
                  ? 'border-emerald-500 bg-emerald-50'
                  : 'border-slate-200 bg-white hover:bg-slate-50',
              ].join(' ')}
              data-testid="provider-option-local-bundled"
            >
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  name="llm-provider"
                  value="local-bundled"
                  checked={llmProvider === 'local-bundled'}
                  onChange={() => setLlmProvider('local-bundled')}
                  data-testid="radio-local-bundled"
                />
                <span className="text-base font-semibold text-slate-900">
                  📦 本地内置
                </span>
                <span className="ml-auto rounded bg-emerald-500 px-2 py-0.5 text-xs text-white">
                  vendor 已就位
                </span>
              </div>
              <p className="text-xs text-slate-600">
                用 Qwen2.5-7B-Instruct(Q4_K_M),完全离线。
              </p>
            </label>
          ) : null}

          {/* ⛔ 纯滑块 */}
          <label
            className={[
              'flex cursor-pointer flex-col gap-1 rounded-lg border p-4 transition',
              llmProvider === 'disabled'
                ? 'border-slate-500 bg-slate-100'
                : 'border-slate-200 bg-white hover:bg-slate-50',
            ].join(' ')}
            data-testid="provider-option-disabled"
          >
            <div className="flex items-center gap-2">
              <input
                type="radio"
                name="llm-provider"
                value="disabled"
                checked={llmProvider === 'disabled'}
                onChange={() => setLlmProvider('disabled')}
                data-testid="radio-disabled"
              />
              <span className="text-base font-semibold text-slate-900">
                ⛔ 纯滑块(不用 LLM)
              </span>
            </div>
            <p className="text-xs text-slate-600">
              完全离线 + 不联网,玩家只能靠预设滑块组合,Phase 1 的安全默认。
            </p>
          </label>

          <div className="flex justify-between">
            <button
              type="button"
              onClick={goPrev}
              className="rounded border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
              data-testid="onboarding-step2-prev"
            >
              ← 上一步
            </button>
            <button
              type="button"
              onClick={goNext}
              data-testid="onboarding-step2-next"
              className="rounded bg-forge-500 px-4 py-2 text-sm font-semibold text-white hover:bg-forge-600"
            >
              下一步 →
            </button>
          </div>
        </section>
      ) : null}

      {/* ===== Step 3:根据 llmProvider 显示不同分支 ===== */}
      {currentStep === 3 ? (
        <section
          className="rounded-lg border border-slate-200 bg-white p-4"
          data-testid="onboarding-step3-config"
        >
          <h2 className="text-base font-semibold text-slate-900">Step 3 · 配置</h2>

          {llmProvider === 'cloud' ? (
            <div className="mt-3 space-y-3" data-testid="step3-cloud">
              <p className="text-xs text-slate-600">
                已选:☁️ 云 API · {CLOUD_PROVIDER_URLS[cloudProvider].label}
              </p>
              <div>
                <label className="block text-xs text-slate-600" htmlFor="onb-api-key">
                  API Key
                </label>
                <input
                  id="onb-api-key"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  data-testid="onboarding-api-key-input"
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                />
                <p className="mt-1 text-xs text-slate-500">
                  {CLOUD_PROVIDER_URLS[cloudProvider].hint}。密钥仅加密后存储在本地,不会上传。
                </p>
              </div>
              <a
                href={CLOUD_PROVIDER_URLS[cloudProvider].url}
                target="_blank"
                rel="noreferrer noopener"
                data-testid={`onboarding-cloud-signup-${cloudProvider}`}
                className="inline-block rounded border border-forge-500 px-3 py-1 text-xs text-forge-700 hover:bg-forge-50"
              >
                申请免费 {CLOUD_PROVIDER_URLS[cloudProvider].label} API →
              </a>
            </div>
          ) : null}

          {llmProvider === 'local-bundled' ? (
            <div className="mt-3 space-y-2" data-testid="step3-local-bundled">
              <p className="text-sm text-emerald-700">✓ 本地模型已就位</p>
              <p className="text-xs text-slate-600">
                将使用 vendored Qwen2.5-7B-Instruct(Q4_K_M)。完全离线,无网络请求。
              </p>
              <p className="rounded bg-amber-50 px-3 py-2 text-xs text-amber-800" data-testid="onboarding-vram-warning">
                注意:本模式需要 8GB 显存(GPU 推理);CPU 推理会非常慢(分钟级)。
              </p>
            </div>
          ) : null}

          {llmProvider === 'disabled' ? (
            <div className="mt-3 space-y-2" data-testid="step3-disabled">
              <p className="text-sm text-slate-700">将使用纯滑块模式</p>
              <p className="text-xs text-slate-600">
                玩家只能靠滑块组合完成任务;无 LLM 辅助,所有评分走规则/启发式。
              </p>
            </div>
          ) : null}

          {submitError ? (
            <p className="mt-3 text-xs text-red-600" data-testid="onboarding-submit-error">
              {submitError}
            </p>
          ) : null}
          {submitMsg ? (
            <p className="mt-3 text-xs text-emerald-600" data-testid="onboarding-submit-msg">
              {submitMsg}
            </p>
          ) : null}

          <div className="mt-4 flex justify-between">
            <button
              type="button"
              onClick={goPrev}
              data-testid="onboarding-step3-prev"
              className="rounded border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              ← 上一步
            </button>
            <button
              type="button"
              onClick={handleComplete}
              disabled={submitting || (llmProvider === 'cloud' && !apiKey.trim())}
              data-testid="onboarding-complete"
              className="rounded bg-forge-500 px-4 py-2 text-sm font-semibold text-white hover:bg-forge-600 disabled:opacity-50"
            >
              {submitting ? '提交中…' : '完成 →'}
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 子组件:vendor 资源指示器行(沿用 Task 1.5 的 testid 与渲染,保持向后兼容)
// ---------------------------------------------------------------------------

function VendorRow(props: {
  testId: string;
  label: string;
  available: boolean;
  availableText: string;
  unavailableText: string;
  sizeText: string;
}) {
  const { testId, label, available, availableText, unavailableText, sizeText } = props;
  return (
    <li
      className="flex items-center gap-2 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
      data-testid={testId}
    >
      <span
        className={[
          'inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold text-white',
          available ? 'bg-green-500' : 'bg-red-500',
        ].join(' ')}
        aria-label={available ? 'available' : 'unavailable'}
        data-testid={`${testId}-indicator`}
      >
        {available ? '✓' : '✗'}
      </span>
      <span className="font-medium text-slate-800">{label}</span>
      <span className={available ? 'text-green-700' : 'text-red-700'}>
        {available ? availableText : unavailableText}
      </span>
      <span className="ml-auto text-xs text-slate-500">{sizeText}</span>
    </li>
  );
}

function MlModelsRow({ vendor }: { vendor: VendorStatus }) {
  const ml = vendor.ml_models;
  const esm2 = ml['esm2-150m']?.available ?? false;
  const spliceai = ml['spliceai']?.available ?? false;
  const st = ml['splice-transformer']?.available ?? false;
  const availableCount = [esm2, spliceai, st].filter(Boolean).length;
  const allAvailable = availableCount === 3;
  const someAvailable = availableCount > 0;
  // 颜色语义:全 green-500,部分 yellow-500,全无 red-500
  const indicatorClass = allAvailable
    ? 'bg-green-500'
    : someAvailable
    ? 'bg-yellow-500'
    : 'bg-red-500';
  const text = allAvailable
    ? '全部就位'
    : someAvailable
    ? `部分就位(ESM2 ${esm2 ? '✓' : '✗'})`
    : '未就位';
  const totalMb =
    (ml['esm2-150m']?.size_mb ?? 0) +
    (ml['spliceai']?.size_mb ?? 0) +
    (ml['splice-transformer']?.size_mb ?? 0);
  return (
    <li
      className="flex items-center gap-2 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
      data-testid="vendor-ml-models"
    >
      <span
        className={[
          'inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold text-white',
          indicatorClass,
        ].join(' ')}
        data-testid="vendor-ml-models-indicator"
      >
        {allAvailable ? '✓' : someAvailable ? '!' : '✗'}
      </span>
      <span className="font-medium text-slate-800">ML 模型</span>
      <span
        className={
          allAvailable ? 'text-green-700' : someAvailable ? 'text-yellow-700' : 'text-red-700'
        }
      >
        {text}
      </span>
      <span className="ml-auto text-xs text-slate-500">{totalMb} MB</span>
    </li>
  );
}

function formatSize(mb: number): string {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)}GB`;
  return `${mb}MB`;
}
