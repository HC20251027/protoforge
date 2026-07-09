import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ForgePage } from '@/pages/ForgePage';

// ---------------------------------------------------------------------------
// Mocks — 隔离 mission + forge fetch 调用
// ---------------------------------------------------------------------------

const MISSION_RESPONSE = {
  id: 'polar-glow-v1',
  title: '极地夜光',
  description: '极地酵母目标 + 哺乳动物正交',
  scenario: 'polar',
  level: 'tutorial',
  target_cell_line: 'PolarYeast',
  off_target: 'HEK293',
  intron_length_range: [80, 250] as [number, number],
  sliders: [
    { key: 'min_target_splice', label: 'min target', min: 0, max: 1, step: 0.01, default: 0.65 },
  ],
  risk_rules: [],
};

function makeFetchMock(): typeof fetch {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.includes('/api/missions/polar-glow-v1')) {
      return new Response(JSON.stringify(MISSION_RESPONSE), { status: 200 });
    }
    if (url.includes('/api/forge/run')) {
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (globalThis as any).__lastForgeBody = body;
      return new Response(
        JSON.stringify({
          run_id: 'run_test',
          mission_id: body.mission_id,
          ritual: body.ritual ?? 'urgent',
          ritual_used: body.ritual ?? 'urgent',
          duration_estimate_sec: 5,
          duration_ms: 12,
          badge_unlocked: '急锻者',
          intron: 'GTATGCATGCAG',
          fasta: '>protoforge\nGTATGCATGCAG\n',
          scores: {
            primary: 0.5,
            components: {},
            weights: { alpha: 0.5, beta: 0.35 },
          },
          risk_flags: [],
          passed_gate: true,
        }),
        { status: 200 },
      );
    }
    return new Response('{}', { status: 200 });
  }) as unknown as typeof fetch;
}

beforeEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  delete (globalThis as any).__lastForgeBody;
  vi.spyOn(global, 'fetch').mockImplementation(makeFetchMock());
});

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  delete (globalThis as any).__lastForgeBody;
});

function renderForgePage() {
  return render(
    <MemoryRouter initialEntries={['/missions/polar-glow-v1/forge']}>
      <Routes>
        <Route path="/missions/:missionId/forge" element={<ForgePage />} />
        <Route path="/missions/:missionId/risk" element={<div>risk page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// 测试 1:4 档 segment control 全部渲染
// ---------------------------------------------------------------------------

describe('ForgePage · ritual segment control', () => {
  it('renders all 4 ritual options', async () => {
    renderForgePage();

    await waitFor(() => {
      expect(screen.getByTestId('ritual-selector')).toBeInTheDocument();
    });

    expect(screen.getByTestId('ritual-option-urgent')).toBeInTheDocument();
    expect(screen.getByTestId('ritual-option-standard')).toBeInTheDocument();
    expect(screen.getByTestId('ritual-option-ancient')).toBeInTheDocument();
    expect(screen.getByTestId('ritual-option-crystal')).toBeInTheDocument();

    expect(screen.getByText('急锻')).toBeInTheDocument();
    expect(screen.getByText('主锻')).toBeInTheDocument();
    expect(screen.getByText('古法锻')).toBeInTheDocument();
    expect(screen.getByText('晶种培育')).toBeInTheDocument();
  });

  it('defaults to urgent when localStorage is empty', async () => {
    renderForgePage();

    await waitFor(() => {
      expect(screen.getByTestId('ritual-option-urgent')).toBeInTheDocument();
    });

    const urgentBtn = screen.getByTestId('ritual-option-urgent');
    expect(urgentBtn.getAttribute('aria-pressed')).toBe('true');
  });

  it('restores ritual from localStorage', async () => {
    window.localStorage.setItem('protoforge.ritual', 'ancient');
    renderForgePage();

    await waitFor(() => {
      expect(screen.getByTestId('ritual-option-ancient')).toBeInTheDocument();
    });

    const ancientBtn = screen.getByTestId('ritual-option-ancient');
    expect(ancientBtn.getAttribute('aria-pressed')).toBe('true');
  });
});

// ---------------------------------------------------------------------------
// 测试 2:选 crystal 档时显示 "⚠️ 长时间等待" 警告
// ---------------------------------------------------------------------------

describe('ForgePage · ritual warning', () => {
  it('shows long-wait warning when crystal is selected', async () => {
    renderForgePage();

    await waitFor(() => {
      expect(screen.getByTestId('ritual-option-crystal')).toBeInTheDocument();
    });

    // 初始(默认急锻)不应该有警告
    expect(screen.queryByTestId('ritual-warning')).toBeNull();

    // 切到 crystal
    fireEvent.click(screen.getByTestId('ritual-option-crystal'));

    await waitFor(() => {
      const warn = screen.getByTestId('ritual-warning');
      expect(warn).toBeInTheDocument();
      expect(warn.textContent).toMatch(/长时间等待/);
      expect(warn.textContent).toMatch(/晶种培育/);
    });

    // 警告应该有 role="alert"
    expect(screen.getByTestId('ritual-warning').getAttribute('role')).toBe('alert');
  });

  it('hides warning when switching back to urgent', async () => {
    window.localStorage.setItem('protoforge.ritual', 'crystal');
    renderForgePage();

    await waitFor(() => {
      expect(screen.getByTestId('ritual-option-crystal')).toBeInTheDocument();
    });

    // 初始就是 crystal → 警告应该存在
    expect(screen.getByTestId('ritual-warning')).toBeInTheDocument();

    // 切到 urgent
    fireEvent.click(screen.getByTestId('ritual-option-urgent'));

    await waitFor(() => {
      expect(screen.queryByTestId('ritual-warning')).toBeNull();
    });
  });
});

// ---------------------------------------------------------------------------
// 测试 3:提交时 ritual 字段进 request body
// ---------------------------------------------------------------------------

describe('ForgePage · submit body includes ritual', () => {
  it('submits selected ritual in the forge request body', async () => {
    window.localStorage.setItem('protoforge.ritual', 'ancient');
    renderForgePage();

    // 等待 mission 加载完成
    await waitFor(() => {
      expect(screen.getByTestId('ritual-option-ancient')).toBeInTheDocument();
    });

    expect(screen.getByTestId('ritual-option-ancient').getAttribute('aria-pressed')).toBe('true');

    // 点击"开始锻造"按钮
    const runBtn = screen.getByTestId('forge-run');
    fireEvent.click(runBtn);

    // 等请求结束
    await waitFor(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const body = (globalThis as any).__lastForgeBody;
      expect(body).toBeTruthy();
      expect(body.ritual).toBe('ancient');
      expect(body.mission_id).toBe('polar-glow-v1');
    });
  });

  it('persists selected ritual to localStorage', async () => {
    renderForgePage();

    await waitFor(() => {
      expect(screen.getByTestId('ritual-option-crystal')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('ritual-option-crystal'));

    expect(window.localStorage.getItem('protoforge.ritual')).toBe('crystal');
  });
});
