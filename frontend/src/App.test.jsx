import { render, screen } from '@testing-library/react';
import App from './App';

test('renders NostroQ header in login mode', () => {
  render(<App />);
  expect(screen.getByText(/Authenticate & Connect/i)).toBeInTheDocument();
});
