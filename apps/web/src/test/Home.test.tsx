import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { Home } from '@/pages/Home';

describe('Home', () => {
  it('renders chinese title', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    );
    expect(screen.getByText(/原体锻炉 ProtoForge/)).toBeInTheDocument();
  });

  it('shows initial loading state', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    );
    expect(screen.getByText(/连接中/)).toBeInTheDocument();
  });

  it('handles health fetch failure gracefully', async () => {
    vi.spyOn(global, 'fetch').mockRejectedValueOnce(new Error('offline'));
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/连接失败/)).toBeInTheDocument();
    });
  });
});
