import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { OnboardingPage } from '@/pages/OnboardingPage';

// ---------------------------------------------------------------------------
// Mocks — 隔离 fetch 调用,避免测试被真实后端依赖
// ---------------------------------------------------------------------------

// 内存里维护 fetch mock 的"下一帧响应"
let nextVendorResponse: unknown = null;
let nextVendorShouldFail = false;
let nextOnboardingResponse: unknown = {
  active: 'cloud',
  providers: [
    { label: '云端 API(推荐 DeepSeek / OpenAI 兼容)', description: 'd', fields: [] },
    { label: '本地模型(Ollama / LM Studio)', description: 'd', fields: [] },
    { label: '不使用 LLM(纯滑块模式)', description: 'd', fields: [] },
  ],
  config: {
    cloud: { name: 'cloud', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat', api_key_set: false },
    local: { name: 'local', base_url: 'http://localhost:11434/v1', model: 'llama3', api_key_set: false },
    disabled: { name: 'disabled', base_url: '', model: '', api_key_set: false },
  },
  last_test_at: null,
  last_test_ok: null,
  last_test_message: '',
};

function makeFetchMock(): typeof fetch {
  return vi.fn(async (url: string) => {
    if (url.includes('/api/vendor/status')) {
      if (nextVendorShouldFail) {
        return new Response('internal error', { status: 500 });
      }
      return new Response(JSON.stringify(nextVendorResponse), { status: 200 });
    }
    if (url.includes('/api/onboarding/status')) {
      return new Response(JSON.stringify(nextOnboardingResponse), { status: 200 });
    }
    // 兜底:任何其他 fetch 直接返回 200 空
    return new Response('{}', { status: 200 });
  }) as unknown as typeof fetch;
}

beforeEach(() => {
  vi.restoreAllMocks();
  // 每次测试前清掉 localStorage,避免污染
  window.localStorage.clear();
  vi.spyOn(global, 'fetch').mockImplementation(makeFetchMock());
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// 测试 1:vendor 全部 available 时,step 1 显示 3 个绿色 ✓
// ---------------------------------------------------------------------------

describe('OnboardingPage · step 1 vendor 指示器', () => {
  it('vendor 全部 available 时显示 3 个绿色 ✓', async () => {
    nextVendorShouldFail = false;
    nextVendorResponse = {
      proto_language: { available: true, size_mb: 12, path: 'vendor/proto-language/build/lib' },
      ml_models: {
        'esm2-150m': { available: true, size_mb: 567, path: 'vendor/models/esm2-150m' },
        spliceai: { available: true, size_mb: 50, path: 'vendor/models/spliceai' },
        'splice-transformer': { available: true, size_mb: 400, path: 'vendor/models/splice-transformer' },
      },
      local_llm: {
        available: true,
        size_mb: 4466,
        path: 'vendor/llm',
        model_name: 'Qwen2.5-7B-Instruct-Q4_K_M',
      },
    };

    render(
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>,
    );

    // 等待 onboarding status 拉完,UI 才完整渲染
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-page')).toBeInTheDocument();
    });

    // vendor list 出现
    await waitFor(() => {
      expect(screen.getByTestId('vendor-list')).toBeInTheDocument();
    });

    // 3 个指示器都应是 green-500
    const protoIndicator = screen.getByTestId('vendor-proto-language-indicator');
    const mlIndicator = screen.getByTestId('vendor-ml-models-indicator');
    const llmIndicator = screen.getByTestId('vendor-local-llm-indicator');

    expect(protoIndicator.className).toContain('bg-green-500');
    expect(protoIndicator.textContent).toBe('✓');

    expect(mlIndicator.className).toContain('bg-green-500');
    expect(mlIndicator.textContent).toBe('✓');

    expect(llmIndicator.className).toContain('bg-green-500');
    expect(llmIndicator.textContent).toBe('✓');
  });
});

// ---------------------------------------------------------------------------
// 测试 2:vendor.local_llm 不可用时,step 3 没有"本地内置" radio
// ---------------------------------------------------------------------------

describe('OnboardingPage · step 3 local-bundled 选项', () => {
  it('local_llm 不可用时,step 3 不显示"本地内置" radio', async () => {
    nextVendorShouldFail = false;
    nextVendorResponse = {
      proto_language: { available: true, size_mb: 12, path: 'vendor/proto-language/build/lib' },
      ml_models: {
        'esm2-150m': { available: true, size_mb: 567, path: 'vendor/models/esm2-150m' },
        spliceai: { available: false, size_mb: 0, path: 'vendor/models/spliceai' },
        'splice-transformer': { available: false, size_mb: 0, path: 'vendor/models/splice-transformer' },
      },
      local_llm: {
        available: false,
        size_mb: 0,
        path: 'vendor/llm',
        model_name: 'Qwen2.5-7B-Instruct-Q4_K_M',
      },
    };

    render(
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('onboarding-page')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByTestId('onboarding-step3-active')).toBeInTheDocument();
    });

    // 关键断言:local-bundled radio **不**应该出现
    expect(screen.queryByTestId('active-radio-local-bundled')).toBeNull();

    // 但 cloud / local / disabled 三个 radio 应当存在
    expect(screen.getByTestId('active-radio-cloud')).toBeInTheDocument();
    expect(screen.getByTestId('active-radio-local')).toBeInTheDocument();
    expect(screen.getByTestId('active-radio-disabled')).toBeInTheDocument();
  });

  it('local_llm 可用时,step 3 显示"本地内置" radio 且可写入 localStorage', async () => {
    nextVendorShouldFail = false;
    nextVendorResponse = {
      proto_language: { available: true, size_mb: 12, path: 'vendor/proto-language/build/lib' },
      ml_models: {
        'esm2-150m': { available: true, size_mb: 567, path: 'vendor/models/esm2-150m' },
        spliceai: { available: false, size_mb: 0, path: 'vendor/models/spliceai' },
        'splice-transformer': { available: false, size_mb: 0, path: 'vendor/models/splice-transformer' },
      },
      local_llm: {
        available: true,
        size_mb: 4466,
        path: 'vendor/llm',
        model_name: 'Qwen2.5-7B-Instruct-Q4_K_M',
      },
    };

    render(
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('onboarding-page')).toBeInTheDocument();
    });

    const bundledRadio = await waitFor(() => screen.getByTestId('active-radio-local-bundled'));
    expect(bundledRadio).toBeInTheDocument();

    // 点击 radio → 应当把 'protoforge.llm.provider' 写到 localStorage
    const radioInput = bundledRadio.querySelector('input[type="radio"]') as HTMLInputElement;
    expect(radioInput).toBeTruthy();
    radioInput.click();

    await waitFor(() => {
      expect(window.localStorage.getItem('protoforge.llm.provider')).toBe('local-bundled');
    });
  });
});
