import { render, screen } from '@testing-library/react';
import { Home } from '@/pages/Home';

describe('Home', () => {
  it('renders title', () => {
    render(<Home />);
    expect(screen.getByText('ProtoForge')).toBeInTheDocument();
  });

  it('shows initial status', () => {
    render(<Home />);
    expect(screen.getByText(/检查中/)).toBeInTheDocument();
  });
});
