import { useEffect, useState } from 'react';
import { onboardingApi } from '../lib/api';
import type { OnboardingStatus } from '@protoforge/shared';

export function OnboardingPage() {
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [draft, setDraft] = useState<Record<string, Record<string, string>>>({});
  const [testing, setTesting] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

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
        <h1 className="text-2xl font-bold text-slate-900">LLM 配置</h1>
        <p className="text-sm text-slate-600">选择 provider 后填入参数,先 Test 再 Save。</p>
      </header>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <label className="text-sm font-semibold text-slate-700">当前 provider</label>
        <div className="mt-2 flex gap-2">
          {(['cloud', 'local', 'disabled'] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setStatus((s) => (s ? { ...s, active: p } : s))}
              className={[
                'rounded border px-3 py-1.5 text-sm',
                status.active === p
                  ? 'border-forge-500 bg-forge-50 text-forge-700'
                  : 'border-slate-300 bg-white text-slate-700',
              ].join(' ')}
            >
              {p}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
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
