import { render, screen } from "@testing-library/react";
import Doci from "./Doci";
describe("Doci", () => {
  it("exposes an accessible label for each state", () => {
    const { rerender } = render(<Doci state="concerned" />);
    expect(screen.getByRole("img", { name: /concerned/i })).toBeInTheDocument();
    rerender(<Doci state="focus-password" />);
    expect(screen.getByRole("img", { name: /looking away/i })).toHaveAttribute("data-state", "focus-password");
  });
});
