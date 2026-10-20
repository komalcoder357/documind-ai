import { api, ApiError } from "./api";
describe("api", () => {
  beforeEach(() => { document.cookie = "csrf=tok123"; });
  it("sends CSRF header on writes and not on reads", async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }); vi.stubGlobal("fetch", f);
    await api("/x"); await api("/y", { body: { a: 1 } });
    expect(f.mock.calls[0][1].headers["X-CSRF-Token"]).toBeUndefined(); expect(f.mock.calls[1][1].headers["X-CSRF-Token"]).toBe("tok123");
  });
  it("surfaces server error detail and network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401, statusText: "x", json: async () => ({ detail: "Invalid email or password." }) }));
    await expect(api("/auth/login", { body: {} })).rejects.toThrow("Invalid email or password.");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    await expect(api("/x")).rejects.toBeInstanceOf(ApiError);
  });
});
