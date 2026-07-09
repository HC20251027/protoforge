import { useEffect, useState } from 'react';
import { onboardingApi, vendorApi, type VendorStatus } from '../lib/api';
import type { OnboardingStatus } from '@protoforge/shared';

// 阶段 1 / 2 / 3 标识(3 步配置流程)
const STEP_LABELS = ['检测本地资源', '配置 LLM', '完成'];

export function OnboardingPage() {
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [vendor, setVendor] = useState<VendorStatus | null>(null);
  const [vendorError, setVendorError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, Record<string, string>>>({});
  const [testing, setTesting] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  // Phase 3 Task 1.5:引导页 step 1 拉取 vendor 状态
  // 用 useEffect + plain fetch(避免引入 react-query 新依赖)
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

  useEffect(() => {
    onboardingApi.status().then((s) => {
      setStatus(s);
      // 初始化 draft 为各 provider 的 base_url/model,api_key 留空
      const next: Record<string, Record<string, string>> = {};
      Object.entries(s.config).forEach(([k, v]) => {
        next[k] = { base_url: v.base_url, model: v.model, api_key: '' };
      });
      setDraft(next);
    });
  }, []);

  if (!status) return <p className="text-slate-400">加载中…</p>;

  const handleTest = async (name: string) => {
    setTesting(name);
    setMsg(null);
    try {
      const r = await onboardingApi.test(name, draft[name] ?? {});
      setMsg(`${name}: ${r.ok ? '✓' : '✗'} ${r.message}`);
      const refreshed = await onboardingApi.status();
      setStatus(refreshed);
    } catch (e) {
      setMsg(`${name}: ✗ ${(e as Error).message}`);
    } finally {
      setTesting(null);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMsg(null);
    try {
      const s = await onboardingApi.save(status.active, draft);
      setStatus(s);
      setMsg('已保存');
    } catch (e) {
      setMsg('保存失败: ' + (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="onboarding-page">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">引导:首次配置</h1>
        <p className="text-sm text-slate-600">3 步走完即可开始锻造。</p>
        <ol className="mt-2 flex gap-3 text-xs text-slate-500" data-testid="onboarding-steps">
          {STEP_LABELS.map((label, i) => (
            <li key={label} className="rounded bg-slate-100 px-2 py-1">
              第 {i + 1} 步 · {label}
            </li>
          ))}
        </ol>
      </header>

      {/* ===== Step 1:vendor 资源就位指示器 ===== */}
      <section
        className="rounded-lg border border-slate-200 bg-white p-4"
        data-testid="onboarding-step1-vendor"
      >
        <h2 className="text-base font-semibold text-slate-900">Step 1 · 本地资源检测</h2>
        <p className="mt-1 text-xs text-slate-600">
          我们会扫描游戏安装目录下的 vendor 资源;缺的资源会自动降级到云 API / 启发式算法。
        </p>

        {vendor === null && vendorError === null ? (
          <p className="mt-3 text-xs text-slate-500" data-testid="vendor-loading">检测中…</p>
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
      </section>

      {/* ===== Step 2:LLM provider 配置 ===== */}
      <section className="space-y-3" data-testid="onboarding-step2-providers">
        <h2 className="text-base font-semibold text-slate-900">Step 2 · 选择 LLM provider</h2>
        {status.providers.map((p, idx) => {
          // status.providers 顺序与 config 一致:cloud/local/disabled
          const name = (['cloud', 'local', 'disabled'] as const)[idx];
          const cfg = status.config[name];
          if (!cfg) return null;
          return (
            <div
              key={name}
              className="rounded-lg border border-slate-200 bg-white p-4"
              data-testid={`provider-card-${name}`}
            >
              <h3 className="text-base font-semibold text-slate-900">{p.label}</h3>
              <p className="mt-1 text-xs text-slate-600">{p.description}</p>
              <div className="mt-3 space-y-2">
                {p.fields.map((f) => (
                  <div key={f.key}>
                    <label className="block text-xs text-slate-600">{f.label}</label>
                    <input
                      type={f.secret ? 'password' : 'text'}
                      value={draft[name]?.[f.key] ?? ''}
                      placeholder={
                        f.secret && cfg.api_key_set ? '(已保存,留空保留原值)' : (f.default ?? '')
                      }
                      onChange={(e) =>
                        setDraft((d) => ({
                          ...d,
                          [name]: { ...(d[name] ?? {}), [f.key]: e.target.value },
                        }))
                      }
                      className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                    />
                  </div>
                ))}
              </div>
              {name !== 'disabled' ? (
                <button
                  type="button"
                  onClick={() => handleTest(name)}
                  disabled={testing === name}
                  className="mt-3 rounded border border-slate-300 bg-white px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {testing === name ? '探测中…' : 'Test'}
                </button>
              ) : null}
            </div>
          );
        })}
      </section>

      {/* ===== Step 3:active provider 选择(含 local-bundled) ===== */}
      <section
        className="rounded-lg border border-slate-200 bg-white p-4"
        data-testid="onboarding-step3-active"
      >
        <h2 className="text-base font-semibold text-slate-900">Step 3 · 启用方式</h2>
        <p className="mt-1 text-xs text-slate-600">
          推荐 ☁️ 云 API;若本地 LLM 资源已就位,可选本地内置(Qwen2.5-7B)。
        </p>
        <div className="mt-3 flex flex-col gap-2">
          {(['cloud', 'local', 'disabled'] as const).map((p) => (
            <label
              key={p}
              className="flex items-center gap-2 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              data-testid={`active-radio-${p}`}
            >
              <input
                type="radio"
                name="active-provider"
                value={p}
                checked={status.active === p}
                onChange={() => setStatus((s) => (s ? { ...s, active: p } : s))}
              />
              <span className="text-slate-700">{p}</span>
            </label>
          ))}

          {/* local-bundled:仅在 vendor.local_llm.available 时显示 */}
          {vendor?.local_llm?.available ? (
            <label
              className="flex items-center gap-2 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm"
              data-testid="active-radio-local-bundled"
            >
              <input
                type="radio"
                name="active-provider"
                value="local-bundled"
                checked={status.active === 'local-bundled'}
                onChange={() => {
                  // 1. UI state 立刻反映
                  setStatus((s) =>
                    s ? { ...s, active: 'local-bundled' as typeof s.active } : s
                  );
                  // 2. localStorage 持久化(供后端 / 启动脚本识别)
                  try {
                    window.localStorage.setItem(
                      'protoforge.llm.provider',
                      'local-bundled',
                    );
                  } catch {
                    // localStorage 不可用(隐私模式 / SSR)— 静默忽略,UI state 仍是 source of truth
                  }
                }}
              />
              <span className="text-slate-700">
                本地内置(Qwen2.5-7B,需要 8GB 显存)
              </span>
              <span className="ml-auto rounded bg-emerald-500 px-2 py-0.5 text-xs text-white">
                vendor 已就位
              </span>
            </label>
          ) : null}
        </div>
      </section>

      <section className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="rounded bg-forge-500 px-4 py-2 text-sm font-semibold text-white hover:bg-forge-600 disabled:opacity-50"
        >
          {saving ? '保存中…' : 'Save'}
        </button>
        <button
          type="button"
          onClick={async () => {
            const s = await onboardingApi.reset();
            setStatus(s);
          }}
          className="rounded border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
        >
          Reset
        </button>
        {msg ? <span className="text-xs text-slate-500">{msg}</span> : null}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 子组件:vendor 资源指示器行
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
