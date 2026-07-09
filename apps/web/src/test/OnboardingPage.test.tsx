import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { OnboardingPage } from '@/pages/OnboardingPage';

// ---------------------------------------------------------------------------
// Mocks — 隔离 fetch 调用,避免测试被真实后端依赖
// ---------------------------------------------------------------------------

// 内存里维护 fetch mock 的"下一帧响应"
let nextVendorResponse: unknown = null;
let nextStateResponse: unknown = {
  completed: false,
  llm_provider: 'cloud',
  cloud_provider: 'deepseek',
  has_api_key: false,
  vendor_status: {
    proto_language: { available: true, size_mb: 12, path: 'vendor/proto-language/build/lib' },
    ml_models: {},
    local_llm: {
      available: true,
      size_mb: 4466,
      path: 'vendor/llm',
      model_name: 'Qwen2.5-7B-Instruct-Q4_K_M',
    },
  },
};
let nextCompleteResponse: { ok: boolean; message: string } = { ok: true, message: '欢迎来到 ProtoForge!' };
let completeCalls: Array<{ url: string; body: unknown }> = [];

function makeFetchMock(): typeof fetch {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.includes('/api/vendor/status') || url.includes('/api/vendor')) {
      return new Response(JSON.stringify(nextVendorResponse), { status: 200 });
    }
    if (url.includes('/api/onboarding/state')) {
      return new Response(JSON.stringify(nextStateResponse), { status: 200 });
    }
    if (url.includes('/api/onboarding/complete')) {
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      completeCalls.push({ url, body });
      return new Response(JSON.stringify(nextCompleteResponse), { status: 200 });
    }
    if (url.includes('/api/onboarding/status')) {
      return new Response(JSON.stringify({ active: 'cloud' }), { status: 200 });
    }
    // 兜底:任何其他 fetch 直接返回 200 空
    return new Response('{}', { status: 200 });
  }) as unknown as typeof fetch;
}

beforeEach(() => {
  vi.restoreAllMocks();
  // 每次测试前清掉 localStorage,避免污染
  window.localStorage.clear();
  completeCalls = [];
  vi.spyOn(global, 'fetch').mockImplementation(makeFetchMock());
});

afterEach(() => {
  vi.restoreAllMocks();
});

// 用一个 wrap helper:在 /onboarding 路径下渲染,方便 useNavigate 不会抛错
function renderOnboarding() {
  return render(
    <MemoryRouter initialEntries={['/onboarding']}>
      <Routes>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/forge" element={<div data-testid="forge-page">FORGE</div>} />
        <Route path="/" element={<div data-testid="home-page">HOME</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Phase 3 Task 1.5 兼容(用新 testid 重新表达):vendor 全部 available 时显示 3 个绿勾
// ---------------------------------------------------------------------------

describe('OnboardingPage · step 1 vendor 指示器', () => {
  it('vendor 全部 available 时显示 3 个绿色 ✓', async () => {
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

    renderOnboarding();

    await waitFor(() => {
      expect(screen.getByTestId('onboarding-page')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByTestId('vendor-list')).toBeInTheDocument();
    });

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
// Phase 3 Task 4:3 步配置流程
// ---------------------------------------------------------------------------

describe('OnboardingPage · 3 步 stepper 渲染', () => {
  it('stepper 渲染 1/2/3 三个步骤,初始在第 1 步', async () => {
    renderOnboarding();
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-stepper')).toBeInTheDocument();
    });
    expect(screen.getByTestId('onboarding-step-1')).toBeInTheDocument();
    expect(screen.getByTestId('onboarding-step-2')).toBeInTheDocument();
    expect(screen.getByTestId('onboarding-step-3')).toBeInTheDocument();
    // 初始只显示 step 1 section
    expect(screen.getByTestId('onboarding-step1-vendor')).toBeInTheDocument();
    expect(screen.queryByTestId('onboarding-step2-providers')).toBeNull();
    expect(screen.queryByTestId('onboarding-step3-config')).toBeNull();
  });

  it('点 step1 "下一步" → 切到 step 2', async () => {
    renderOnboarding();
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-step1-next')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-step2-providers')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('onboarding-step1-vendor')).toBeNull();
  });

  it('step2 "下一步" → step 3;step3 "上一步" → step 2', async () => {
    renderOnboarding();
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-step1-next')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-step2-next')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('onboarding-step2-next'));
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-step3-config')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('onboarding-step3-prev'));
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-step2-providers')).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Phase 3 Task 4:Step 2 默认 cloud + Step 3 分支
// ---------------------------------------------------------------------------

describe('OnboardingPage · step 2 provider 选择', () => {
  it('step 2 默认选中 cloud,且显示 cloud subcards(DeepSeek/Claude/OpenAI)', async () => {
    renderOnboarding();
    await waitFor(() => screen.getByTestId('onboarding-step1-next'));
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => screen.getByTestId('provider-option-cloud'));

    const cloudRadio = screen.getByTestId('radio-cloud') as HTMLInputElement;
    expect(cloudRadio.checked).toBe(true);

    // subcards 应在 cloud 选中时显示
    expect(screen.getByTestId('cloud-subcards')).toBeInTheDocument();
    expect(screen.getByTestId('cloud-subcard-deepseek')).toBeInTheDocument();
    expect(screen.getByTestId('cloud-subcard-claude')).toBeInTheDocument();
    expect(screen.getByTestId('cloud-subcard-openai')).toBeInTheDocument();
  });

  it('vendor.local_llm 不可用时,step 2 不显示 local-bundled 选项', async () => {
    nextVendorResponse = {
      proto_language: { available: true, size_mb: 12, path: 'x' },
      ml_models: {},
      local_llm: { available: false, size_mb: 0, path: 'y', model_name: 'm' },
    };
    renderOnboarding();
    await waitFor(() => screen.getByTestId('onboarding-step1-next'));
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => screen.getByTestId('provider-option-cloud'));
    expect(screen.queryByTestId('provider-option-local-bundled')).toBeNull();
    // disabled 仍然在
    expect(screen.getByTestId('provider-option-disabled')).toBeInTheDocument();
  });

  it('vendor.local_llm 可用时,step 2 显示 local-bundled 选项', async () => {
    nextVendorResponse = {
      proto_language: { available: true, size_mb: 12, path: 'x' },
      ml_models: {},
      local_llm: { available: true, size_mb: 4466, path: 'y', model_name: 'm' },
    };
    renderOnboarding();
    await waitFor(() => screen.getByTestId('onboarding-step1-next'));
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => screen.getByTestId('provider-option-local-bundled'));
  });
});

// ---------------------------------------------------------------------------
// Phase 3 Task 4:Step 3 分支显示
// ---------------------------------------------------------------------------

describe('OnboardingPage · step 3 三种 provider 的不同分支', () => {
  async function jumpToStep3() {
    renderOnboarding();
    await waitFor(() => screen.getByTestId('onboarding-step1-next'));
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => screen.getByTestId('onboarding-step2-next'));
    fireEvent.click(screen.getByTestId('onboarding-step2-next'));
    await waitFor(() => screen.getByTestId('onboarding-step3-config'));
  }

  it('cloud 选中时,step 3 显示 API key 输入 + 申请免费 API 链接', async () => {
    await jumpToStep3();
    expect(screen.getByTestId('step3-cloud')).toBeInTheDocument();
    expect(screen.getByTestId('onboarding-api-key-input')).toBeInTheDocument();
    // 默认 deepseek → 应当有 deepseek 申请链接
    const link = screen.getByTestId('onboarding-cloud-signup-deepseek');
    expect(link).toBeInTheDocument();
    expect(link.getAttribute('href')).toContain('deepseek.com');
  });

  it('local-bundled 选中时,step 3 显示"本地模型已就位" + 8GB 显存警告', async () => {
    // 跳到 step 2,选 local-bundled
    renderOnboarding();
    await waitFor(() => screen.getByTestId('onboarding-step1-next'));
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => screen.getByTestId('provider-option-local-bundled'));
    fireEvent.click(screen.getByTestId('radio-local-bundled'));
    fireEvent.click(screen.getByTestId('onboarding-step2-next'));
    await waitFor(() => screen.getByTestId('step3-local-bundled'));
    expect(screen.getByTestId('onboarding-vram-warning')).toBeInTheDocument();
    expect(screen.getByTestId('onboarding-vram-warning').textContent).toMatch(/8GB/);
  });

  it('disabled 选中时,step 3 显示"将使用纯滑块模式"', async () => {
    renderOnboarding();
    await waitFor(() => screen.getByTestId('onboarding-step1-next'));
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => screen.getByTestId('provider-option-disabled'));
    fireEvent.click(screen.getByTestId('radio-disabled'));
    fireEvent.click(screen.getByTestId('onboarding-step2-next'));
    await waitFor(() => screen.getByTestId('step3-disabled'));
    expect(screen.getByTestId('step3-disabled').textContent).toMatch(/纯滑块/);
  });
});

// ---------------------------------------------------------------------------
// Phase 3 Task 4:完成提交
// ---------------------------------------------------------------------------

describe('OnboardingPage · 完成提交', () => {
  it('点"完成"调 onboardingApi.complete,成功后 localStorage 写入 onboarding_completed=true', async () => {
    renderOnboarding();
    // step1 → step2 → step3
    await waitFor(() => screen.getByTestId('onboarding-step1-next'));
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => screen.getByTestId('onboarding-step2-next'));
    fireEvent.click(screen.getByTestId('onboarding-step2-next'));
    await waitFor(() => screen.getByTestId('onboarding-step3-config'));

    // 默认 cloud + deepseek + 空 key → 完成按钮应当 disabled
    const completeBtn = screen.getByTestId('onboarding-complete') as HTMLButtonElement;
    expect(completeBtn.disabled).toBe(true);

    // 填 api key
    const keyInput = screen.getByTestId('onboarding-api-key-input');
    fireEvent.change(keyInput, { target: { value: 'sk-test-key' } });

    // 现在按钮可用
    expect(completeBtn.disabled).toBe(false);

    fireEvent.click(completeBtn);

    // 等 complete fetch 被调用
    await waitFor(() => {
      expect(completeCalls.length).toBe(1);
    });
    const call = completeCalls[0];
    expect(call.url).toContain('/api/onboarding/complete');
    expect(call.body).toEqual({
      llm_provider: 'cloud',
      cloud_provider: 'deepseek',
      api_key: 'sk-test-key',
    });

    // localStorage 写入了
    await waitFor(() => {
      expect(window.localStorage.getItem('protoforge.onboarding_completed')).toBe('true');
    });
    expect(window.localStorage.getItem('protoforge.llm.provider')).toBe('cloud');
  });

  it('disabled 模式:无需 API key,"完成"按钮即可点击', async () => {
    renderOnboarding();
    await waitFor(() => screen.getByTestId('onboarding-step1-next'));
    fireEvent.click(screen.getByTestId('onboarding-step1-next'));
    await waitFor(() => screen.getByTestId('provider-option-disabled'));
    fireEvent.click(screen.getByTestId('radio-disabled'));
    fireEvent.click(screen.getByTestId('onboarding-step2-next'));
    await waitFor(() => screen.getByTestId('onboarding-complete'));

    const completeBtn = screen.getByTestId('onboarding-complete') as HTMLButtonElement;
    expect(completeBtn.disabled).toBe(false);

    fireEvent.click(completeBtn);
    await waitFor(() => {
      expect(completeCalls.length).toBe(1);
    });
    expect(completeCalls[0].body).toEqual({
      llm_provider: 'disabled',
      cloud_provider: null,
      api_key: null,
    });
  });
});

// ---------------------------------------------------------------------------
// Phase 3 Task 4:启动跳过
// ---------------------------------------------------------------------------

describe('OnboardingPage · 启动跳过', () => {
  it('localStorage.protoforge.onboarding_completed=true 时,组件挂载后跳到 /forge', async () => {
    window.localStorage.setItem('protoforge.onboarding_completed', 'true');
    renderOnboarding();
    // 跳到 /forge 后,forge page 占位应该出现
    await waitFor(() => {
      expect(screen.getByTestId('forge-page')).toBeInTheDocument();
    });
  });
});
